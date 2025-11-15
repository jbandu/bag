"""
Authentication utility functions

Database operations for:
- API key management
- User management
- Audit logging
- Rate limiting
"""
import asyncpg
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from loguru import logger

from app.core.security import (
    hash_api_key,
    verify_api_key,
    hash_password,
    verify_password,
    generate_api_key
)
from app.auth.schemas import UserRole
from app.auth.models import CurrentAirline, CurrentUser, CurrentAPIKey


class AuthDatabase:
    """Database operations for authentication"""

    def __init__(self, database_url: str):
        """
        Initialize auth database

        Args:
            database_url: PostgreSQL connection string
        """
        self.database_url = database_url
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Create database connection pool"""
        if not self._pool:
            self._pool = await asyncpg.create_pool(
                self.database_url,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            logger.info("Auth database pool created")

    async def disconnect(self):
        """Close database connection pool"""
        if self._pool:
            await self._pool.close()
            logger.info("Auth database pool closed")

    # ========================================================================
    # AIRLINE OPERATIONS
    # ========================================================================

    async def get_airline_by_id(self, airline_id: int) -> Optional[Dict[str, Any]]:
        """Get airline by ID"""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, name, code, iata_code, status, max_api_keys, max_users,
                       created_at, updated_at
                FROM airlines
                WHERE id = $1
                """,
                airline_id
            )
            return dict(row) if row else None

    async def get_airline_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Get airline by code"""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, name, code, iata_code, status, max_api_keys, max_users,
                       created_at, updated_at
                FROM airlines
                WHERE code = $1
                """,
                code
            )
            return dict(row) if row else None

    async def create_airline(
        self,
        name: str,
        code: str,
        iata_code: Optional[str] = None,
        status: str = "active",
        max_api_keys: int = 10,
        max_users: int = 50
    ) -> Dict[str, Any]:
        """Create new airline"""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO airlines (name, code, iata_code, status, max_api_keys, max_users)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, name, code, iata_code, status, max_api_keys, max_users,
                          created_at, updated_at
                """,
                name, code, iata_code, status, max_api_keys, max_users
            )
            logger.info(f"Created airline: {code} (ID: {row['id']})")
            return dict(row)

    # ========================================================================
    # API KEY OPERATIONS
    # ========================================================================

    async def create_api_key(
        self,
        airline_id: int,
        name: str,
        role: str,
        created_by: Optional[int] = None,
        expires_days: Optional[int] = None
    ) -> tuple[Dict[str, Any], str]:
        """
        Create new API key

        Returns:
            Tuple of (api_key_record, plain_api_key)
        """
        # Get airline to generate key with correct prefix
        airline = await self.get_airline_by_id(airline_id)
        if not airline:
            raise ValueError(f"Airline {airline_id} not found")

        # Generate plain key and hash it
        plain_key = generate_api_key(airline['code'])
        key_hash = hash_api_key(plain_key)

        # Calculate expiration
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)

        # Insert into database
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO api_keys (
                    airline_id, key_hash, name, role, is_active,
                    created_by, expires_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id, airline_id, name, role, is_active, created_by,
                          expires_at, last_used_at, usage_count, created_at, updated_at
                """,
                airline_id, key_hash, name, role, True, created_by, expires_at
            )

            logger.info(f"Created API key '{name}' for airline {airline_id} (ID: {row['id']})")
            return dict(row), plain_key

    async def verify_api_key_and_get_details(self, plain_key: str) -> Optional[CurrentAPIKey]:
        """
        Verify API key and return details if valid

        Args:
            plain_key: Plain API key from request header

        Returns:
            CurrentAPIKey if valid, None otherwise
        """
        # Extract airline code from key (format: bagi_{airline_code}_{random})
        try:
            parts = plain_key.split('_')
            if len(parts) != 3 or parts[0] != 'bagi':
                logger.warning("Invalid API key format")
                return None
            airline_code = parts[1]
        except Exception as e:
            logger.warning(f"Error parsing API key: {e}")
            return None

        # Get airline
        airline = await self.get_airline_by_code(airline_code)
        if not airline or airline['status'] != 'active':
            logger.warning(f"Airline {airline_code} not found or not active")
            return None

        # Get all active API keys for this airline
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, airline_id, key_hash, name, role, is_active, expires_at
                FROM api_keys
                WHERE airline_id = $1 AND is_active = true
                AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                """,
                airline['id']
            )

            # Verify key against each hash (constant-time comparison)
            for row in rows:
                if verify_api_key(plain_key, row['key_hash']):
                    # Update last_used_at and usage_count
                    await conn.execute(
                        """
                        UPDATE api_keys
                        SET last_used_at = CURRENT_TIMESTAMP,
                            usage_count = usage_count + 1
                        WHERE id = $1
                        """,
                        row['id']
                    )

                    logger.info(f"API key authenticated: {row['name']} (airline: {airline_code})")

                    return CurrentAPIKey(
                        id=row['id'],
                        airline_id=row['airline_id'],
                        name=row['name'],
                        role=UserRole(row['role']),
                        airline=CurrentAirline(
                            id=airline['id'],
                            name=airline['name'],
                            code=airline['code'],
                            iata_code=airline['iata_code'],
                            status=airline['status']
                        )
                    )

            logger.warning(f"API key verification failed for airline {airline_code}")
            return None

    async def list_api_keys(self, airline_id: int, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """List API keys for an airline"""
        async with self._pool.acquire() as conn:
            query = """
                SELECT id, airline_id, name, role, is_active, created_by,
                       expires_at, last_used_at, usage_count, created_at, updated_at
                FROM api_keys
                WHERE airline_id = $1
            """
            if not include_inactive:
                query += " AND is_active = true"
            query += " ORDER BY created_at DESC"

            rows = await conn.fetch(query, airline_id)
            return [dict(row) for row in rows]

    async def revoke_api_key(self, api_key_id: int, airline_id: int) -> bool:
        """Revoke an API key"""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE api_keys
                SET is_active = false, updated_at = CURRENT_TIMESTAMP
                WHERE id = $1 AND airline_id = $2
                """,
                api_key_id, airline_id
            )
            success = result.split()[-1] == '1'
            if success:
                logger.info(f"Revoked API key {api_key_id}")
            return success

    # ========================================================================
    # USER OPERATIONS
    # ========================================================================

    async def create_user(
        self,
        airline_id: int,
        email: str,
        password: str,
        first_name: Optional[str],
        last_name: Optional[str],
        role: str
    ) -> Dict[str, Any]:
        """Create new user"""
        password_hash = hash_password(password)

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO users (
                    airline_id, email, password_hash, first_name, last_name,
                    role, is_active
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id, airline_id, email, first_name, last_name, role,
                          is_active, email_verified, last_login_at, created_at, updated_at
                """,
                airline_id, email, password_hash, first_name, last_name, role, True
            )

            logger.info(f"Created user: {email} (ID: {row['id']})")
            return dict(row)

    async def verify_user_credentials(self, email: str, password: str) -> Optional[CurrentUser]:
        """
        Verify user credentials and return user details

        Args:
            email: User email
            password: Plain password

        Returns:
            CurrentUser if valid, None otherwise
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT u.id, u.airline_id, u.email, u.password_hash, u.role, u.is_active,
                       u.locked_until, u.failed_login_attempts,
                       a.id as airline_id_2, a.name as airline_name, a.code as airline_code,
                       a.iata_code as airline_iata, a.status as airline_status
                FROM users u
                JOIN airlines a ON u.airline_id = a.id
                WHERE u.email = $1
                """,
                email
            )

            if not row:
                logger.warning(f"User not found: {email}")
                return None

            # Check if account is locked
            if row['locked_until'] and row['locked_until'] > datetime.utcnow():
                logger.warning(f"User account locked: {email}")
                return None

            # Check if user is active
            if not row['is_active']:
                logger.warning(f"User account inactive: {email}")
                return None

            # Check if airline is active
            if row['airline_status'] != 'active':
                logger.warning(f"Airline inactive for user: {email}")
                return None

            # Verify password
            if not verify_password(password, row['password_hash']):
                # Increment failed login attempts
                await conn.execute(
                    """
                    UPDATE users
                    SET failed_login_attempts = failed_login_attempts + 1,
                        locked_until = CASE
                            WHEN failed_login_attempts >= 4 THEN CURRENT_TIMESTAMP + INTERVAL '1 hour'
                            ELSE NULL
                        END
                    WHERE id = $1
                    """,
                    row['id']
                )
                logger.warning(f"Invalid password for user: {email}")
                return None

            # Reset failed attempts and update last login
            await conn.execute(
                """
                UPDATE users
                SET failed_login_attempts = 0,
                    locked_until = NULL,
                    last_login_at = CURRENT_TIMESTAMP
                WHERE id = $1
                """,
                row['id']
            )

            logger.info(f"User authenticated: {email}")

            return CurrentUser(
                id=row['id'],
                airline_id=row['airline_id'],
                email=row['email'],
                role=UserRole(row['role']),
                airline=CurrentAirline(
                    id=row['airline_id'],
                    name=row['airline_name'],
                    code=row['airline_code'],
                    iata_code=row['airline_iata'],
                    status=row['airline_status']
                )
            )

    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, airline_id, email, first_name, last_name, role,
                       is_active, email_verified, last_login_at, created_at, updated_at
                FROM users
                WHERE id = $1
                """,
                user_id
            )
            return dict(row) if row else None

    # ========================================================================
    # AUDIT LOG OPERATIONS
    # ========================================================================

    async def create_audit_log(
        self,
        airline_id: Optional[int],
        user_id: Optional[int],
        api_key_id: Optional[int],
        action: str,
        resource: Optional[str],
        resource_id: Optional[str],
        status: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_method: Optional[str] = None,
        request_path: Optional[str] = None,
        response_status: Optional[int] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Create audit log entry"""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO audit_log (
                    airline_id, user_id, api_key_id, action, resource, resource_id,
                    status, ip_address, user_agent, request_method, request_path,
                    response_status, error_message, metadata
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                """,
                airline_id, user_id, api_key_id, action, resource, resource_id,
                status, ip_address, user_agent, request_method, request_path,
                response_status, error_message, metadata
            )

    async def query_audit_log(
        self,
        airline_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[int] = None,
        api_key_id: Optional[int] = None,
        action: Optional[str] = None,
        resource: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Query audit log

        Returns:
            Tuple of (entries, total_count)
        """
        async with self._pool.acquire() as conn:
            # Build query
            where_clauses = ["airline_id = $1"]
            params = [airline_id]
            param_count = 1

            if start_date:
                param_count += 1
                where_clauses.append(f"timestamp >= ${param_count}")
                params.append(start_date)

            if end_date:
                param_count += 1
                where_clauses.append(f"timestamp <= ${param_count}")
                params.append(end_date)

            if user_id:
                param_count += 1
                where_clauses.append(f"user_id = ${param_count}")
                params.append(user_id)

            if api_key_id:
                param_count += 1
                where_clauses.append(f"api_key_id = ${param_count}")
                params.append(api_key_id)

            if action:
                param_count += 1
                where_clauses.append(f"action = ${param_count}")
                params.append(action)

            if resource:
                param_count += 1
                where_clauses.append(f"resource = ${param_count}")
                params.append(resource)

            where_sql = " AND ".join(where_clauses)

            # Get total count
            count_query = f"SELECT COUNT(*) FROM audit_log WHERE {where_sql}"
            total = await conn.fetchval(count_query, *params)

            # Get entries
            param_count += 1
            params.append(limit)
            param_count += 1
            params.append(offset)

            entries_query = f"""
                SELECT id, airline_id, user_id, api_key_id, action, resource,
                       resource_id, status, ip_address, user_agent, request_method,
                       request_path, response_status, error_message, timestamp
                FROM audit_log
                WHERE {where_sql}
                ORDER BY timestamp DESC
                LIMIT ${param_count - 1} OFFSET ${param_count}
            """
            rows = await conn.fetch(entries_query, *params)
            entries = [dict(row) for row in rows]

            return entries, total

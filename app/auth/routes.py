"""
Authentication API routes

Endpoints for:
- API key management
- User authentication (login/logout)
- Token refresh
- Audit log queries
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from datetime import timedelta
from loguru import logger

from app.auth.models import (
    APIKeyCreate,
    APIKeyResponse,
    APIKeyCreateResponse,
    APIKeyListResponse,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
    AuditLogQuery,
    AuditLogResponse,
    AuditLogEntry,
    CurrentUser,
    CurrentAPIKey,
    CurrentAirline
)
from app.auth.dependencies import (
    get_current_auth,
    get_current_airline,
    require_admin,
    _auth_db,
    _jwt_secret,
    create_audit_log_entry
)
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.auth.schemas import UserRole


# Create router
router = APIRouter(prefix="/auth", tags=["authentication"])


# ============================================================================
# API KEY MANAGEMENT
# ============================================================================

@router.post("/api-keys", response_model=APIKeyCreateResponse, dependencies=[Depends(require_admin)])
async def create_api_key(
    request: Request,
    key_request: APIKeyCreate,
    auth: CurrentUser | CurrentAPIKey = Depends(require_admin),
    airline: CurrentAirline = Depends(get_current_airline)
):
    """
    Create a new API key (admin only)

    **IMPORTANT:** The plain API key is only returned once at creation.
    Save it securely - it cannot be retrieved later.

    **Permissions:** Requires airline_admin or system_admin role
    """
    try:
        # Get creator user ID (only if authenticated as user, not API key)
        created_by = auth.id if isinstance(auth, CurrentUser) else None

        # Create API key
        api_key_record, plain_key = await _auth_db.create_api_key(
            airline_id=airline.id,
            name=key_request.name,
            role=key_request.role.value,
            created_by=created_by,
            expires_days=key_request.expires_days
        )

        # Audit log
        await create_audit_log_entry(
            request=request,
            auth=auth,
            action="create_api_key",
            resource="api_key",
            resource_id=str(api_key_record['id']),
            status="success"
        )

        logger.info(f"Created API key: {key_request.name} for airline {airline.code}")

        # Return response with plain key
        return APIKeyCreateResponse(
            **api_key_record,
            plain_key=plain_key
        )

    except Exception as e:
        logger.error(f"Error creating API key: {e}")
        await create_audit_log_entry(
            request=request,
            auth=auth,
            action="create_api_key",
            resource="api_key",
            status="failure",
            error_message=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create API key: {str(e)}"
        )


@router.get("/api-keys", response_model=APIKeyListResponse)
async def list_api_keys(
    airline: CurrentAirline = Depends(get_current_airline),
    include_inactive: bool = False
):
    """
    List all API keys for the current airline

    **Query Parameters:**
    - include_inactive: Include revoked/expired keys (default: false)
    """
    try:
        keys = await _auth_db.list_api_keys(
            airline_id=airline.id,
            include_inactive=include_inactive
        )

        return APIKeyListResponse(
            keys=[APIKeyResponse(**key) for key in keys],
            total=len(keys)
        )

    except Exception as e:
        logger.error(f"Error listing API keys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list API keys: {str(e)}"
        )


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
async def revoke_api_key(
    request: Request,
    key_id: int,
    auth: CurrentUser | CurrentAPIKey = Depends(require_admin),
    airline: CurrentAirline = Depends(get_current_airline)
):
    """
    Revoke an API key (admin only)

    **Permissions:** Requires airline_admin or system_admin role
    """
    try:
        success = await _auth_db.revoke_api_key(key_id, airline.id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )

        # Audit log
        await create_audit_log_entry(
            request=request,
            auth=auth,
            action="revoke_api_key",
            resource="api_key",
            resource_id=str(key_id),
            status="success"
        )

        logger.info(f"Revoked API key {key_id} for airline {airline.code}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking API key: {e}")
        await create_audit_log_entry(
            request=request,
            auth=auth,
            action="revoke_api_key",
            resource="api_key",
            resource_id=str(key_id),
            status="failure",
            error_message=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke API key: {str(e)}"
        )


# ============================================================================
# USER MANAGEMENT
# ============================================================================

@router.post("/users", response_model=UserResponse, dependencies=[Depends(require_admin)])
async def create_user(
    request: Request,
    user_request: UserCreate,
    auth: CurrentUser | CurrentAPIKey = Depends(require_admin),
    airline: CurrentAirline = Depends(get_current_airline)
):
    """
    Create a new user (admin only)

    **Permissions:** Requires airline_admin or system_admin role
    """
    try:
        user_data = await _auth_db.create_user(
            airline_id=airline.id,
            email=user_request.email,
            password=user_request.password,
            first_name=user_request.first_name,
            last_name=user_request.last_name,
            role=user_request.role.value
        )

        # Audit log
        await create_audit_log_entry(
            request=request,
            auth=auth,
            action="create_user",
            resource="user",
            resource_id=str(user_data['id']),
            status="success"
        )

        logger.info(f"Created user: {user_request.email} for airline {airline.code}")

        return UserResponse(**user_data)

    except Exception as e:
        logger.error(f"Error creating user: {e}")
        await create_audit_log_entry(
            request=request,
            auth=auth,
            action="create_user",
            resource="user",
            status="failure",
            error_message=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )


# ============================================================================
# AUTHENTICATION
# ============================================================================

@router.post("/login", response_model=LoginResponse)
async def login(request: Request, login_request: LoginRequest):
    """
    Authenticate user and return JWT tokens

    **Returns:**
    - access_token: Short-lived token (1 hour) for API requests
    - refresh_token: Long-lived token (30 days) for refreshing access token
    """
    if not _auth_db or not _jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable"
        )

    try:
        # Verify credentials
        user = await _auth_db.verify_user_credentials(
            email=login_request.email,
            password=login_request.password
        )

        if not user:
            # Audit failed login
            await _auth_db.create_audit_log(
                airline_id=None,
                user_id=None,
                api_key_id=None,
                action="login",
                resource="auth",
                status="failure",
                ip_address=request.client.host if request.client else None,
                error_message="Invalid credentials"
            )

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Create tokens
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "airline_id": user.airline_id,
            "role": user.role.value
        }

        access_token = create_access_token(
            data=token_data,
            secret_key=_jwt_secret,
            expires_delta=timedelta(hours=1)
        )

        refresh_token = create_refresh_token(
            data=token_data,
            secret_key=_jwt_secret,
            expires_delta=timedelta(days=30)
        )

        # Audit successful login
        await _auth_db.create_audit_log(
            airline_id=user.airline_id,
            user_id=user.id,
            api_key_id=None,
            action="login",
            resource="auth",
            status="success",
            ip_address=request.client.host if request.client else None
        )

        logger.info(f"User logged in: {user.email}")

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse(
                id=user.id,
                airline_id=user.airline_id,
                email=user.email,
                role=user.role,
                is_active=True,
                email_verified=False,
                last_login_at=None,
                created_at=None
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_request: RefreshTokenRequest):
    """
    Refresh access token using refresh token

    **Returns:**
    - access_token: New short-lived token (1 hour)
    """
    if not _jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable"
        )

    try:
        # Decode refresh token
        payload = decode_token(refresh_request.refresh_token, _jwt_secret)

        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )

        # Verify token type
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )

        # Create new access token
        token_data = {
            "sub": payload.get("sub"),
            "email": payload.get("email"),
            "airline_id": payload.get("airline_id"),
            "role": payload.get("role")
        }

        access_token = create_access_token(
            data=token_data,
            secret_key=_jwt_secret,
            expires_delta=timedelta(hours=1)
        )

        logger.info(f"Token refreshed for user: {payload.get('email')}")

        return TokenResponse(access_token=access_token)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


# ============================================================================
# AUDIT LOG
# ============================================================================

@router.get("/audit-log", response_model=AuditLogResponse)
async def query_audit_log(
    query: AuditLogQuery = Depends(),
    auth: CurrentUser | CurrentAPIKey = Depends(get_current_auth),
    airline: CurrentAirline = Depends(get_current_airline)
):
    """
    Query audit log for the current airline

    **Query Parameters:**
    - start_date: Filter by start date (ISO 8601)
    - end_date: Filter by end date (ISO 8601)
    - user_id: Filter by user ID
    - api_key_id: Filter by API key ID
    - action: Filter by action
    - resource: Filter by resource type
    - limit: Max results (default: 100, max: 1000)
    - offset: Pagination offset (default: 0)
    """
    try:
        entries, total = await _auth_db.query_audit_log(
            airline_id=airline.id,
            start_date=query.start_date,
            end_date=query.end_date,
            user_id=query.user_id,
            api_key_id=query.api_key_id,
            action=query.action,
            resource=query.resource,
            limit=query.limit,
            offset=query.offset
        )

        return AuditLogResponse(
            entries=[AuditLogEntry(**entry) for entry in entries],
            total=total,
            limit=query.limit,
            offset=query.offset
        )

    except Exception as e:
        logger.error(f"Error querying audit log: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query audit log: {str(e)}"
        )


# ============================================================================
# CURRENT USER INFO
# ============================================================================

@router.get("/me")
async def get_current_user_info(
    auth: CurrentUser | CurrentAPIKey = Depends(get_current_auth)
):
    """
    Get current authenticated user/API key information

    **Returns:**
    - Authentication details (user or API key)
    - Airline information
    - Role and permissions
    """
    return {
        "auth_type": "user" if isinstance(auth, CurrentUser) else "api_key",
        "id": auth.id,
        "airline": {
            "id": auth.airline.id,
            "name": auth.airline.name,
            "code": auth.airline.code,
            "iata_code": auth.airline.iata_code
        },
        "role": auth.role.value,
        "email": auth.email if isinstance(auth, CurrentUser) else None,
        "name": auth.name if isinstance(auth, CurrentAPIKey) else None
    }

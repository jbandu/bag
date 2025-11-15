"""
FastAPI dependencies for authentication

Provides dependency injection for:
- API key authentication
- JWT token authentication
- Current airline/user extraction
- Permission checks
- Rate limiting
"""
from fastapi import Header, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Annotated
from datetime import datetime
from loguru import logger

from app.auth.models import CurrentUser, CurrentAPIKey, CurrentAirline
from app.auth.schemas import UserRole
from app.core.security import decode_token


# ============================================================================
# GLOBAL STATE (will be injected by main app)
# ============================================================================

_auth_db = None
_redis_client = None
_jwt_secret = None


def set_auth_dependencies(auth_db, redis_client, jwt_secret: str):
    """
    Initialize auth dependencies

    Call this from main.py on startup
    """
    global _auth_db, _redis_client, _jwt_secret
    _auth_db = auth_db
    _redis_client = redis_client
    _jwt_secret = jwt_secret
    logger.info("Auth dependencies initialized")


# ============================================================================
# API KEY AUTHENTICATION
# ============================================================================

async def get_api_key_from_header(
    x_api_key: Annotated[Optional[str], Header()] = None
) -> Optional[str]:
    """
    Extract API key from X-API-Key header

    Args:
        x_api_key: API key from header

    Returns:
        API key or None
    """
    return x_api_key


async def authenticate_api_key(
    api_key: str = Depends(get_api_key_from_header)
) -> CurrentAPIKey:
    """
    Authenticate request using API key

    Args:
        api_key: API key from header

    Returns:
        CurrentAPIKey with airline and role information

    Raises:
        HTTPException: 401 if authentication fails
    """
    if not api_key:
        logger.warning("API key authentication failed: No API key provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide X-API-Key header."
        )

    if not _auth_db:
        logger.error("Auth database not initialized")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable"
        )

    # Verify API key and get details
    current_api_key = await _auth_db.verify_api_key_and_get_details(api_key)

    if not current_api_key:
        logger.warning(f"API key authentication failed: Invalid key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    logger.info(f"API key authenticated: {current_api_key.name} (airline: {current_api_key.airline.code})")
    return current_api_key


# ============================================================================
# JWT AUTHENTICATION
# ============================================================================

security = HTTPBearer()


async def get_token_from_header(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Extract JWT token from Authorization header

    Args:
        credentials: Bearer token from header

    Returns:
        Token string
    """
    return credentials.credentials


async def authenticate_jwt(
    token: str = Depends(get_token_from_header)
) -> CurrentUser:
    """
    Authenticate request using JWT token

    Args:
        token: JWT token from header

    Returns:
        CurrentUser with airline and role information

    Raises:
        HTTPException: 401 if authentication fails
    """
    if not _jwt_secret:
        logger.error("JWT secret not initialized")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable"
        )

    # Decode token
    payload = decode_token(token, _jwt_secret)

    if not payload:
        logger.warning("JWT authentication failed: Invalid token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify token type
    if payload.get("type") != "access":
        logger.warning("JWT authentication failed: Not an access token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract user information
    user_id = payload.get("sub")
    airline_id = payload.get("airline_id")
    role = payload.get("role")

    if not all([user_id, airline_id, role]):
        logger.warning("JWT authentication failed: Missing required claims")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user details from database
    if not _auth_db:
        logger.error("Auth database not initialized")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable"
        )

    user_data = await _auth_db.get_user_by_id(int(user_id))
    if not user_data or not user_data['is_active']:
        logger.warning(f"JWT authentication failed: User {user_id} not found or inactive")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get airline details
    airline_data = await _auth_db.get_airline_by_id(airline_id)
    if not airline_data or airline_data['status'] != 'active':
        logger.warning(f"JWT authentication failed: Airline {airline_id} not found or inactive")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Airline account inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info(f"JWT authenticated: {user_data['email']} (airline: {airline_data['code']})")

    return CurrentUser(
        id=user_data['id'],
        airline_id=user_data['airline_id'],
        email=user_data['email'],
        role=UserRole(user_data['role']),
        airline=CurrentAirline(
            id=airline_data['id'],
            name=airline_data['name'],
            code=airline_data['code'],
            iata_code=airline_data['iata_code'],
            status=airline_data['status']
        )
    )


# ============================================================================
# FLEXIBLE AUTHENTICATION (API Key OR JWT)
# ============================================================================

async def get_current_auth(
    request: Request,
    api_key: Optional[str] = Depends(get_api_key_from_header),
) -> CurrentUser | CurrentAPIKey:
    """
    Authenticate using either API key or JWT token

    Tries API key first, then JWT if no API key provided

    Returns:
        CurrentUser or CurrentAPIKey depending on auth method

    Raises:
        HTTPException: 401 if authentication fails
    """
    # Try API key authentication first
    if api_key:
        return await authenticate_api_key(api_key)

    # Try JWT authentication
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        return await authenticate_jwt(token)

    # No authentication provided
    logger.warning("No authentication provided")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide either X-API-Key header or Authorization: Bearer token"
    )


# ============================================================================
# AIRLINE EXTRACTION
# ============================================================================

async def get_current_airline(
    auth: CurrentUser | CurrentAPIKey = Depends(get_current_auth)
) -> CurrentAirline:
    """
    Get current airline from authenticated user/API key

    Args:
        auth: Current authentication (user or API key)

    Returns:
        CurrentAirline
    """
    return auth.airline


# ============================================================================
# PERMISSION CHECKS
# ============================================================================

def require_role(required_roles: list[UserRole]):
    """
    Dependency factory for role-based access control

    Usage:
        @app.get("/admin", dependencies=[Depends(require_role([UserRole.SYSTEM_ADMIN]))])

    Args:
        required_roles: List of roles that are allowed access

    Returns:
        Dependency function
    """
    async def check_role(auth: CurrentUser | CurrentAPIKey = Depends(get_current_auth)):
        if auth.role not in required_roles:
            logger.warning(f"Permission denied: {auth.role} not in {required_roles}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {[r.value for r in required_roles]}"
            )
        return auth

    return check_role


# Convenience dependencies for common role checks
async def require_admin(
    auth: CurrentUser | CurrentAPIKey = Depends(get_current_auth)
):
    """Require system_admin or airline_admin role"""
    if auth.role not in [UserRole.SYSTEM_ADMIN, UserRole.AIRLINE_ADMIN]:
        logger.warning(f"Admin permission denied for role: {auth.role}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    return auth


async def require_ops_or_admin(
    auth: CurrentUser | CurrentAPIKey = Depends(get_current_auth)
):
    """Require ops_user, airline_admin, or system_admin role"""
    if auth.role not in [UserRole.SYSTEM_ADMIN, UserRole.AIRLINE_ADMIN, UserRole.OPS_USER]:
        logger.warning(f"Ops permission denied for role: {auth.role}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operations role required"
        )
    return auth


# ============================================================================
# RATE LIMITING
# ============================================================================

async def check_rate_limit(
    request: Request,
    auth: CurrentUser | CurrentAPIKey = Depends(get_current_auth)
):
    """
    Check rate limit for current request

    Uses Redis to track requests per hour per API key/user

    Args:
        request: FastAPI request
        auth: Current authentication

    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    if not _redis_client:
        # Rate limiting disabled if Redis not available
        logger.warning("Rate limiting disabled - Redis not configured")
        return

    # Determine rate limit key
    if isinstance(auth, CurrentAPIKey):
        limit_key = f"ratelimit:apikey:{auth.id}"
        limit = 1000  # 1000 requests per hour for API keys
    else:
        limit_key = f"ratelimit:user:{auth.id}"
        limit = 500  # 500 requests per hour for users

    # Get current count
    try:
        current = await _redis_client.incr(limit_key)

        # Set expiration on first request
        if current == 1:
            await _redis_client.expire(limit_key, 3600)  # 1 hour

        # Check limit
        if current > limit:
            ttl = await _redis_client.ttl(limit_key)
            logger.warning(f"Rate limit exceeded for {limit_key}: {current}/{limit}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {ttl} seconds.",
                headers={"Retry-After": str(ttl)}
            )

        # Add rate limit headers to response (will be done in middleware)
        request.state.rate_limit_current = current
        request.state.rate_limit_limit = limit
        request.state.rate_limit_remaining = limit - current

    except Exception as e:
        logger.error(f"Rate limiting error: {e}")
        # Don't block request if rate limiting fails
        pass


# ============================================================================
# AUDIT LOGGING
# ============================================================================

async def create_audit_log_entry(
    request: Request,
    auth: CurrentUser | CurrentAPIKey,
    action: str,
    resource: Optional[str] = None,
    resource_id: Optional[str] = None,
    status: str = "success",
    response_status: Optional[int] = None,
    error_message: Optional[str] = None
):
    """
    Create audit log entry

    Args:
        request: FastAPI request
        auth: Current authentication
        action: Action performed
        resource: Resource type
        resource_id: Resource ID
        status: Status (success/failure)
        response_status: HTTP response status
        error_message: Error message if failed
    """
    if not _auth_db:
        return

    try:
        # Extract request details
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        request_method = request.method
        request_path = str(request.url.path)

        # Determine user_id and api_key_id
        user_id = auth.id if isinstance(auth, CurrentUser) else None
        api_key_id = auth.id if isinstance(auth, CurrentAPIKey) else None

        await _auth_db.create_audit_log(
            airline_id=auth.airline_id,
            user_id=user_id,
            api_key_id=api_key_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            status=status,
            ip_address=ip_address,
            user_agent=user_agent,
            request_method=request_method,
            request_path=request_path,
            response_status=response_status,
            error_message=error_message
        )
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")

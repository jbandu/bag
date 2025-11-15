"""
Authentication module for Baggage Operations Platform

Multi-tenant authentication with:
- API key authentication (X-API-Key header)
- JWT token authentication (Bearer token)
- Role-based access control
- Audit logging
- Rate limiting
"""
from app.auth.models import (
    UserRole,
    CurrentUser,
    CurrentAPIKey,
    CurrentAirline
)
from app.auth.dependencies import (
    get_current_auth,
    get_current_airline,
    authenticate_api_key,
    authenticate_jwt,
    require_admin,
    require_ops_or_admin,
    require_role,
    check_rate_limit,
    set_auth_dependencies
)
from app.auth.routes import router as auth_router
from app.auth.utils import AuthDatabase

__all__ = [
    # Models
    "UserRole",
    "CurrentUser",
    "CurrentAPIKey",
    "CurrentAirline",
    # Dependencies
    "get_current_auth",
    "get_current_airline",
    "authenticate_api_key",
    "authenticate_jwt",
    "require_admin",
    "require_ops_or_admin",
    "require_role",
    "check_rate_limit",
    "set_auth_dependencies",
    # Router
    "auth_router",
    # Database
    "AuthDatabase"
]

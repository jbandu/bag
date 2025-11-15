"""
Pydantic models for authentication API

Request and response models for:
- API key management
- User authentication
- Audit log queries
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, EmailStr, Field, validator
from app.auth.schemas import UserRole, AirlineStatus


# ============================================================================
# AIRLINE MODELS
# ============================================================================

class AirlineBase(BaseModel):
    """Base airline model"""
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=2, max_length=10, pattern="^[a-z0-9_]+$")
    iata_code: Optional[str] = Field(None, min_length=2, max_length=3, pattern="^[A-Z]{2,3}$")
    status: AirlineStatus = AirlineStatus.ACTIVE


class AirlineCreate(AirlineBase):
    """Create airline request"""
    max_api_keys: int = Field(10, ge=1, le=100)
    max_users: int = Field(50, ge=1, le=1000)


class AirlineResponse(AirlineBase):
    """Airline response"""
    id: int
    max_api_keys: int
    max_users: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# API KEY MODELS
# ============================================================================

class APIKeyCreate(BaseModel):
    """Create API key request"""
    name: str = Field(..., min_length=1, max_length=255, description="Descriptive name for the API key")
    role: UserRole = Field(UserRole.READONLY, description="Role for access control")
    expires_days: Optional[int] = Field(None, ge=1, le=365, description="Expiration in days (None = no expiration)")

    @validator('name')
    def validate_name(cls, v):
        """Ensure name is descriptive"""
        if len(v.strip()) < 3:
            raise ValueError("Name must be at least 3 characters")
        return v.strip()


class APIKeyResponse(BaseModel):
    """API key response (without the actual key)"""
    id: int
    airline_id: int
    name: str
    role: UserRole
    is_active: bool
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    usage_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class APIKeyCreateResponse(APIKeyResponse):
    """
    Response when creating a new API key

    IMPORTANT: The plain_key is only shown ONCE at creation time
    """
    plain_key: str = Field(..., description="The actual API key - SAVE THIS! It won't be shown again")


class APIKeyListResponse(BaseModel):
    """List of API keys"""
    keys: List[APIKeyResponse]
    total: int


# ============================================================================
# USER MODELS
# ============================================================================

class UserBase(BaseModel):
    """Base user model"""
    email: EmailStr
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    role: UserRole = UserRole.READONLY


class UserCreate(UserBase):
    """Create user request"""
    password: str = Field(..., min_length=8, max_length=100)

    @validator('password')
    def validate_password(cls, v):
        """Ensure strong password"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserResponse(UserBase):
    """User response"""
    id: int
    airline_id: int
    is_active: bool
    email_verified: bool
    last_login_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Update user request"""
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


# ============================================================================
# AUTHENTICATION MODELS
# ============================================================================

class LoginRequest(BaseModel):
    """User login request"""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Login response with tokens"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600  # seconds
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


# ============================================================================
# CURRENT USER/AIRLINE MODELS
# ============================================================================

class CurrentAirline(BaseModel):
    """Current authenticated airline"""
    id: int
    name: str
    code: str
    iata_code: Optional[str]
    status: AirlineStatus


class CurrentUser(BaseModel):
    """Current authenticated user"""
    id: int
    airline_id: int
    email: str
    role: UserRole
    airline: Optional[CurrentAirline] = None


class CurrentAPIKey(BaseModel):
    """Current authenticated API key"""
    id: int
    airline_id: int
    name: str
    role: UserRole
    airline: Optional[CurrentAirline] = None


# ============================================================================
# AUDIT LOG MODELS
# ============================================================================

class AuditLogEntry(BaseModel):
    """Audit log entry"""
    id: int
    airline_id: Optional[int]
    user_id: Optional[int]
    api_key_id: Optional[int]
    action: str
    resource: Optional[str]
    resource_id: Optional[str]
    status: str
    ip_address: Optional[str]
    request_method: Optional[str]
    request_path: Optional[str]
    response_status: Optional[int]
    error_message: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True


class AuditLogQuery(BaseModel):
    """Query parameters for audit log"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    user_id: Optional[int] = None
    api_key_id: Optional[int] = None
    action: Optional[str] = None
    resource: Optional[str] = None
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)


class AuditLogResponse(BaseModel):
    """Audit log response"""
    entries: List[AuditLogEntry]
    total: int
    limit: int
    offset: int


# ============================================================================
# PERMISSION CHECKS
# ============================================================================

class PermissionCheck(BaseModel):
    """Permission check result"""
    allowed: bool
    reason: Optional[str] = None


# ============================================================================
# RATE LIMIT MODELS
# ============================================================================

class RateLimitInfo(BaseModel):
    """Rate limit information"""
    limit: int
    remaining: int
    reset_at: datetime
    retry_after: Optional[int] = None  # seconds until rate limit resets

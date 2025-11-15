"""
Security utilities for authentication and encryption
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
from loguru import logger

# Password hashing context (using bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings (will be configured from settings)
ALGORITHM = "HS256"


def generate_api_key(airline_code: str) -> str:
    """
    Generate a secure API key with airline prefix

    Format: bagi_{airline_code}_{32_char_hex}
    Example: bagi_copa_a1b2c3d4e5f6...

    Args:
        airline_code: Airline IATA code (e.g., 'copa')

    Returns:
        Formatted API key string
    """
    random_part = secrets.token_hex(16)  # 32 characters
    api_key = f"bagi_{airline_code.lower()}_{random_part}"
    logger.info(f"Generated API key for airline: {airline_code}")
    return api_key


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for secure storage

    Uses bcrypt for secure, salted hashing

    Args:
        api_key: Plain API key string

    Returns:
        Hashed API key
    """
    return pwd_context.hash(api_key)


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """
    Verify an API key against its hash using constant-time comparison

    Args:
        plain_key: Plain API key from request
        hashed_key: Hashed API key from database

    Returns:
        True if keys match, False otherwise
    """
    return pwd_context.verify(plain_key, hashed_key)


def hash_password(password: str) -> str:
    """
    Hash a password for secure storage

    Args:
        password: Plain password string

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash

    Args:
        plain_password: Plain password from login
        hashed_password: Hashed password from database

    Returns:
        True if passwords match, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: Dict[str, Any],
    secret_key: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token

    Args:
        data: Data to encode in token (e.g., user_id, airline_id, role)
        secret_key: Secret key for signing
        expires_delta: Token expiration time (default: 1 hour)

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=1)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })

    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any],
    secret_key: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token

    Args:
        data: Data to encode in token
        secret_key: Secret key for signing
        expires_delta: Token expiration time (default: 30 days)

    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=30)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })

    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str, secret_key: str) -> Optional[Dict[str, Any]]:
    """
    Decode and verify a JWT token

    Args:
        token: JWT token to decode
        secret_key: Secret key for verification

    Returns:
        Decoded token payload or None if invalid
    """
    try:
        payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None


def generate_session_id() -> str:
    """
    Generate a unique session ID

    Returns:
        32-character hex session ID
    """
    return secrets.token_hex(16)

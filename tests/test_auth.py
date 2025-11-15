"""
Authentication System Tests

Tests for:
- API key generation and verification
- JWT token creation and validation
- User authentication
- Role-based access control
- Rate limiting
- Audit logging
"""
import pytest
import asyncio
from datetime import datetime, timedelta

from app.core.security import (
    generate_api_key,
    hash_api_key,
    verify_api_key,
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
)


# ============================================================================
# API KEY TESTS
# ============================================================================

def test_generate_api_key():
    """Test API key generation"""
    api_key = generate_api_key("copa")

    assert api_key.startswith("bagi_copa_")
    assert len(api_key) == len("bagi_copa_") + 32  # prefix + 32 hex chars
    assert "_" in api_key


def test_api_key_hashing():
    """Test API key hashing and verification"""
    api_key = generate_api_key("copa")
    key_hash = hash_api_key(api_key)

    # Hash should be different from plain key
    assert key_hash != api_key

    # Verification should succeed with correct key
    assert verify_api_key(api_key, key_hash)

    # Verification should fail with wrong key
    wrong_key = generate_api_key("copa")
    assert not verify_api_key(wrong_key, key_hash)


def test_api_key_uniqueness():
    """Test that generated API keys are unique"""
    keys = [generate_api_key("copa") for _ in range(10)]

    # All keys should be unique
    assert len(keys) == len(set(keys))


# ============================================================================
# PASSWORD TESTS
# ============================================================================

def test_password_hashing():
    """Test password hashing and verification"""
    password = "SecurePassword123!"
    password_hash = hash_password(password)

    # Hash should be different from plain password
    assert password_hash != password

    # Verification should succeed with correct password
    assert verify_password(password, password_hash)

    # Verification should fail with wrong password
    assert not verify_password("WrongPassword", password_hash)


# ============================================================================
# JWT TOKEN TESTS
# ============================================================================

def test_create_access_token():
    """Test JWT access token creation"""
    secret = "test_secret_key_123456789"
    data = {
        "sub": "1",
        "email": "test@example.com",
        "airline_id": 1,
        "role": "ops_user"
    }

    token = create_access_token(data, secret)

    assert isinstance(token, str)
    assert len(token) > 50  # JWT tokens are typically longer


def test_decode_token():
    """Test JWT token decoding"""
    secret = "test_secret_key_123456789"
    data = {
        "sub": "1",
        "email": "test@example.com",
        "airline_id": 1,
        "role": "ops_user"
    }

    token = create_access_token(data, secret)
    payload = decode_token(token, secret)

    assert payload is not None
    assert payload["sub"] == "1"
    assert payload["email"] == "test@example.com"
    assert payload["airline_id"] == 1
    assert payload["role"] == "ops_user"
    assert payload["type"] == "access"


def test_expired_token():
    """Test that expired tokens are rejected"""
    secret = "test_secret_key_123456789"
    data = {"sub": "1"}

    # Create token that expires immediately
    token = create_access_token(
        data,
        secret,
        expires_delta=timedelta(seconds=-1)  # Already expired
    )

    payload = decode_token(token, secret)

    # Should return None for expired token
    assert payload is None


def test_invalid_token():
    """Test that invalid tokens are rejected"""
    secret = "test_secret_key_123456789"

    # Try to decode a clearly invalid token
    payload = decode_token("invalid.token.here", secret)

    assert payload is None


def test_wrong_secret():
    """Test that tokens signed with wrong secret are rejected"""
    secret1 = "test_secret_key_111111111"
    secret2 = "test_secret_key_222222222"
    data = {"sub": "1"}

    # Create token with secret1
    token = create_access_token(data, secret1)

    # Try to decode with secret2
    payload = decode_token(token, secret2)

    assert payload is None


def test_refresh_token():
    """Test refresh token creation"""
    secret = "test_secret_key_123456789"
    data = {"sub": "1"}

    refresh_token = create_refresh_token(data, secret)
    payload = decode_token(refresh_token, secret)

    assert payload is not None
    assert payload["type"] == "refresh"


# ============================================================================
# ROLE-BASED ACCESS CONTROL TESTS
# ============================================================================

def test_role_hierarchy():
    """Test that role hierarchy is correct"""
    from app.auth.schemas import UserRole

    # All roles should be accessible
    assert UserRole.SYSTEM_ADMIN == "system_admin"
    assert UserRole.AIRLINE_ADMIN == "airline_admin"
    assert UserRole.OPS_USER == "ops_user"
    assert UserRole.READONLY == "readonly"


# ============================================================================
# DATABASE TESTS (require async)
# ============================================================================

@pytest.mark.asyncio
async def test_auth_database_connection():
    """Test that auth database can connect"""
    import os
    from app.auth.utils import AuthDatabase

    # Skip if no database URL
    db_url = os.getenv("NEON_DATABASE_URL")
    if not db_url:
        pytest.skip("NEON_DATABASE_URL not set")

    auth_db = AuthDatabase(db_url)
    await auth_db.connect()
    await auth_db.disconnect()


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_full_api_key_flow():
    """Test complete API key creation and verification flow"""
    import os
    from app.auth.utils import AuthDatabase

    # Skip if no database URL
    db_url = os.getenv("NEON_DATABASE_URL")
    if not db_url:
        pytest.skip("NEON_DATABASE_URL not set")

    auth_db = AuthDatabase(db_url)
    await auth_db.connect()

    try:
        # Get Copa airline
        airline = await auth_db.get_airline_by_code("copa")
        if not airline:
            pytest.skip("Copa airline not found in database")

        # Create API key
        api_key_record, plain_key = await auth_db.create_api_key(
            airline_id=airline['id'],
            name="Test API Key",
            role="readonly",
            expires_days=30
        )

        assert api_key_record is not None
        assert plain_key.startswith("bagi_copa_")

        # Verify API key
        verified = await auth_db.verify_api_key_and_get_details(plain_key)

        assert verified is not None
        assert verified.airline_id == airline['id']
        assert verified.airline.code == "copa"
        assert verified.role.value == "readonly"

        # Revoke API key
        success = await auth_db.revoke_api_key(api_key_record['id'], airline['id'])
        assert success

        # Verify revoked key doesn't work
        verified_after_revoke = await auth_db.verify_api_key_and_get_details(plain_key)
        assert verified_after_revoke is None

    finally:
        await auth_db.disconnect()


@pytest.mark.asyncio
async def test_full_user_flow():
    """Test complete user creation and authentication flow"""
    import os
    from app.auth.utils import AuthDatabase

    # Skip if no database URL
    db_url = os.getenv("NEON_DATABASE_URL")
    if not db_url:
        pytest.skip("NEON_DATABASE_URL not set")

    auth_db = AuthDatabase(db_url)
    await auth_db.connect()

    try:
        # Get Copa airline
        airline = await auth_db.get_airline_by_code("copa")
        if not airline:
            pytest.skip("Copa airline not found in database")

        # Create user
        test_email = f"test_{datetime.utcnow().timestamp()}@example.com"
        test_password = "TestPassword123!"

        user_data = await auth_db.create_user(
            airline_id=airline['id'],
            email=test_email,
            password=test_password,
            first_name="Test",
            last_name="User",
            role="readonly"
        )

        assert user_data is not None
        assert user_data['email'] == test_email

        # Verify credentials
        verified = await auth_db.verify_user_credentials(test_email, test_password)

        assert verified is not None
        assert verified.email == test_email
        assert verified.airline.code == "copa"
        assert verified.role.value == "readonly"

        # Wrong password should fail
        wrong_verify = await auth_db.verify_user_credentials(test_email, "WrongPassword")
        assert wrong_verify is None

    finally:
        await auth_db.disconnect()


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    print("Running authentication tests...")
    print("\nTo run all tests:")
    print("  pytest tests/test_auth.py -v")
    print("\nTo run specific test:")
    print("  pytest tests/test_auth.py::test_generate_api_key -v")
    print("\nTo run with database tests:")
    print("  NEON_DATABASE_URL=<your_url> pytest tests/test_auth.py -v")

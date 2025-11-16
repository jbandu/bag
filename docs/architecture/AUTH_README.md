# Authentication System - Copa Airlines Baggage Platform

## Overview

Production-grade multi-tenant authentication system with:
- **API Key Authentication** (X-API-Key header) for system-to-system integration
- **JWT Authentication** (Bearer token) for dashboard users
- **Role-Based Access Control** (RBAC) with 4 roles
- **Audit Logging** for all authenticated operations
- **Rate Limiting** (1000 req/hour per API key, 500 req/hour per user)
- **Multi-Tenant** support for multiple airlines

---

## Quick Start

### 1. Run Database Migration

```bash
# Connect to your Neon PostgreSQL database
psql $NEON_DATABASE_URL -f migrations/add_auth_tables.sql
```

### 2. Generate Secrets

```bash
# Generate JWT secret
python -c 'import secrets; print(f"JWT_SECRET={secrets.token_urlsafe(32)}")'

# Generate application secret
python -c 'import secrets; print(f"SECRET_KEY={secrets.token_urlsafe(32)}")'
```

### 3. Update Environment Variables

Add to your `.env`:

```bash
# Authentication
JWT_SECRET=<generated_jwt_secret>
SECRET_KEY=<generated_secret_key>
NEON_DATABASE_URL=postgresql://user:password@host/database
```

### 4. Set Up Copa Airlines

```bash
python scripts/setup_copa_auth.py
```

This creates:
- Copa Airlines tenant
- Initial admin user: `admin@copaair.com`
- Initial API key

**⚠️ SAVE THE CREDENTIALS! They are only shown once.**

---

## API Key Authentication

### Creating an API Key

**Endpoint:** `POST /auth/api-keys`

**Required Role:** `airline_admin` or `system_admin`

**Request:**
```json
{
  "name": "Production BHS Integration",
  "role": "ops_user",
  "expires_days": 365
}
```

**Response:**
```json
{
  "id": 1,
  "airline_id": 1,
  "name": "Production BHS Integration",
  "role": "ops_user",
  "plain_key": "bagi_copa_a1b2c3d4e5f67890...",
  "created_at": "2024-11-14T10:00:00Z"
}
```

**⚠️ Save `plain_key` immediately - it won't be shown again!**

### Using an API Key

Add `X-API-Key` header to all requests:

```bash
curl -H "X-API-Key: bagi_copa_a1b2c3d4..." \
     https://your-api.railway.app/api/v1/bags
```

### Listing API Keys

```bash
curl -H "X-API-Key: bagi_copa_..." \
     https://your-api.railway.app/auth/api-keys
```

### Revoking an API Key

```bash
curl -X DELETE \
     -H "X-API-Key: bagi_copa_..." \
     https://your-api.railway.app/auth/api-keys/1
```

---

## JWT Authentication (Dashboard Users)

### Creating a User

**Endpoint:** `POST /auth/users`

**Required Role:** `airline_admin` or `system_admin`

**Request:**
```json
{
  "email": "ops@copaair.com",
  "password": "SecurePassword123!",
  "first_name": "Operations",
  "last_name": "User",
  "role": "ops_user"
}
```

### Login

**Endpoint:** `POST /auth/login`

**Request:**
```json
{
  "email": "admin@copaair.com",
  "password": "Copa2024!Admin"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1...",
  "refresh_token": "eyJhbGciOiJIUzI1...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": 1,
    "email": "admin@copaair.com",
    "role": "system_admin"
  }
}
```

### Using JWT Token

Add `Authorization: Bearer <token>` header:

```bash
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1..." \
     https://your-api.railway.app/api/v1/bags
```

### Refreshing Token

**Endpoint:** `POST /auth/refresh`

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1..."
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

## Roles & Permissions

### Role Hierarchy

| Role | Permissions | Use Case |
|------|-------------|----------|
| **system_admin** | Full system access, manage all airlines | Copa IT administrators |
| **airline_admin** | Manage airline users/keys, all airline operations | Copa baggage managers |
| **ops_user** | Create/update bags, scan events, read audit log | Operations staff, integrations |
| **readonly** | Read-only access to bags and events | Reporting, analytics |

### Permission Matrix

| Operation | readonly | ops_user | airline_admin | system_admin |
|-----------|----------|----------|---------------|--------------|
| Read bags | ✅ | ✅ | ✅ | ✅ |
| Process scan events | ❌ | ✅ | ✅ | ✅ |
| Create API keys | ❌ | ❌ | ✅ | ✅ |
| Create users | ❌ | ❌ | ✅ | ✅ |
| View audit log | ❌ | ✅ | ✅ | ✅ |
| Manage airlines | ❌ | ❌ | ❌ | ✅ |

---

## Audit Logging

All authenticated operations are automatically logged.

### Query Audit Log

**Endpoint:** `GET /auth/audit-log`

**Query Parameters:**
- `start_date`: ISO 8601 timestamp
- `end_date`: ISO 8601 timestamp
- `action`: Action filter (e.g., `create_api_key`, `login`)
- `resource`: Resource filter (e.g., `api_key`, `bag`)
- `limit`: Max results (default: 100)
- `offset`: Pagination offset

**Example:**
```bash
curl -H "X-API-Key: bagi_copa_..." \
     "https://your-api.railway.app/auth/audit-log?action=create_api_key&limit=50"
```

**Response:**
```json
{
  "entries": [
    {
      "id": 123,
      "action": "create_api_key",
      "resource": "api_key",
      "resource_id": "5",
      "status": "success",
      "user_id": 1,
      "ip_address": "192.168.1.1",
      "timestamp": "2024-11-14T10:00:00Z"
    }
  ],
  "total": 150,
  "limit": 50,
  "offset": 0
}
```

---

## Rate Limiting

### Limits

- **API Keys:** 1000 requests/hour
- **JWT Users:** 500 requests/hour
- **Window:** Sliding 1-hour window
- **Storage:** Redis

### Response Headers

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 847
X-RateLimit-Reset: 2024-11-14T11:00:00Z
```

### 429 Too Many Requests

```json
{
  "detail": "Rate limit exceeded. Try again in 1847 seconds.",
  "retry_after": 1847
}
```

---

## Multi-Tenant Isolation

All data is automatically filtered by `airline_id`:
- Each airline can only access their own data
- API keys are scoped to a single airline
- Users belong to a single airline
- All database queries include `airline_id` filter

---

## Security Best Practices

### API Key Security

✅ **DO:**
- Store API keys in environment variables or secure vaults
- Use different keys for dev/staging/production
- Rotate keys regularly (every 90-365 days)
- Revoke keys immediately if compromised
- Set expiration dates when creating keys

❌ **DON'T:**
- Commit API keys to version control
- Share keys via email or chat
- Use the same key across multiple systems
- Log or display API keys in plain text

### Password Security

✅ **DO:**
- Enforce strong password requirements (8+ chars, mixed case, numbers)
- Use bcrypt for password hashing
- Implement account lockout (5 failed attempts = 1 hour lockout)
- Force password change on first login
- Use 2FA for production (future enhancement)

❌ **DON'T:**
- Store passwords in plain text
- Allow weak passwords
- Share user accounts

### JWT Security

✅ **DO:**
- Use short expiration times (1 hour for access tokens)
- Use refresh tokens for long sessions (30 days)
- Store tokens securely (httpOnly cookies in browsers)
- Invalidate tokens on logout
- Rotate JWT secrets periodically

❌ **DON'T:**
- Store JWTs in localStorage (XSS risk)
- Use long expiration times for access tokens
- Share JWT secrets
- Include sensitive data in JWT payload

---

## Testing

### Test Authentication

```bash
# Create test script
cat > test_auth.sh << 'EOF'
#!/bin/bash

API_KEY="your_api_key_here"
API_URL="http://localhost:8000"

echo "1. Test API key authentication..."
curl -H "X-API-Key: $API_KEY" $API_URL/api/v1/bags

echo "\n2. Test login..."
curl -X POST $API_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@copaair.com","password":"Copa2024!Admin"}'

echo "\n3. Test /me endpoint..."
curl -H "X-API-Key: $API_KEY" $API_URL/auth/me
EOF

chmod +x test_auth.sh
./test_auth.sh
```

### Unit Tests

```bash
pytest tests/test_auth.py -v
```

---

## Troubleshooting

### "API key required"

- Verify `X-API-Key` header is present
- Check key format: `bagi_<airline>_<random32>`
- Verify key is active and not expired

### "Invalid API key"

- Key may be revoked or expired
- Key hash mismatch (typo in key)
- Airline account suspended

### "Invalid or expired token"

- Access token expired (1 hour lifetime)
- Use refresh token to get new access token
- Re-login if refresh token expired (30 days)

### "Insufficient permissions"

- Check user/API key role
- Verify endpoint permission requirements
- Contact admin to upgrade role if needed

### "Rate limit exceeded"

- Wait for rate limit window to reset
- Check `Retry-After` header for wait time
- Consider upgrading to higher tier (future)

---

## Deployment Checklist

### Railway Deployment

1. **Set Environment Variables:**
   ```
   JWT_SECRET=<generated_secret>
   SECRET_KEY=<generated_secret>
   NEON_DATABASE_URL=<neon_connection_string>
   REDIS_URL=<railway_redis_url>
   ```

2. **Run Migration:**
   ```bash
   railway run psql $NEON_DATABASE_URL -f migrations/add_auth_tables.sql
   ```

3. **Initialize Copa:**
   ```bash
   railway run python scripts/setup_copa_auth.py
   ```

4. **Verify Deployment:**
   ```bash
   curl https://your-app.railway.app/health
   curl -H "X-API-Key: <key>" https://your-app.railway.app/auth/me
   ```

---

## API Reference

### Authentication Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/auth/login` | POST | None | User login |
| `/auth/refresh` | POST | None | Refresh access token |
| `/auth/api-keys` | POST | Admin | Create API key |
| `/auth/api-keys` | GET | Any | List API keys |
| `/auth/api-keys/{id}` | DELETE | Admin | Revoke API key |
| `/auth/users` | POST | Admin | Create user |
| `/auth/audit-log` | GET | Ops+ | Query audit log |
| `/auth/me` | GET | Any | Get current auth info |

---

## Support

For issues or questions:
1. Check this documentation
2. Review audit logs for error details
3. Test with the provided scripts
4. Contact Copa IT support

---

**Last Updated:** November 14, 2024
**Version:** 1.0.0
**Maintained by:** Copa Airlines IT Team

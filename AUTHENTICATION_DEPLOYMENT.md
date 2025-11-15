# Authentication System Deployment Guide

## 🚀 Quick Start (5 Steps to Production)

### Step 1: Run Database Migration

Connect to your Neon PostgreSQL database and run the migration:

```bash
# Option A: Direct connection
psql $NEON_DATABASE_URL -f migrations/add_auth_tables.sql

# Option B: Railway CLI
railway run psql $NEON_DATABASE_URL -f migrations/add_auth_tables.sql
```

**Verification:**
```sql
-- Check tables were created
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('airlines', 'users', 'api_keys', 'audit_log', 'rate_limits');

-- Verify Copa Airlines exists
SELECT * FROM airlines WHERE code = 'copa';
```

---

### Step 2: Generate Secrets

```bash
# Generate JWT secret (32+ characters)
python3 -c "import secrets; print('JWT_SECRET=' + secrets.token_urlsafe(32))"

# Generate application secret (32+ characters)
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
```

**Save these secrets securely!**

---

### Step 3: Update Environment Variables

#### Railway Deployment

```bash
# Set via Railway dashboard or CLI
railway variables set JWT_SECRET="<your_jwt_secret>"
railway variables set SECRET_KEY="<your_secret_key>"
railway variables set NEON_DATABASE_URL="<your_neon_url>"
```

#### Local .env File

```bash
# Add to .env
JWT_SECRET=<your_jwt_secret>
SECRET_KEY=<your_secret_key>
NEON_DATABASE_URL=postgresql://user:password@host/database
```

---

### Step 4: Initialize Copa Airlines

```bash
# Install dependencies first
pip install -r requirements.full.txt

# Run setup script
python scripts/setup_copa_auth.py
```

**Output will show:**
- ✅ Copa Airlines tenant created
- ✅ Admin user created (admin@copaair.com)
- ✅ Initial API key generated

**⚠️ SAVE THE CREDENTIALS! They are only shown once.**

The credentials will be saved to `COPA_CREDENTIALS.txt` - **delete this file** after copying credentials to a secure location.

---

### Step 5: Test Authentication

```bash
# Test API key authentication
curl -H "X-API-Key: bagi_copa_..." \
     https://your-app.railway.app/auth/me

# Test user login
curl -X POST https://your-app.railway.app/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"admin@copaair.com","password":"Copa2024!Admin"}'

# Test protected endpoint
curl -H "X-API-Key: bagi_copa_..." \
     https://your-app.railway.app/api/v1/bags
```

---

## 📋 Deployment Checklist

### Pre-Deployment

- [ ] Backup existing database
- [ ] Review migration script
- [ ] Generate JWT_SECRET and SECRET_KEY
- [ ] Test migration in development first

### Deployment

- [ ] Run database migration
- [ ] Update environment variables
- [ ] Run Copa setup script
- [ ] Save credentials securely
- [ ] Delete COPA_CREDENTIALS.txt

### Post-Deployment

- [ ] Test API key authentication
- [ ] Test user login
- [ ] Test protected endpoints
- [ ] Verify audit logging
- [ ] Test rate limiting
- [ ] Check metrics endpoint

### Security

- [ ] Change default admin password
- [ ] Create additional API keys as needed
- [ ] Set up API key rotation schedule (90-365 days)
- [ ] Configure CORS for production domains
- [ ] Enable HTTPS/TLS
- [ ] Review audit logs regularly

---

## 🔧 Configuration Options

### JWT Settings (in config/settings.py)

```python
# Token expiration times
ACCESS_TOKEN_EXPIRE = timedelta(hours=1)      # Short-lived
REFRESH_TOKEN_EXPIRE = timedelta(days=30)     # Long-lived
```

### Rate Limits (in app/auth/dependencies.py)

```python
# Current limits
API_KEY_LIMIT = 1000  # requests per hour
USER_LIMIT = 500      # requests per hour
```

### Password Requirements

Enforced automatically:
- Minimum 8 characters
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 digit

Account lockout:
- 5 failed attempts = 1 hour lockout
- Automatically reset on successful login

---

## 🏗️ Architecture Changes

### New Database Tables

1. **airlines** - Multi-tenant airline accounts
2. **users** - Dashboard users with JWT authentication
3. **api_keys** - System-to-system API keys
4. **audit_log** - Complete audit trail
5. **rate_limits** - Rate limiting tracking

### New API Endpoints

- `POST /auth/login` - User authentication
- `POST /auth/refresh` - Token refresh
- `POST /auth/api-keys` - Create API key (admin)
- `GET /auth/api-keys` - List API keys
- `DELETE /auth/api-keys/{id}` - Revoke API key
- `POST /auth/users` - Create user (admin)
- `GET /auth/audit-log` - Query audit trail
- `GET /auth/me` - Get current auth info

### Modified API Endpoints

All existing baggage endpoints now require authentication:
- `POST /api/v1/scan` - Requires ops_user or higher
- `POST /api/v1/type-b` - Requires ops_user or higher
- `GET /api/v1/bag/{tag}` - Requires any authenticated user
- `GET /api/v1/bags` - Requires any authenticated user

**Tenant Isolation:** All queries automatically filter by `airline_id`

---

## 🔐 Security Features

### Multi-Tenant Isolation

Each airline's data is completely isolated:
- Separate `airline_id` on all baggage records
- API keys scoped to single airline
- Users scoped to single airline
- Automatic filtering in all queries

### Audit Logging

All authenticated operations are logged:
- Who (user_id or api_key_id)
- What (action and resource)
- When (timestamp)
- Where (IP address)
- Result (success/failure)

### Rate Limiting

- Per API key: 1000 requests/hour
- Per user: 500 requests/hour
- Redis-backed sliding window
- Automatic 429 response with retry-after

### Secure Credential Storage

- API keys: bcrypt hashed (never stored plain)
- Passwords: bcrypt hashed with salt
- JWT: Signed with secret key
- Constant-time comparison for verification

---

## 🧪 Testing

### Run Unit Tests

```bash
pytest tests/test_auth.py -v
```

### Test with Real Database

```bash
NEON_DATABASE_URL=<your_url> pytest tests/test_auth.py -v
```

### Manual Testing Script

```bash
#!/bin/bash
# Save as test_auth_live.sh

API_URL="https://your-app.railway.app"
API_KEY="your_api_key_here"

echo "1. Test health check (public)..."
curl $API_URL/health

echo "\n2. Test authentication required..."
curl $API_URL/api/v1/bags  # Should return 401

echo "\n3. Test API key auth..."
curl -H "X-API-Key: $API_KEY" $API_URL/api/v1/bags

echo "\n4. Test login..."
curl -X POST $API_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@copaair.com","password":"Copa2024!Admin"}'

echo "\n5. Test /me endpoint..."
curl -H "X-API-Key: $API_KEY" $API_URL/auth/me

echo "\n6. Test audit log..."
curl -H "X-API-Key: $API_KEY" "$API_URL/auth/audit-log?limit=10"
```

---

## 📊 Monitoring

### Key Metrics to Track

1. **Authentication Failures**
   ```sql
   SELECT COUNT(*), action, status
   FROM audit_log
   WHERE status = 'failure' AND action IN ('login', 'api_key_auth')
   GROUP BY action, status
   ORDER BY count DESC;
   ```

2. **API Key Usage**
   ```sql
   SELECT name, usage_count, last_used_at
   FROM api_keys
   WHERE airline_id = 1 AND is_active = true
   ORDER BY usage_count DESC;
   ```

3. **Rate Limit Hits**
   ```sql
   SELECT COUNT(*)
   FROM audit_log
   WHERE response_status = 429
   AND timestamp > NOW() - INTERVAL '24 hours';
   ```

4. **Active Users**
   ```sql
   SELECT email, last_login_at
   FROM users
   WHERE airline_id = 1 AND is_active = true
   ORDER BY last_login_at DESC;
   ```

---

## 🚨 Troubleshooting

### Issue: "JWT_SECRET not set"

**Solution:**
```bash
# Generate and set JWT_SECRET
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Add to .env or Railway variables
```

### Issue: "Authentication service unavailable"

**Causes:**
- Database not initialized
- Missing environment variables
- Database connection failed

**Solution:**
```bash
# Check environment variables
echo $NEON_DATABASE_URL
echo $JWT_SECRET
echo $SECRET_KEY

# Test database connection
psql $NEON_DATABASE_URL -c "SELECT 1"
```

### Issue: "API key required"

**Solution:**
- Add `X-API-Key` header to request
- Verify key format: `bagi_<airline>_<random32>`
- Check key is active and not expired

### Issue: "Invalid API key"

**Causes:**
- Key revoked or expired
- Typo in key
- Airline account suspended

**Solution:**
```sql
-- Check API key status
SELECT id, name, is_active, expires_at
FROM api_keys
WHERE key_hash = '<hash>';

-- List active keys
SELECT * FROM api_keys WHERE airline_id = 1 AND is_active = true;
```

### Issue: "Insufficient permissions"

**Solution:**
- Check user/API key role
- Verify endpoint requirements
- Contact admin to upgrade role

---

## 🔄 Migration from Non-Authenticated Version

### Step 1: Backup Current Data

```bash
# Backup baggage data
pg_dump $NEON_DATABASE_URL -t baggage > backup_baggage.sql
pg_dump $NEON_DATABASE_URL -t scan_events > backup_scans.sql
```

### Step 2: Add airline_id Column

```sql
-- Add airline_id to existing tables
ALTER TABLE baggage ADD COLUMN airline_id INTEGER;
ALTER TABLE scan_events ADD COLUMN airline_id INTEGER;
-- ... repeat for other tables

-- Get Copa Airlines ID
SELECT id FROM airlines WHERE code = 'copa';

-- Update all existing records
UPDATE baggage SET airline_id = <copa_id>;
UPDATE scan_events SET airline_id = <copa_id>;
-- ... repeat for other tables

-- Add foreign key constraints
ALTER TABLE baggage
  ADD CONSTRAINT fk_baggage_airline
  FOREIGN KEY (airline_id) REFERENCES airlines(id);
```

### Step 3: Update Application Code

Replace `api_server.py` with `api_server_auth.py`:

```bash
# Backup original
mv api_server.py api_server_original.py

# Use authenticated version
mv api_server_auth.py api_server.py

# Update imports if needed
```

### Step 4: Update Client Applications

All API clients must now include authentication:

```python
# Before
response = requests.get("http://api/bags")

# After
headers = {"X-API-Key": "bagi_copa_..."}
response = requests.get("http://api/bags", headers=headers)
```

---

## 📚 Additional Resources

- **Auth README:** `AUTH_README.md` - Complete API reference
- **API Documentation:** `/docs` - Interactive Swagger UI
- **Code Examples:** `tests/test_auth.py` - Working examples
- **Migration Script:** `migrations/add_auth_tables.sql`
- **Setup Script:** `scripts/setup_copa_auth.py`

---

## 🎯 Next Steps

### Immediate (Pre-December 15 Demo)

1. Deploy authentication system
2. Create API keys for BHS/DCS integrations
3. Create user accounts for Copa team
4. Test all protected endpoints
5. Monitor audit logs

### Short Term (Post-Demo)

1. Add 2FA for admin users
2. Implement OAuth/SSO integration
3. Add email verification flow
4. Set up automated key rotation
5. Implement advanced rate limiting (per endpoint)

### Long Term

1. Add biometric authentication (mobile app)
2. Implement RBAC for specific resources
3. Add IP whitelisting
4. Implement session management
5. Add federated authentication

---

**Deployment Date:** November 14, 2024
**Version:** 1.0.0
**For:** Copa Airlines Baggage Platform
**Contact:** Copa IT Team

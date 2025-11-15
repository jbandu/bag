-- ============================================================================
-- BAGGAGE OPERATIONS PLATFORM - AUTHENTICATION TABLES
-- ============================================================================
-- Version: 1.0.0
-- Date: 2024-11-14
-- Purpose: Multi-tenant authentication with RBAC and audit logging
--
-- Run this migration on your Neon PostgreSQL database
-- ============================================================================

-- Drop tables if they exist (for clean migration)
-- WARNING: This will delete all existing authentication data!
DROP TABLE IF EXISTS rate_limits CASCADE;
DROP TABLE IF EXISTS audit_log CASCADE;
DROP TABLE IF EXISTS api_keys CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS airlines CASCADE;

-- ============================================================================
-- AIRLINES TABLE
-- ============================================================================

CREATE TABLE airlines (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(10) UNIQUE NOT NULL,
    iata_code VARCHAR(3),
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    max_api_keys INTEGER DEFAULT 10,
    max_users INTEGER DEFAULT 50,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_airlines_code ON airlines(code);
CREATE INDEX idx_airlines_status ON airlines(status);

COMMENT ON TABLE airlines IS 'Multi-tenant airline accounts';
COMMENT ON COLUMN airlines.code IS 'Unique airline identifier (lowercase, alphanumeric)';
COMMENT ON COLUMN airlines.iata_code IS 'IATA airline code (e.g., CM for Copa)';
COMMENT ON COLUMN airlines.status IS 'Account status: active, suspended, trial';

-- ============================================================================
-- USERS TABLE
-- ============================================================================

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    airline_id INTEGER NOT NULL REFERENCES airlines(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role VARCHAR(50) NOT NULL DEFAULT 'readonly',
    is_active BOOLEAN DEFAULT true,
    email_verified BOOLEAN DEFAULT false,
    last_login_at TIMESTAMP,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_airline ON users(airline_id);
CREATE INDEX idx_users_active ON users(is_active);

COMMENT ON TABLE users IS 'Dashboard users for JWT authentication';
COMMENT ON COLUMN users.role IS 'User role: system_admin, airline_admin, ops_user, readonly';
COMMENT ON COLUMN users.failed_login_attempts IS 'Failed login counter for account lockout';
COMMENT ON COLUMN users.locked_until IS 'Account locked until this timestamp';

-- ============================================================================
-- API KEYS TABLE
-- ============================================================================

CREATE TABLE api_keys (
    id SERIAL PRIMARY KEY,
    airline_id INTEGER NOT NULL REFERENCES airlines(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'readonly',
    is_active BOOLEAN DEFAULT true,
    created_by INTEGER REFERENCES users(id),
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    usage_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_api_keys_airline ON api_keys(airline_id);
CREATE INDEX idx_api_keys_active ON api_keys(is_active);
CREATE INDEX idx_api_keys_expires ON api_keys(expires_at);

COMMENT ON TABLE api_keys IS 'API keys for system-to-system authentication';
COMMENT ON COLUMN api_keys.key_hash IS 'Bcrypt hash of API key (never store plain keys)';
COMMENT ON COLUMN api_keys.name IS 'Descriptive name for the API key';
COMMENT ON COLUMN api_keys.role IS 'API key role: system_admin, airline_admin, ops_user, readonly';

-- ============================================================================
-- AUDIT LOG TABLE
-- ============================================================================

CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    airline_id INTEGER REFERENCES airlines(id) ON DELETE SET NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    api_key_id INTEGER REFERENCES api_keys(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource VARCHAR(255),
    resource_id VARCHAR(100),
    status VARCHAR(20) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    request_method VARCHAR(10),
    request_path VARCHAR(500),
    response_status INTEGER,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_airline ON audit_log(airline_id);
CREATE INDEX idx_audit_user ON audit_log(user_id);
CREATE INDEX idx_audit_api_key ON audit_log(api_key_id);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX idx_audit_action ON audit_log(action);
CREATE INDEX idx_audit_resource ON audit_log(resource);

COMMENT ON TABLE audit_log IS 'Audit trail for all authenticated operations';
COMMENT ON COLUMN audit_log.action IS 'Action performed (e.g., create_api_key, login, update_bag)';
COMMENT ON COLUMN audit_log.status IS 'Operation status: success, failure';

-- ============================================================================
-- RATE LIMITS TABLE
-- ============================================================================

CREATE TABLE rate_limits (
    id SERIAL PRIMARY KEY,
    airline_id INTEGER NOT NULL REFERENCES airlines(id) ON DELETE CASCADE,
    api_key_id INTEGER REFERENCES api_keys(id) ON DELETE CASCADE,
    window_start TIMESTAMP NOT NULL,
    window_end TIMESTAMP NOT NULL,
    request_count INTEGER DEFAULT 0,
    limit_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_rate_limits_airline ON rate_limits(airline_id);
CREATE INDEX idx_rate_limits_api_key ON rate_limits(api_key_id);
CREATE INDEX idx_rate_limits_window ON rate_limits(window_start, window_end);

COMMENT ON TABLE rate_limits IS 'Rate limiting tracking (hourly windows)';
COMMENT ON COLUMN rate_limits.limit_type IS 'Type of rate limit: api_key, user, global';

-- ============================================================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_airlines_updated_at BEFORE UPDATE ON airlines
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_api_keys_updated_at BEFORE UPDATE ON api_keys
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_rate_limits_updated_at BEFORE UPDATE ON rate_limits
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- INITIAL DATA SEED - COPA AIRLINES
-- ============================================================================

-- Insert Copa Airlines as first tenant
INSERT INTO airlines (name, code, iata_code, status, max_api_keys, max_users)
VALUES ('Copa Airlines', 'copa', 'CM', 'active', 20, 100)
ON CONFLICT (code) DO NOTHING;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify tables were created
SELECT table_name, table_type
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('airlines', 'users', 'api_keys', 'audit_log', 'rate_limits')
ORDER BY table_name;

-- Verify Copa Airlines was inserted
SELECT id, name, code, iata_code, status, created_at
FROM airlines
WHERE code = 'copa';

-- Show all indexes
SELECT
    tablename,
    indexname,
    indexdef
FROM
    pg_indexes
WHERE
    schemaname = 'public'
    AND tablename IN ('airlines', 'users', 'api_keys', 'audit_log', 'rate_limits')
ORDER BY
    tablename, indexname;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ Authentication tables created successfully!';
    RAISE NOTICE '✅ Copa Airlines tenant initialized';
    RAISE NOTICE '📝 Next steps:';
    RAISE NOTICE '   1. Run setup_copa_auth.py to create initial admin user and API key';
    RAISE NOTICE '   2. Update .env with JWT_SECRET and SECRET_KEY';
    RAISE NOTICE '   3. Test authentication endpoints';
END $$;

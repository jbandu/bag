"""
Database schema models for authentication

These models define the database tables for:
- Airlines (multi-tenant support)
- API Keys (system-to-system authentication)
- Users (dashboard authentication)
- Audit Log (compliance and security)
"""
from datetime import datetime
from typing import Optional
from enum import Enum


class UserRole(str, Enum):
    """User and API key roles for RBAC"""
    SYSTEM_ADMIN = "system_admin"      # Full system access
    AIRLINE_ADMIN = "airline_admin"    # Airline-wide admin
    OPS_USER = "ops_user"              # Operations staff
    READONLY = "readonly"              # Read-only access


class AirlineStatus(str, Enum):
    """Airline account status"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"


# SQL queries for table creation (will be in migration file)
CREATE_AIRLINES_TABLE = """
CREATE TABLE IF NOT EXISTS airlines (
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
"""

CREATE_API_KEYS_TABLE = """
CREATE TABLE IF NOT EXISTS api_keys (
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
"""

CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
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
"""

CREATE_AUDIT_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS audit_log (
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
"""

CREATE_RATE_LIMIT_TABLE = """
CREATE TABLE IF NOT EXISTS rate_limits (
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
"""

# Combined migration
CREATE_ALL_AUTH_TABLES = f"""
-- ============================================================================
-- BAGGAGE OPERATIONS PLATFORM - AUTHENTICATION TABLES
-- ============================================================================
-- Version: 1.0.0
-- Date: 2024-11-14
-- Purpose: Multi-tenant authentication with RBAC and audit logging
-- ============================================================================

-- Drop tables if they exist (for clean migration)
DROP TABLE IF EXISTS rate_limits CASCADE;
DROP TABLE IF EXISTS audit_log CASCADE;
DROP TABLE IF EXISTS api_keys CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS airlines CASCADE;

-- Create tables
{CREATE_AIRLINES_TABLE}

{CREATE_USERS_TABLE}

{CREATE_API_KEYS_TABLE}

{CREATE_AUDIT_LOG_TABLE}

{CREATE_RATE_LIMIT_TABLE}

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers for updated_at columns
CREATE TRIGGER update_airlines_updated_at BEFORE UPDATE ON airlines
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_api_keys_updated_at BEFORE UPDATE ON api_keys
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_rate_limits_updated_at BEFORE UPDATE ON rate_limits
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- INITIAL DATA SEED
-- ============================================================================

-- Insert Copa Airlines as first tenant
INSERT INTO airlines (name, code, iata_code, status, max_api_keys, max_users)
VALUES ('Copa Airlines', 'copa', 'CM', 'active', 20, 100)
ON CONFLICT (code) DO NOTHING;

-- ============================================================================
-- PERMISSIONS
-- ============================================================================

-- Grant appropriate permissions (adjust based on your Neon user)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO your_app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO your_app_user;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify tables were created
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('airlines', 'users', 'api_keys', 'audit_log', 'rate_limits')
ORDER BY table_name;

-- Verify Copa Airlines was inserted
SELECT * FROM airlines WHERE code = 'copa';
"""

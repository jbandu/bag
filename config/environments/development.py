"""
Development Configuration

Optimized for local development:
- All external services in mock mode
- Relaxed security (dev secrets OK)
- Verbose logging
- No database required (graceful degradation)
- Fast iteration

Usage:
    export ENV=development
    python api_server_auth.py
"""
from config.base import BaseConfig, Environment


class DevelopmentConfig(BaseConfig):
    """Development environment configuration"""

    # Environment
    environment: Environment = Environment.DEVELOPMENT
    log_level: str = "DEBUG"
    debug: bool = True

    # Security (dev secrets are OK)
    jwt_secret: str = "dev-jwt-secret-not-for-production"
    secret_key: str = "dev-secret-key-not-for-production"

    # All external services in mock mode
    worldtracer_use_mock: bool = True
    twilio_use_mock: bool = True
    sendgrid_use_mock: bool = True

    # Feature flags (all enabled for testing)
    enable_ai_agents: bool = True
    enable_worldtracer: bool = True
    enable_sms_notifications: bool = True
    enable_email_notifications: bool = True
    enable_push_notifications: bool = False
    enable_courier_dispatch: bool = True

    # Fast timeouts for development
    worldtracer_timeout: int = 10

    # Local databases (can be missing - graceful degradation)
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    redis_url: str = "redis://localhost:6379"

    # PostgreSQL optional in development
    # Will use mock data if not present
    # Set NEON_DATABASE_URL in .env to use real DB

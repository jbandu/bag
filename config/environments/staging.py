"""
Staging Configuration

Pre-production testing environment:
- Real databases (Neon, Neo4j Aura, Upstash Redis)
- Real AI processing (Anthropic)
- Mock external notifications (Twilio, SendGrid) to avoid costs
- Real WorldTracer (if available)
- Production-like security
- Comprehensive logging

Usage:
    export ENV=staging
    export NEON_DATABASE_URL=postgresql://...
    export ANTHROPIC_API_KEY=sk-...
    python api_server_auth.py
"""
from config.base import BaseConfig, Environment
from typing import Optional


class StagingConfig(BaseConfig):
    """Staging environment configuration"""

    # Environment
    environment: Environment = Environment.STAGING
    log_level: str = "INFO"
    debug: bool = True  # More verbose errors in staging

    # Security (MUST override via environment variables)
    # jwt_secret: required from env
    # secret_key: required from env

    # Databases (REQUIRED in staging)
    # neon_database_url: required from env
    # neo4j_uri: required from env
    # neo4j_password: required from env
    # redis_url: required from env

    # AI (REQUIRED)
    # anthropic_api_key: required from env

    # External services strategy:
    # - WorldTracer: Use real API if available, otherwise mock
    # - Twilio/SendGrid: Use MOCK to avoid SMS/email costs in testing
    worldtracer_use_mock: bool = False  # Try real API in staging
    twilio_use_mock: bool = True  # Mock to save costs
    sendgrid_use_mock: bool = True  # Mock to save costs

    # Feature flags (all enabled for full testing)
    enable_ai_agents: bool = True
    enable_worldtracer: bool = True
    enable_sms_notifications: bool = True  # Will use mock
    enable_email_notifications: bool = True  # Will use mock
    enable_push_notifications: bool = False
    enable_courier_dispatch: bool = True

    # Production-like timeouts
    worldtracer_timeout: int = 30

    def validate_staging_config(self):
        """
        Validate required staging configuration

        Raises ValueError if critical settings missing
        """
        errors = []

        if not self.has_anthropic_key:
            errors.append("ANTHROPIC_API_KEY is required in staging")

        if not self.has_database:
            errors.append("NEON_DATABASE_URL is required in staging")

        if self.neo4j_password == "password":
            errors.append("NEO4J_PASSWORD must be set in staging")

        if errors:
            error_msg = "Staging configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ValueError(error_msg)

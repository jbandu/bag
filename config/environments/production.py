"""
Production Configuration

Live Copa Airlines environment:
- All real databases
- All real external services
- Strict security validation
- Production secrets required
- Error logging only (no debug)
- Performance optimized

Usage:
    export ENV=production
    export NEON_DATABASE_URL=postgresql://...
    export ANTHROPIC_API_KEY=sk-...
    export WORLDTRACER_API_KEY=...
    export TWILIO_ACCOUNT_SID=...
    export SENDGRID_API_KEY=...
    python api_server_auth.py
"""
from config.base import BaseConfig, Environment


class ProductionConfig(BaseConfig):
    """Production environment configuration"""

    # Environment
    environment: Environment = Environment.PRODUCTION
    log_level: str = "INFO"  # ERROR for less verbosity
    debug: bool = False

    # Security (MUST be set via environment variables - no defaults)
    # jwt_secret: REQUIRED - must not start with "dev-"
    # secret_key: REQUIRED - must not start with "dev-"

    # Databases (ALL REQUIRED)
    # neon_database_url: REQUIRED
    # neo4j_uri: REQUIRED (Neo4j Aura)
    # neo4j_password: REQUIRED
    # redis_url: REQUIRED (Upstash or Railway)

    # AI (REQUIRED)
    # anthropic_api_key: REQUIRED

    # External services (ALL REAL - no mocks)
    worldtracer_use_mock: bool = False
    twilio_use_mock: bool = False
    sendgrid_use_mock: bool = False

    # External service credentials (REQUIRED if feature enabled)
    # worldtracer_api_key: REQUIRED if enable_worldtracer=True
    # twilio_account_sid: REQUIRED if enable_sms_notifications=True
    # sendgrid_api_key: REQUIRED if enable_email_notifications=True

    # Feature flags (customize per Copa requirements)
    enable_ai_agents: bool = True
    enable_worldtracer: bool = True
    enable_sms_notifications: bool = True
    enable_email_notifications: bool = True
    enable_push_notifications: bool = False  # Not implemented yet
    enable_courier_dispatch: bool = True

    # Production timeouts
    worldtracer_timeout: int = 30

    # Connection pooling (production-sized)
    postgres_min_connections: int = 10
    postgres_max_connections: int = 50

    def __init__(self, **kwargs):
        """Initialize and validate production config"""
        super().__init__(**kwargs)

        # Automatically validate on initialization
        self.validate_production_config()

        # Additional production-specific validations
        self.validate_external_services()

    def validate_external_services(self):
        """
        Validate external service credentials if features enabled

        Raises ValueError if credentials missing for enabled features
        """
        errors = []

        # WorldTracer validation
        if self.enable_worldtracer and not self.worldtracer_use_mock:
            if self.worldtracer_api_key == "placeholder-key":
                errors.append("WORLDTRACER_API_KEY required when WorldTracer enabled")

        # Twilio validation
        if self.enable_sms_notifications and not self.twilio_use_mock:
            if not self.twilio_account_sid:
                errors.append("TWILIO_ACCOUNT_SID required when SMS enabled")
            if not self.twilio_auth_token:
                errors.append("TWILIO_AUTH_TOKEN required when SMS enabled")
            if not self.twilio_from_number:
                errors.append("TWILIO_FROM_NUMBER required when SMS enabled")

        # SendGrid validation
        if self.enable_email_notifications and not self.sendgrid_use_mock:
            if not self.sendgrid_api_key:
                errors.append("SENDGRID_API_KEY required when email enabled")
            if not self.sendgrid_from_email:
                errors.append("SENDGRID_FROM_EMAIL required when email enabled")

        if errors:
            error_msg = "Production external services validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ValueError(error_msg)

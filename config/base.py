"""
Base Configuration

Provides safe defaults for all configuration values.
Environment-specific configs (dev/staging/prod) override these values.

Design principles:
- All optional fields have safe defaults
- No crashes if env vars missing
- Mock mode enabled by default for safety
- Production mode requires explicit ENV=production
"""
from pydantic_settings import BaseSettings
from typing import Optional
from enum import Enum


class Environment(str, Enum):
    """Environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class BaseConfig(BaseSettings):
    """
    Base configuration with safe defaults

    All optional values have defaults that allow the system to run
    without external services. This enables local development and testing.
    """

    model_config = {"extra": "ignore", "protected_namespaces": ("settings_",)}

    # ============================================================================
    # ENVIRONMENT
    # ============================================================================
    environment: Environment = Environment.DEVELOPMENT
    log_level: str = "INFO"
    debug: bool = False

    # ============================================================================
    # APPLICATION
    # ============================================================================
    api_port: int = 8000
    dashboard_port: int = 8501

    # ============================================================================
    # SECURITY (Required - no defaults)
    # ============================================================================
    # These MUST be set via environment variables
    jwt_secret: str = "dev-jwt-secret-change-in-production"
    secret_key: str = "dev-secret-key-change-in-production"

    # ============================================================================
    # AI MODEL (Required)
    # ============================================================================
    anthropic_api_key: str = ""  # Required in all environments
    model_name: str = "claude-sonnet-4-20250514"
    model_temperature: float = 0.1

    # ============================================================================
    # DATABASES (Optional with defaults)
    # ============================================================================

    # PostgreSQL (Neon)
    neon_database_url: Optional[str] = None
    postgres_min_connections: int = 2
    postgres_max_connections: int = 20

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    neo4j_database: str = "neo4j"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Supabase (deprecated - using Neon instead)
    supabase_url: str = "https://placeholder.supabase.co"
    supabase_key: str = "placeholder-key"
    supabase_service_key: str = "placeholder-service-key"

    # ============================================================================
    # EXTERNAL SERVICES - WorldTracer
    # ============================================================================
    worldtracer_api_url: str = "https://worldtracer-api.example.com"
    worldtracer_api_key: str = "placeholder-key"
    worldtracer_airline_code: str = "CM"
    worldtracer_use_mock: bool = True  # Safe default
    worldtracer_timeout: int = 30

    # ============================================================================
    # EXTERNAL SERVICES - Communication
    # ============================================================================

    # Twilio SMS
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_from_number: Optional[str] = None
    twilio_use_mock: bool = True  # Safe default

    # SendGrid Email
    sendgrid_api_key: Optional[str] = None
    sendgrid_from_email: Optional[str] = None
    sendgrid_from_name: str = "Copa Airlines Baggage Services"
    sendgrid_use_mock: bool = True  # Safe default

    # Firebase (Push Notifications)
    firebase_credentials_path: Optional[str] = None

    # ============================================================================
    # EXTERNAL SERVICES - Courier
    # ============================================================================
    courier_api_url: Optional[str] = None
    courier_api_key: Optional[str] = None

    # ============================================================================
    # SITA MESSAGING
    # ============================================================================
    sita_type_b_endpoint: str = "https://sita-gateway.example.com"
    sita_airline_code: str = "CMXH"

    # ============================================================================
    # OPERATIONAL SETTINGS
    # ============================================================================

    # Risk thresholds
    high_risk_threshold: float = 0.7
    critical_risk_threshold: float = 0.9
    auto_dispatch_threshold: float = 0.8

    # Timing
    mct_buffer_minutes: int = 15
    scan_gap_warning_minutes: int = 30

    # Compensation
    montreal_convention_max_usd: float = 1500.0

    # ============================================================================
    # FEATURE FLAGS
    # ============================================================================
    enable_ai_agents: bool = True
    enable_worldtracer: bool = True
    enable_sms_notifications: bool = True
    enable_email_notifications: bool = True
    enable_push_notifications: bool = False
    enable_courier_dispatch: bool = True

    # ============================================================================
    # COPA AIRLINES SPECIFIC
    # ============================================================================
    copa_airline_id: int = 1
    copa_hub_airport: str = "PTY"
    copa_customer_service_phone: str = "+507-217-2672"
    copa_baggage_email: str = "baggage@copaair.com"

    # ============================================================================
    # HELPER PROPERTIES
    # ============================================================================

    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.environment == Environment.DEVELOPMENT

    @property
    def is_staging(self) -> bool:
        """Check if running in staging mode"""
        return self.environment == Environment.STAGING

    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.environment == Environment.PRODUCTION

    @property
    def use_mocks(self) -> bool:
        """
        Check if mocks should be used

        Returns True if ANY external service is in mock mode
        """
        return (
            self.worldtracer_use_mock or
            self.twilio_use_mock or
            self.sendgrid_use_mock
        )

    @property
    def has_database(self) -> bool:
        """Check if PostgreSQL database is configured"""
        return self.neon_database_url is not None

    @property
    def has_anthropic_key(self) -> bool:
        """Check if Anthropic API key is configured"""
        return bool(self.anthropic_api_key and self.anthropic_api_key != "")

    def validate_production_config(self):
        """
        Validate that all required production settings are present

        Raises ValueError if critical settings are missing in production
        """
        if not self.is_production:
            return

        errors = []

        # Critical secrets
        if self.jwt_secret.startswith("dev-"):
            errors.append("JWT_SECRET must be set to production value")

        if self.secret_key.startswith("dev-"):
            errors.append("SECRET_KEY must be set to production value")

        if not self.has_anthropic_key:
            errors.append("ANTHROPIC_API_KEY is required in production")

        if not self.has_database:
            errors.append("NEON_DATABASE_URL is required in production")

        # External services should not be in mock mode in production
        if self.worldtracer_use_mock:
            errors.append("WorldTracer should not use mock mode in production")

        if self.twilio_use_mock and self.enable_sms_notifications:
            errors.append("Twilio should not use mock mode in production if SMS enabled")

        if self.sendgrid_use_mock and self.enable_email_notifications:
            errors.append("SendGrid should not use mock mode in production if email enabled")

        if errors:
            error_msg = "Production configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ValueError(error_msg)


# Module-level function to load config from environment variables
def load_base_config() -> BaseConfig:
    """
    Load base configuration from environment variables

    Returns:
        BaseConfig instance with values from environment
    """
    import os

    # Load from .env file if it exists (development mode)
    if os.path.exists(".env"):
        return BaseConfig(_env_file=".env", _env_file_encoding="utf-8")
    else:
        return BaseConfig()

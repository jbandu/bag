"""
Application configuration management
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings from environment variables"""

    model_config = {"extra": "ignore", "protected_namespaces": ("settings_",)}

    # AI Model Configuration
    anthropic_api_key: str
    model_name: str = "claude-sonnet-4-20250514"
    model_temperature: float = 0.1

    # Database Configuration (Optional for initial deployment)
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    # PostgreSQL (Neon) - Primary database for Railway
    neon_database_url: Optional[str] = None

    supabase_url: str = "https://placeholder.supabase.co"
    supabase_key: str = "placeholder-key"
    supabase_service_key: str = "placeholder-service-key"

    redis_url: str = "redis://localhost:6379"

    # WorldTracer Integration (Optional)
    worldtracer_api_url: str = "https://worldtracer-api.example.com"
    worldtracer_api_key: str = "placeholder-key"
    worldtracer_airline_code: str = "CM"

    # SITA Messaging (Optional)
    sita_type_b_endpoint: str = "https://sita-gateway.example.com"
    sita_airline_code: str = "CMXH"
    
    # Communication Services
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_from_number: Optional[str] = None
    
    sendgrid_api_key: Optional[str] = None
    sendgrid_from_email: Optional[str] = None
    
    firebase_credentials_path: Optional[str] = None
    
    # Courier Services
    courier_api_url: Optional[str] = None
    courier_api_key: Optional[str] = None
    
    # Application Settings
    environment: str = "development"
    log_level: str = "INFO"
    api_port: int = 8000
    dashboard_port: int = 8501
    
    # Risk Thresholds
    high_risk_threshold: float = 0.7
    critical_risk_threshold: float = 0.9
    auto_dispatch_threshold: float = 0.8
    
    # Operational Settings
    mct_buffer_minutes: int = 15
    scan_gap_warning_minutes: int = 30
    montreal_convention_max_usd: float = 1500.0


# Global settings instance
# In production (Railway), environment variables are set directly
# In development, load from .env file if it exists
import os
if os.path.exists(".env"):
    settings = Settings(_env_file=".env", _env_file_encoding="utf-8")
else:
    settings = Settings()  # Load from environment variables only

"""
Configuration Module

Environment-aware configuration loading.

Loads config based on ENV environment variable:
- ENV=development -> DevelopmentConfig (mock services, relaxed security)
- ENV=staging -> StagingConfig (real DBs, mock notifications)
- ENV=production -> ProductionConfig (all real, strict validation)

If ENV not set, defaults to development.

Usage:
    from config import config

    if config.is_production:
        # Production-specific logic
        pass

    if config.use_mocks:
        # Use mock services
        pass
"""
import os
from loguru import logger

from config.base import BaseConfig, Environment
from config.environments.development import DevelopmentConfig
from config.environments.staging import StagingConfig
from config.environments.production import ProductionConfig


def load_config() -> BaseConfig:
    """
    Load configuration based on ENV environment variable

    Environment variable priority:
    1. ENV=production � ProductionConfig
    2. ENV=staging � StagingConfig
    3. ENV=development � DevelopmentConfig
    4. Not set � DevelopmentConfig (safe default)

    Returns:
        Appropriate config instance for current environment

    Raises:
        ValueError: If production config validation fails
    """
    env = os.getenv("ENV", "development").lower()

    # Log which environment we're loading
    logger.info(f"Loading configuration for environment: {env}")

    try:
        if env == "production":
            config = ProductionConfig()
            logger.info(" Production configuration loaded and validated")

        elif env == "staging":
            config = StagingConfig()
            # Validate staging config
            config.validate_staging_config()
            logger.info(" Staging configuration loaded and validated")

        else:  # development or any other value
            config = DevelopmentConfig()
            logger.info(" Development configuration loaded (mock mode enabled)")

        # Log key config info
        logger.info(f"Environment: {config.environment.value}")
        logger.info(f"API Port: {config.api_port}")
        logger.info(f"Log Level: {config.log_level}")
        logger.info(f"Database: {'Configured' if config.has_database else 'Not configured (will gracefully degrade)'}")
        logger.info(f"Anthropic API: {'Configured' if config.has_anthropic_key else 'Missing'}")
        logger.info(f"Using mocks: {config.use_mocks}")

        if config.use_mocks:
            logger.info("<� External services in MOCK mode:")
            if config.worldtracer_use_mock:
                logger.info("  - WorldTracer: MOCK")
            if config.twilio_use_mock:
                logger.info("  - Twilio SMS: MOCK")
            if config.sendgrid_use_mock:
                logger.info("  - SendGrid Email: MOCK")

        return config

    except ValueError as e:
        logger.error(f"L Configuration validation failed: {e}")
        raise
    except Exception as e:
        logger.error(f"L Failed to load configuration: {e}")
        raise


# Global config instance
# Load once when module is imported
config = load_config()

# Export commonly used items
__all__ = [
    "config",
    "BaseConfig",
    "Environment",
    "DevelopmentConfig",
    "StagingConfig",
    "ProductionConfig"
]

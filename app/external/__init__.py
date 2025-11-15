"""
External Services Integration Module

Provides integration with external APIs and services:
- WorldTracer (SITA) - Lost baggage tracking
- Twilio - SMS notifications
- SendGrid - Email notifications

All services support both production and mock modes via feature flags.
"""

from app.external.worldtracer import WorldTracerClient
from app.external.twilio_client import TwilioClient
from app.external.sendgrid_client import SendGridClient
from app.external.manager import ExternalServicesManager

__all__ = [
    "WorldTracerClient",
    "TwilioClient",
    "SendGridClient",
    "ExternalServicesManager"
]

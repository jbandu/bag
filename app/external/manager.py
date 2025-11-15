"""
External Services Manager

Unified manager for all external service integrations.

Features:
- Centralized initialization and configuration
- Health checks for all services
- Graceful degradation
- Feature flag support
"""
from typing import Dict, Any
from loguru import logger
import asyncio

from app.external.worldtracer import WorldTracerClient
from app.external.twilio_client import TwilioClient
from app.external.sendgrid_client import SendGridClient


class ExternalServicesManager:
    """
    Unified manager for external services

    Manages:
    - WorldTracer API (baggage tracking)
    - Twilio SMS (notifications)
    - SendGrid Email (notifications)

    Features:
    - Centralized initialization
    - Parallel health checks
    - Feature flags for mock mode
    - Graceful degradation
    """

    def __init__(
        self,
        # WorldTracer configuration
        worldtracer_api_url: str,
        worldtracer_api_key: str,
        worldtracer_airline_code: str,
        worldtracer_use_mock: bool = False,

        # Twilio configuration
        twilio_account_sid: str = None,
        twilio_auth_token: str = None,
        twilio_from_number: str = None,
        twilio_use_mock: bool = False,

        # SendGrid configuration
        sendgrid_api_key: str = None,
        sendgrid_from_email: str = None,
        sendgrid_from_name: str = "Copa Airlines Baggage Services",
        sendgrid_use_mock: bool = False
    ):
        """
        Initialize external services manager

        Args:
            WorldTracer args: API URL, key, airline code, mock flag
            Twilio args: Account SID, auth token, from number, mock flag
            SendGrid args: API key, from email, from name, mock flag
        """
        # Initialize WorldTracer client
        self.worldtracer = WorldTracerClient(
            api_url=worldtracer_api_url,
            api_key=worldtracer_api_key,
            airline_code=worldtracer_airline_code,
            use_mock=worldtracer_use_mock
        )

        # Initialize Twilio client
        self.twilio = TwilioClient(
            account_sid=twilio_account_sid,
            auth_token=twilio_auth_token,
            from_number=twilio_from_number,
            use_mock=twilio_use_mock
        )

        # Initialize SendGrid client
        self.sendgrid = SendGridClient(
            api_key=sendgrid_api_key,
            from_email=sendgrid_from_email,
            from_name=sendgrid_from_name,
            use_mock=sendgrid_use_mock
        )

        logger.info("ExternalServicesManager initialized")

    async def connect_all(self):
        """
        Connect to all external services in parallel

        Gracefully handles connection failures - services continue in mock mode
        """
        logger.info("Connecting to external services...")

        # Connect to all services in parallel
        results = await asyncio.gather(
            self.worldtracer.connect(),
            self.twilio.connect(),
            self.sendgrid.connect(),
            return_exceptions=True
        )

        # Log any connection errors (but don't fail)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                service_name = ["WorldTracer", "Twilio", "SendGrid"][i]
                logger.warning(f"⚠️ {service_name} connection error (continuing with mock): {result}")

        logger.success("✅ External services initialized")

    async def disconnect_all(self):
        """Disconnect from all external services"""
        logger.info("Disconnecting from external services...")

        await asyncio.gather(
            self.worldtracer.disconnect(),
            self.twilio.disconnect(),
            self.sendgrid.disconnect(),
            return_exceptions=True
        )

        logger.info("External services disconnected")

    async def health_check_all(self) -> Dict[str, Any]:
        """
        Check health of all external services in parallel

        Returns:
            {
                "status": "healthy" | "degraded" | "unhealthy",
                "healthy": bool,
                "services": {
                    "worldtracer": {...},
                    "twilio": {...},
                    "sendgrid": {...}
                },
                "summary": {
                    "total_services": 3,
                    "healthy_services": 2,
                    "mock_services": 1,
                    "unhealthy_services": 0
                }
            }
        """
        # Run all health checks in parallel
        worldtracer_health, twilio_health, sendgrid_health = await asyncio.gather(
            self.worldtracer.health_check(),
            self.twilio.health_check(),
            self.sendgrid.health_check(),
            return_exceptions=True
        )

        # Handle exceptions
        if isinstance(worldtracer_health, Exception):
            worldtracer_health = {
                "status": "unhealthy",
                "healthy": False,
                "error": str(worldtracer_health)
            }

        if isinstance(twilio_health, Exception):
            twilio_health = {
                "status": "unhealthy",
                "healthy": False,
                "error": str(twilio_health)
            }

        if isinstance(sendgrid_health, Exception):
            sendgrid_health = {
                "status": "unhealthy",
                "healthy": False,
                "error": str(sendgrid_health)
            }

        # Count service statuses
        services = {
            "worldtracer": worldtracer_health,
            "twilio": twilio_health,
            "sendgrid": sendgrid_health
        }

        healthy_count = sum(1 for s in services.values() if s.get("healthy", False))
        mock_count = sum(1 for s in services.values() if s.get("mode") == "mock")
        total_count = len(services)

        # Determine overall status
        # All services healthy (even if mock)
        if healthy_count == total_count:
            if mock_count > 0:
                overall_status = "degraded"  # Healthy but some in mock mode
                overall_healthy = True
            else:
                overall_status = "healthy"
                overall_healthy = True
        elif healthy_count >= 2:  # At least 2/3 services healthy
            overall_status = "degraded"
            overall_healthy = True
        else:
            overall_status = "unhealthy"
            overall_healthy = False

        return {
            "status": overall_status,
            "healthy": overall_healthy,
            "services": services,
            "summary": {
                "total_services": total_count,
                "healthy_services": healthy_count,
                "mock_services": mock_count,
                "unhealthy_services": total_count - healthy_count
            }
        }

    # Convenience methods for common operations

    async def notify_pir_created(
        self,
        passenger_name: str,
        passenger_phone: str,
        passenger_email: str,
        pir_number: str,
        bag_tag: str,
        flight_number: str,
        claim_station: str
    ):
        """
        Send PIR confirmation via SMS and email

        Args:
            Passenger contact info
            PIR details

        Returns:
            {
                "sms": {...},
                "email": {...}
            }
        """
        # Send both notifications in parallel
        sms_result, email_result = await asyncio.gather(
            self.twilio.send_sms(
                to_number=passenger_phone,
                message=f"Copa Airlines: Your baggage report {pir_number} has been filed for bag {bag_tag} on flight {flight_number}. We're working to locate it.",
                bag_tag=bag_tag
            ),
            self.sendgrid.send_pir_confirmation(
                to_email=passenger_email,
                passenger_name=passenger_name,
                pir_number=pir_number,
                bag_tag=bag_tag,
                flight_number=flight_number,
                claim_station=claim_station
            ),
            return_exceptions=True
        )

        return {
            "sms": sms_result if not isinstance(sms_result, Exception) else {"error": str(sms_result)},
            "email": email_result if not isinstance(email_result, Exception) else {"error": str(email_result)}
        }

    async def notify_bag_found(
        self,
        passenger_name: str,
        passenger_phone: str,
        passenger_email: str,
        bag_tag: str,
        location: str,
        pir_number: str
    ):
        """
        Send bag found notification via SMS and email

        Args:
            Passenger contact info
            Bag details

        Returns:
            {
                "sms": {...},
                "email": {...}
            }
        """
        # Send both notifications in parallel
        sms_result, email_result = await asyncio.gather(
            self.twilio.send_bag_found_notification(
                to_number=passenger_phone,
                passenger_name=passenger_name,
                bag_tag=bag_tag,
                location=location,
                pir_number=pir_number
            ),
            self.sendgrid.send_bag_found_notification(
                to_email=passenger_email,
                passenger_name=passenger_name,
                bag_tag=bag_tag,
                location=location,
                pir_number=pir_number
            ),
            return_exceptions=True
        )

        return {
            "sms": sms_result if not isinstance(sms_result, Exception) else {"error": str(sms_result)},
            "email": email_result if not isinstance(email_result, Exception) else {"error": str(email_result)}
        }

    async def notify_delivery(
        self,
        passenger_name: str,
        passenger_phone: str,
        passenger_email: str,
        bag_tag: str,
        delivery_address: str,
        delivery_time: str,
        pir_number: str
    ):
        """
        Send delivery confirmation via SMS and email

        Args:
            Passenger contact info
            Delivery details

        Returns:
            {
                "sms": {...},
                "email": {...}
            }
        """
        # Send both notifications in parallel
        sms_result, email_result = await asyncio.gather(
            self.twilio.send_delivery_notification(
                to_number=passenger_phone,
                passenger_name=passenger_name,
                bag_tag=bag_tag,
                delivery_address=delivery_address,
                estimated_delivery=delivery_time
            ),
            self.sendgrid.send_delivery_confirmation(
                to_email=passenger_email,
                passenger_name=passenger_name,
                bag_tag=bag_tag,
                delivery_address=delivery_address,
                delivery_time=delivery_time,
                pir_number=pir_number
            ),
            return_exceptions=True
        )

        return {
            "sms": sms_result if not isinstance(sms_result, Exception) else {"error": str(sms_result)},
            "email": email_result if not isinstance(email_result, Exception) else {"error": str(email_result)}
        }

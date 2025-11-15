"""
Twilio SMS Client

Provides SMS notification capabilities for passenger communication.

Features:
- Send SMS notifications
- Delivery status tracking
- Mock mode for testing
- Health checks

Use cases:
- Bag found notifications
- Delivery updates
- Exception alerts
- Courier dispatch notifications
"""
from typing import Optional, Dict, Any
from loguru import logger
import time
from datetime import datetime


class TwilioClient:
    """
    Twilio SMS client for passenger notifications

    Features:
    - Send SMS messages
    - Track delivery status
    - Mock mode for development
    - Health monitoring
    """

    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        from_number: Optional[str] = None,
        use_mock: bool = False
    ):
        """
        Initialize Twilio client

        Args:
            account_sid: Twilio account SID
            auth_token: Twilio authentication token
            from_number: Twilio phone number to send from
            use_mock: If True, use mock responses instead of real API
        """
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.use_mock = use_mock or not all([account_sid, auth_token, from_number])

        self._client = None

        if self.use_mock:
            logger.info("TwilioClient initialized in MOCK mode")
        else:
            logger.info(f"TwilioClient initialized (from: {from_number})")

    async def connect(self):
        """Initialize Twilio client"""
        if self.use_mock:
            logger.info("✅ Twilio client connected (MOCK mode)")
            return

        try:
            # Import Twilio SDK only when needed (not in mock mode)
            from twilio.rest import Client

            self._client = Client(self.account_sid, self.auth_token)

            # Test connection by fetching account info
            account = self._client.api.accounts(self.account_sid).fetch()

            logger.success(f"✅ Twilio connected (account: {account.friendly_name})")

        except ImportError:
            logger.warning("⚠️ Twilio SDK not installed - falling back to mock mode")
            logger.info("Install with: pip install twilio")
            self.use_mock = True

        except Exception as e:
            logger.error(f"❌ Twilio connection failed: {e}")
            logger.warning("⚠️ Falling back to mock mode")
            self.use_mock = True

    async def disconnect(self):
        """Close Twilio client"""
        if self._client:
            self._client = None
            logger.info("Twilio client disconnected")

    async def send_sms(
        self,
        to_number: str,
        message: str,
        bag_tag: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send SMS notification

        Args:
            to_number: Recipient phone number (E.164 format: +15551234567)
            message: SMS message body (max 1600 chars)
            bag_tag: Optional bag tag for tracking

        Returns:
            {
                "message_sid": "SM...",
                "status": "queued" | "sent" | "delivered",
                "to": "+15551234567",
                "from": "+15559876543",
                "sent_at": "2024-12-01T10:30:00Z"
            }
        """
        if self.use_mock:
            return await self._send_sms_mock(to_number, message, bag_tag)

        try:
            # Send SMS via Twilio
            twilio_message = self._client.messages.create(
                to=to_number,
                from_=self.from_number,
                body=message
            )

            result = {
                "message_sid": twilio_message.sid,
                "status": twilio_message.status,
                "to": to_number,
                "from": self.from_number,
                "sent_at": datetime.utcnow().isoformat() + "Z",
                "bag_tag": bag_tag
            }

            logger.info(f"✅ SMS sent to {to_number}: {message_sid}")
            return result

        except Exception as e:
            logger.error(f"❌ Failed to send SMS to {to_number}: {e}")
            raise

    async def _send_sms_mock(
        self,
        to_number: str,
        message: str,
        bag_tag: Optional[str]
    ) -> Dict[str, Any]:
        """Mock SMS sending for testing"""
        message_sid = f"SM{int(time.time())}{hash(to_number) % 10000:04d}"

        logger.info(f"🎭 MOCK SMS to {to_number}: {message[:50]}...")

        return {
            "message_sid": message_sid,
            "status": "delivered",
            "to": to_number,
            "from": self.from_number or "+15555551234",
            "sent_at": datetime.utcnow().isoformat() + "Z",
            "bag_tag": bag_tag,
            "mock": True,
            "message_preview": message[:100]
        }

    async def send_bag_found_notification(
        self,
        to_number: str,
        passenger_name: str,
        bag_tag: str,
        location: str,
        pir_number: str
    ) -> Dict[str, Any]:
        """
        Send bag found notification

        Args:
            to_number: Passenger phone number
            passenger_name: Passenger name
            bag_tag: Bag tag number
            location: Where bag was found
            pir_number: PIR reference number

        Returns:
            SMS delivery info
        """
        message = (
            f"Good news {passenger_name}! Your bag ({bag_tag}) has been found at {location}. "
            f"PIR: {pir_number}. We'll contact you shortly about delivery. - Copa Airlines"
        )

        return await self.send_sms(to_number, message, bag_tag)

    async def send_delivery_notification(
        self,
        to_number: str,
        passenger_name: str,
        bag_tag: str,
        delivery_address: str,
        estimated_delivery: str
    ) -> Dict[str, Any]:
        """
        Send delivery notification

        Args:
            to_number: Passenger phone number
            passenger_name: Passenger name
            bag_tag: Bag tag number
            delivery_address: Delivery location
            estimated_delivery: ETA

        Returns:
            SMS delivery info
        """
        message = (
            f"Hi {passenger_name}, your bag ({bag_tag}) is being delivered to {delivery_address}. "
            f"Estimated arrival: {estimated_delivery}. Track at copa.com/baggage - Copa Airlines"
        )

        return await self.send_sms(to_number, message, bag_tag)

    async def send_exception_alert(
        self,
        to_number: str,
        passenger_name: str,
        bag_tag: str,
        issue: str,
        contact_number: str
    ) -> Dict[str, Any]:
        """
        Send exception alert

        Args:
            to_number: Passenger phone number
            passenger_name: Passenger name
            bag_tag: Bag tag number
            issue: Issue description
            contact_number: Support contact

        Returns:
            SMS delivery info
        """
        message = (
            f"{passenger_name}, there's an issue with your bag ({bag_tag}): {issue}. "
            f"Please call {contact_number} for assistance. - Copa Airlines"
        )

        return await self.send_sms(to_number, message, bag_tag)

    async def get_message_status(self, message_sid: str) -> Dict[str, Any]:
        """
        Get SMS delivery status

        Args:
            message_sid: Twilio message SID

        Returns:
            {
                "status": "queued" | "sent" | "delivered" | "failed",
                "error_code": Optional error code,
                "error_message": Optional error message
            }
        """
        if self.use_mock:
            return {
                "message_sid": message_sid,
                "status": "delivered",
                "mock": True
            }

        try:
            message = self._client.messages(message_sid).fetch()

            return {
                "message_sid": message_sid,
                "status": message.status,
                "error_code": message.error_code,
                "error_message": message.error_message
            }

        except Exception as e:
            logger.error(f"Failed to get message status for {message_sid}: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """
        Check Twilio service health

        Returns:
            {
                "status": "healthy" | "unhealthy",
                "healthy": bool,
                "mode": "production" | "mock"
            }
        """
        if self.use_mock:
            return {
                "status": "healthy",
                "healthy": True,
                "mode": "mock",
                "message": "Mock mode - no real SMS sent"
            }

        try:
            if not self._client:
                return {
                    "status": "disconnected",
                    "healthy": False,
                    "error": "Client not connected"
                }

            # Fetch account to verify connection
            account = self._client.api.accounts(self.account_sid).fetch()

            return {
                "status": "healthy",
                "healthy": True,
                "mode": "production",
                "account_name": account.friendly_name,
                "from_number": self.from_number
            }

        except Exception as e:
            logger.error(f"Twilio health check failed: {e}")
            return {
                "status": "unhealthy",
                "healthy": False,
                "error": str(e),
                "mode": "production"
            }

    @property
    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self.use_mock or self._client is not None

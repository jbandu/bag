"""
SendGrid Email Client

Provides email notification capabilities for passenger communication.

Features:
- Send email notifications
- HTML email templates
- Delivery tracking
- Mock mode for testing
- Health checks

Use cases:
- PIR confirmations
- Bag found notifications
- Delivery confirmations
- Compensation claims
- Customer support communications
"""
from typing import Optional, Dict, Any, List
from loguru import logger
import time
from datetime import datetime


class SendGridClient:
    """
    SendGrid email client for passenger notifications

    Features:
    - Send HTML and plain text emails
    - Template support
    - Delivery tracking
    - Mock mode for development
    - Health monitoring
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: str = "Copa Airlines Baggage Services",
        use_mock: bool = False
    ):
        """
        Initialize SendGrid client

        Args:
            api_key: SendGrid API key
            from_email: Sender email address
            from_name: Sender display name
            use_mock: If True, use mock responses instead of real API
        """
        self.api_key = api_key
        self.from_email = from_email
        self.from_name = from_name
        self.use_mock = use_mock or not all([api_key, from_email])

        self._client = None

        if self.use_mock:
            logger.info("SendGridClient initialized in MOCK mode")
        else:
            logger.info(f"SendGridClient initialized (from: {from_email})")

    async def connect(self):
        """Initialize SendGrid client"""
        if self.use_mock:
            logger.info("✅ SendGrid client connected (MOCK mode)")
            return

        try:
            # Import SendGrid SDK only when needed (not in mock mode)
            from sendgrid import SendGridAPIClient

            self._client = SendGridAPIClient(api_key=self.api_key)

            # Test connection by validating API key
            # Note: SendGrid doesn't have a health endpoint, so we just create the client

            logger.success("✅ SendGrid connected")

        except ImportError:
            logger.warning("⚠️ SendGrid SDK not installed - falling back to mock mode")
            logger.info("Install with: pip install sendgrid")
            self.use_mock = True

        except Exception as e:
            logger.error(f"❌ SendGrid connection failed: {e}")
            logger.warning("⚠️ Falling back to mock mode")
            self.use_mock = True

    async def disconnect(self):
        """Close SendGrid client"""
        if self._client:
            self._client = None
            logger.info("SendGrid client disconnected")

    async def send_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        html_content: str,
        plain_text_content: Optional[str] = None,
        bag_tag: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send email notification

        Args:
            to_email: Recipient email address
            to_name: Recipient name
            subject: Email subject
            html_content: HTML email body
            plain_text_content: Plain text fallback
            bag_tag: Optional bag tag for tracking

        Returns:
            {
                "message_id": "...",
                "status": "queued" | "sent",
                "to": "passenger@example.com",
                "subject": "...",
                "sent_at": "2024-12-01T10:30:00Z"
            }
        """
        if self.use_mock:
            return await self._send_email_mock(to_email, to_name, subject, bag_tag)

        try:
            from sendgrid.helpers.mail import Mail, Email, To, Content

            # Create email message
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to_email, to_name),
                subject=subject,
                html_content=Content("text/html", html_content)
            )

            # Add plain text content if provided
            if plain_text_content:
                message.add_content(Content("text/plain", plain_text_content))

            # Send via SendGrid
            response = self._client.send(message)

            # SendGrid returns 202 for accepted
            if response.status_code == 202:
                message_id = response.headers.get('X-Message-Id', f"msg_{int(time.time())}")

                result = {
                    "message_id": message_id,
                    "status": "queued",
                    "to": to_email,
                    "subject": subject,
                    "sent_at": datetime.utcnow().isoformat() + "Z",
                    "bag_tag": bag_tag
                }

                logger.info(f"✅ Email sent to {to_email}: {subject}")
                return result
            else:
                raise Exception(f"SendGrid returned status {response.status_code}")

        except Exception as e:
            logger.error(f"❌ Failed to send email to {to_email}: {e}")
            raise

    async def _send_email_mock(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        bag_tag: Optional[str]
    ) -> Dict[str, Any]:
        """Mock email sending for testing"""
        message_id = f"msg_{int(time.time())}_{hash(to_email) % 10000:04d}"

        logger.info(f"🎭 MOCK EMAIL to {to_email}: {subject}")

        return {
            "message_id": message_id,
            "status": "sent",
            "to": to_email,
            "to_name": to_name,
            "subject": subject,
            "sent_at": datetime.utcnow().isoformat() + "Z",
            "bag_tag": bag_tag,
            "mock": True
        }

    async def send_pir_confirmation(
        self,
        to_email: str,
        passenger_name: str,
        pir_number: str,
        bag_tag: str,
        flight_number: str,
        claim_station: str
    ) -> Dict[str, Any]:
        """
        Send PIR confirmation email

        Args:
            to_email: Passenger email
            passenger_name: Passenger name
            pir_number: PIR reference number
            bag_tag: Bag tag number
            flight_number: Flight number
            claim_station: Where PIR was filed

        Returns:
            Email delivery info
        """
        subject = f"Copa Airlines - Baggage Report {pir_number} Received"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #003a70;">Baggage Irregularity Report Received</h2>

                <p>Dear {passenger_name},</p>

                <p>We have received your baggage irregularity report and are actively working to locate your bag.</p>

                <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <strong>Report Details:</strong><br>
                    PIR Number: <strong>{pir_number}</strong><br>
                    Bag Tag: <strong>{bag_tag}</strong><br>
                    Flight: <strong>{flight_number}</strong><br>
                    Filed at: <strong>{claim_station}</strong>
                </div>

                <p>We will contact you as soon as we have an update on your bag's location.</p>

                <p>You can track your bag status at: <a href="https://copa.com/baggage/{pir_number}">copa.com/baggage/{pir_number}</a></p>

                <p>For immediate assistance, please contact our Baggage Services team at +507-217-2672.</p>

                <p>Thank you for your patience.</p>

                <p style="margin-top: 30px;">
                    Best regards,<br>
                    <strong>Copa Airlines Baggage Services</strong>
                </p>
            </div>
        </body>
        </html>
        """

        plain_text = f"""
        Baggage Irregularity Report Received

        Dear {passenger_name},

        We have received your baggage irregularity report and are actively working to locate your bag.

        Report Details:
        PIR Number: {pir_number}
        Bag Tag: {bag_tag}
        Flight: {flight_number}
        Filed at: {claim_station}

        We will contact you as soon as we have an update on your bag's location.

        Track your bag: https://copa.com/baggage/{pir_number}

        For assistance: +507-217-2672

        Best regards,
        Copa Airlines Baggage Services
        """

        return await self.send_email(to_email, passenger_name, subject, html_content, plain_text, bag_tag)

    async def send_bag_found_notification(
        self,
        to_email: str,
        passenger_name: str,
        bag_tag: str,
        location: str,
        pir_number: str
    ) -> Dict[str, Any]:
        """
        Send bag found notification email

        Args:
            to_email: Passenger email
            passenger_name: Passenger name
            bag_tag: Bag tag number
            location: Where bag was found
            pir_number: PIR reference

        Returns:
            Email delivery info
        """
        subject = f"Good News! Your Bag Has Been Found - {pir_number}"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #28a745;">✓ Your Bag Has Been Found!</h2>

                <p>Dear {passenger_name},</p>

                <p>Great news! We have located your bag and will be arranging delivery shortly.</p>

                <div style="background-color: #d4edda; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #28a745;">
                    <strong>Bag Details:</strong><br>
                    Bag Tag: <strong>{bag_tag}</strong><br>
                    Found at: <strong>{location}</strong><br>
                    PIR: <strong>{pir_number}</strong>
                </div>

                <p>Our team will contact you within the next few hours to arrange delivery to your preferred address.</p>

                <p>Track delivery status: <a href="https://copa.com/baggage/{pir_number}">copa.com/baggage/{pir_number}</a></p>

                <p>Thank you for your patience.</p>

                <p style="margin-top: 30px;">
                    Best regards,<br>
                    <strong>Copa Airlines Baggage Services</strong>
                </p>
            </div>
        </body>
        </html>
        """

        plain_text = f"""
        Your Bag Has Been Found!

        Dear {passenger_name},

        Great news! We have located your bag and will be arranging delivery shortly.

        Bag Details:
        Bag Tag: {bag_tag}
        Found at: {location}
        PIR: {pir_number}

        Our team will contact you within the next few hours to arrange delivery.

        Track delivery: https://copa.com/baggage/{pir_number}

        Best regards,
        Copa Airlines Baggage Services
        """

        return await self.send_email(to_email, passenger_name, subject, html_content, plain_text, bag_tag)

    async def send_delivery_confirmation(
        self,
        to_email: str,
        passenger_name: str,
        bag_tag: str,
        delivery_address: str,
        delivery_time: str,
        pir_number: str
    ) -> Dict[str, Any]:
        """
        Send delivery confirmation email

        Args:
            to_email: Passenger email
            passenger_name: Passenger name
            bag_tag: Bag tag number
            delivery_address: Delivery location
            delivery_time: When delivered
            pir_number: PIR reference

        Returns:
            Email delivery info
        """
        subject = f"Your Bag Has Been Delivered - {pir_number}"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #003a70;">Bag Delivery Confirmed</h2>

                <p>Dear {passenger_name},</p>

                <p>Your bag has been successfully delivered.</p>

                <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <strong>Delivery Details:</strong><br>
                    Bag Tag: <strong>{bag_tag}</strong><br>
                    Delivered to: <strong>{delivery_address}</strong><br>
                    Delivery time: <strong>{delivery_time}</strong><br>
                    PIR: <strong>{pir_number}</strong>
                </div>

                <p>Thank you for flying Copa Airlines. We apologize for any inconvenience caused by the delay.</p>

                <p>For any questions or concerns, please contact us at +507-217-2672.</p>

                <p style="margin-top: 30px;">
                    Best regards,<br>
                    <strong>Copa Airlines Baggage Services</strong>
                </p>
            </div>
        </body>
        </html>
        """

        plain_text = f"""
        Bag Delivery Confirmed

        Dear {passenger_name},

        Your bag has been successfully delivered.

        Delivery Details:
        Bag Tag: {bag_tag}
        Delivered to: {delivery_address}
        Delivery time: {delivery_time}
        PIR: {pir_number}

        Thank you for flying Copa Airlines.

        Questions? Call +507-217-2672

        Best regards,
        Copa Airlines Baggage Services
        """

        return await self.send_email(to_email, passenger_name, subject, html_content, plain_text, bag_tag)

    async def health_check(self) -> Dict[str, Any]:
        """
        Check SendGrid service health

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
                "message": "Mock mode - no real emails sent"
            }

        try:
            if not self._client:
                return {
                    "status": "disconnected",
                    "healthy": False,
                    "error": "Client not connected"
                }

            # SendGrid doesn't have a health endpoint, but we can verify the client exists
            return {
                "status": "healthy",
                "healthy": True,
                "mode": "production",
                "from_email": self.from_email,
                "from_name": self.from_name
            }

        except Exception as e:
            logger.error(f"SendGrid health check failed: {e}")
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

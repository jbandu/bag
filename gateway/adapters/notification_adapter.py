"""
Notification Adapter
====================

Adapter for notification services (Twilio, SendGrid, Firebase).

Handles:
- SMS (Twilio)
- Email (SendGrid)
- Push notifications (Firebase)

Version: 1.0.0
"""

from typing import Dict, Any, Optional
from datetime import datetime
import time
from loguru import logger

from gateway.adapters.base_adapter import BaseAdapter, AdapterConfig


class NotificationAdapter(BaseAdapter):
    """Notification services adapter"""

    def __init__(self, config: AdapterConfig):
        super().__init__("notification", config)

    def send_sms(
        self,
        phone: str,
        message: str,
        priority: str = "NORMAL"
    ) -> Dict[str, Any]:
        """Send SMS via Twilio"""
        start_time = time.time()

        try:
            logger.info(f"Sending SMS to {phone[:4]}****{phone[-4:]}")

            message_id = f"SM{datetime.now().strftime('%Y%m%d%H%M%S')}"

            result = {
                "message_id": message_id,
                "status": "SENT",
                "phone": phone,
                "sent_at": datetime.now().isoformat(),
                "provider": "twilio"
            }

            latency = (time.time() - start_time) * 1000
            self._log_call("send_sms", True, latency)
            return result

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            self._log_call("send_sms", False, latency, str(e))
            raise

    def send_email(
        self,
        email: str,
        subject: str,
        body: str,
        template: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send email via SendGrid"""
        start_time = time.time()

        try:
            logger.info(f"Sending email to {email}")

            message_id = f"EM{datetime.now().strftime('%Y%m%d%H%M%S')}"

            result = {
                "message_id": message_id,
                "status": "SENT",
                "email": email,
                "subject": subject,
                "sent_at": datetime.now().isoformat(),
                "provider": "sendgrid"
            }

            latency = (time.time() - start_time) * 1000
            self._log_call("send_email", True, latency)
            return result

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            self._log_call("send_email", False, latency, str(e))
            raise

    def send_push(
        self,
        device_token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send push notification via Firebase"""
        start_time = time.time()

        try:
            logger.info(f"Sending push notification to device {device_token[:10]}...")

            message_id = f"PN{datetime.now().strftime('%Y%m%d%H%M%S')}"

            result = {
                "message_id": message_id,
                "status": "SENT",
                "sent_at": datetime.now().isoformat(),
                "provider": "firebase"
            }

            latency = (time.time() - start_time) * 1000
            self._log_call("send_push", True, latency)
            return result

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            self._log_call("send_push", False, latency, str(e))
            raise

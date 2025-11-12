"""
Notification Service - SMS, Email, and Push Notifications
Integrates with Twilio (SMS), SendGrid (Email), and Firebase (Push)
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger
from config.settings import settings


class NotificationService:
    """Unified notification service for passenger communications"""

    def __init__(self):
        self.twilio_client = None
        self.sendgrid_client = None
        self.firebase_app = None
        self._initialize_clients()

    def _initialize_clients(self):
        """Lazy initialization of notification clients"""
        # Twilio SMS
        try:
            from twilio.rest import Client
            if hasattr(settings, 'twilio_account_sid') and hasattr(settings, 'twilio_auth_token'):
                self.twilio_client = Client(
                    settings.twilio_account_sid,
                    settings.twilio_auth_token
                )
                logger.info("✅ Twilio SMS client initialized")
        except ImportError:
            logger.warning("⚠️ Twilio not installed - SMS notifications disabled")
        except Exception as e:
            logger.warning(f"⚠️ Twilio initialization failed: {e}")

        # SendGrid Email
        try:
            from sendgrid import SendGridAPIClient
            if hasattr(settings, 'sendgrid_api_key'):
                self.sendgrid_client = SendGridAPIClient(settings.sendgrid_api_key)
                logger.info("✅ SendGrid email client initialized")
        except ImportError:
            logger.warning("⚠️ SendGrid not installed - Email notifications disabled")
        except Exception as e:
            logger.warning(f"⚠️ SendGrid initialization failed: {e}")

        # Firebase Push Notifications
        try:
            import firebase_admin
            from firebase_admin import credentials
            if hasattr(settings, 'firebase_credentials_path'):
                cred = credentials.Certificate(settings.firebase_credentials_path)
                self.firebase_app = firebase_admin.initialize_app(cred)
                logger.info("✅ Firebase push notification client initialized")
        except ImportError:
            logger.warning("⚠️ Firebase not installed - Push notifications disabled")
        except Exception as e:
            logger.warning(f"⚠️ Firebase initialization failed: {e}")

    # ========================================
    # SMS Notifications (Twilio)
    # ========================================

    def send_sms(
        self,
        to_phone: str,
        message: str,
        bag_tag: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send SMS notification via Twilio

        Args:
            to_phone: Recipient phone number (E.164 format: +1234567890)
            message: SMS message content (max 160 chars recommended)
            bag_tag: Associated bag tag
            metadata: Additional metadata

        Returns:
            Dict with status and message ID
        """
        if not self.twilio_client:
            logger.warning("SMS notification skipped - Twilio not configured")
            return {
                "status": "skipped",
                "reason": "twilio_not_configured",
                "channel": "sms"
            }

        try:
            from_phone = getattr(settings, 'twilio_phone_number', None)
            if not from_phone:
                raise ValueError("TWILIO_PHONE_NUMBER not configured")

            # Send SMS
            message_obj = self.twilio_client.messages.create(
                body=message,
                from_=from_phone,
                to=to_phone
            )

            logger.info(f"✅ SMS sent to {to_phone} | SID: {message_obj.sid}")

            return {
                "status": "sent",
                "channel": "sms",
                "message_id": message_obj.sid,
                "to": to_phone,
                "sent_at": datetime.utcnow().isoformat(),
                "bag_tag": bag_tag,
                "metadata": metadata
            }

        except Exception as e:
            logger.error(f"❌ Failed to send SMS to {to_phone}: {str(e)}")
            return {
                "status": "failed",
                "channel": "sms",
                "error": str(e),
                "to": to_phone,
                "bag_tag": bag_tag
            }

    # ========================================
    # Email Notifications (SendGrid)
    # ========================================

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        plain_content: Optional[str] = None,
        bag_tag: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send email notification via SendGrid

        Args:
            to_email: Recipient email address
            subject: Email subject line
            html_content: HTML email body
            plain_content: Plain text fallback
            bag_tag: Associated bag tag
            metadata: Additional metadata

        Returns:
            Dict with status and response
        """
        if not self.sendgrid_client:
            logger.warning("Email notification skipped - SendGrid not configured")
            return {
                "status": "skipped",
                "reason": "sendgrid_not_configured",
                "channel": "email"
            }

        try:
            from sendgrid.helpers.mail import Mail, Email, To, Content

            from_email = getattr(settings, 'sendgrid_from_email', 'noreply@copaair.com')
            from_name = getattr(settings, 'sendgrid_from_name', 'Copa Airlines Baggage Operations')

            message = Mail(
                from_email=Email(from_email, from_name),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )

            if plain_content:
                message.plain_text_content = Content("text/plain", plain_content)

            # Send email
            response = self.sendgrid_client.send(message)

            logger.info(f"✅ Email sent to {to_email} | Status: {response.status_code}")

            return {
                "status": "sent",
                "channel": "email",
                "status_code": response.status_code,
                "to": to_email,
                "subject": subject,
                "sent_at": datetime.utcnow().isoformat(),
                "bag_tag": bag_tag,
                "metadata": metadata
            }

        except Exception as e:
            logger.error(f"❌ Failed to send email to {to_email}: {str(e)}")
            return {
                "status": "failed",
                "channel": "email",
                "error": str(e),
                "to": to_email,
                "bag_tag": bag_tag
            }

    # ========================================
    # Push Notifications (Firebase)
    # ========================================

    def send_push(
        self,
        device_token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        bag_tag: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send push notification via Firebase Cloud Messaging

        Args:
            device_token: FCM device token
            title: Notification title
            body: Notification body
            data: Additional data payload
            bag_tag: Associated bag tag

        Returns:
            Dict with status and message ID
        """
        if not self.firebase_app:
            logger.warning("Push notification skipped - Firebase not configured")
            return {
                "status": "skipped",
                "reason": "firebase_not_configured",
                "channel": "push"
            }

        try:
            from firebase_admin import messaging

            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=data or {},
                token=device_token
            )

            # Send push
            response = messaging.send(message)

            logger.info(f"✅ Push notification sent | Token: {device_token[:10]}... | Response: {response}")

            return {
                "status": "sent",
                "channel": "push",
                "message_id": response,
                "device_token": device_token,
                "sent_at": datetime.utcnow().isoformat(),
                "bag_tag": bag_tag
            }

        except Exception as e:
            logger.error(f"❌ Failed to send push notification: {str(e)}")
            return {
                "status": "failed",
                "channel": "push",
                "error": str(e),
                "device_token": device_token,
                "bag_tag": bag_tag
            }

    # ========================================
    # Multi-Channel Notifications
    # ========================================

    def send_multi_channel(
        self,
        channels: List[str],
        passenger_info: Dict[str, Any],
        notification_type: str,
        bag_data: Dict[str, Any],
        custom_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send notification across multiple channels

        Args:
            channels: List of channels ['sms', 'email', 'push']
            passenger_info: Dict with phone, email, device_token, name
            notification_type: Type of notification (high_risk, delayed, etc.)
            bag_data: Bag information
            custom_message: Optional custom message override

        Returns:
            Dict with results for each channel
        """
        results = {
            "notification_type": notification_type,
            "bag_tag": bag_data.get('bag_tag'),
            "passenger_name": passenger_info.get('name'),
            "channels": {},
            "sent_at": datetime.utcnow().isoformat()
        }

        bag_tag = bag_data.get('bag_tag', 'UNKNOWN')
        passenger_name = passenger_info.get('name', 'Valued Customer')

        # Generate messages based on type
        messages = self._generate_messages(
            notification_type,
            passenger_name,
            bag_data,
            custom_message
        )

        # Send SMS
        if 'sms' in channels and passenger_info.get('phone'):
            results['channels']['sms'] = self.send_sms(
                to_phone=passenger_info['phone'],
                message=messages['sms'],
                bag_tag=bag_tag,
                metadata={'notification_type': notification_type}
            )

        # Send Email
        if 'email' in channels and passenger_info.get('email'):
            results['channels']['email'] = self.send_email(
                to_email=passenger_info['email'],
                subject=messages['email_subject'],
                html_content=messages['email_html'],
                plain_content=messages['email_plain'],
                bag_tag=bag_tag,
                metadata={'notification_type': notification_type}
            )

        # Send Push
        if 'push' in channels and passenger_info.get('device_token'):
            results['channels']['push'] = self.send_push(
                device_token=passenger_info['device_token'],
                title=messages['push_title'],
                body=messages['push_body'],
                data={'bag_tag': bag_tag, 'type': notification_type},
                bag_tag=bag_tag
            )

        # Count successes
        success_count = sum(
            1 for channel_result in results['channels'].values()
            if channel_result.get('status') == 'sent'
        )

        results['success_count'] = success_count
        results['total_channels'] = len(results['channels'])

        return results

    # ========================================
    # Message Templates
    # ========================================

    def _generate_messages(
        self,
        notification_type: str,
        passenger_name: str,
        bag_data: Dict[str, Any],
        custom_message: Optional[str] = None
    ) -> Dict[str, str]:
        """Generate notification messages for different channels"""

        bag_tag = bag_data.get('bag_tag', 'UNKNOWN')
        risk_score = bag_data.get('risk_score', 0)
        current_location = bag_data.get('current_location', 'Unknown')
        destination = bag_data.get('destination', 'Unknown')

        templates = {
            'high_risk': {
                'sms': f"Copa Airlines: Your bag {bag_tag} requires attention. Our team is monitoring it closely. We'll keep you updated.",
                'email_subject': f"Copa Airlines - Baggage Update for {bag_tag}",
                'email_html': self._get_high_risk_email_html(passenger_name, bag_data),
                'email_plain': f"Dear {passenger_name},\n\nWe're closely monitoring your bag {bag_tag}. Our team is taking proactive steps to ensure it reaches {destination} on time.\n\nCurrent status: {current_location}\nRisk level: Attention required\n\nWe'll notify you of any updates.\n\nCopa Airlines Baggage Operations",
                'push_title': "Baggage Update",
                'push_body': f"We're monitoring your bag {bag_tag}. Our team is on it!"
            },
            'delayed': {
                'sms': f"Copa Airlines: Your bag {bag_tag} is delayed but will arrive on the next available flight. We apologize for the inconvenience.",
                'email_subject': f"Copa Airlines - Delayed Baggage Notice for {bag_tag}",
                'email_html': self._get_delayed_email_html(passenger_name, bag_data),
                'email_plain': f"Dear {passenger_name},\n\nYour bag {bag_tag} has been delayed and will arrive on the next available flight to {destination}.\n\nWe sincerely apologize for this inconvenience and are working to expedite delivery.\n\nCopa Airlines Baggage Operations",
                'push_title': "Baggage Delayed",
                'push_body': f"Bag {bag_tag} delayed - arriving on next flight"
            },
            'found': {
                'sms': f"Copa Airlines: Good news! Your bag {bag_tag} has been located and is on its way to {destination}.",
                'email_subject': f"Copa Airlines - Baggage Located: {bag_tag}",
                'email_html': self._get_found_email_html(passenger_name, bag_data),
                'email_plain': f"Dear {passenger_name},\n\nGood news! Your bag {bag_tag} has been located and is being forwarded to {destination}.\n\nThank you for your patience.\n\nCopa Airlines Baggage Operations",
                'push_title': "Baggage Found",
                'push_body': f"Great news! Bag {bag_tag} located and on its way"
            },
            'delivered': {
                'sms': f"Copa Airlines: Your bag {bag_tag} has been delivered. Thank you for flying with us!",
                'email_subject': f"Copa Airlines - Baggage Delivered: {bag_tag}",
                'email_html': self._get_delivered_email_html(passenger_name, bag_data),
                'email_plain': f"Dear {passenger_name},\n\nYour bag {bag_tag} has been successfully delivered.\n\nThank you for flying Copa Airlines!\n\nCopa Airlines Baggage Operations",
                'push_title': "Baggage Delivered",
                'push_body': f"Your bag {bag_tag} has been delivered!"
            }
        }

        # Use custom message if provided
        if custom_message:
            return {
                'sms': custom_message[:160],  # SMS limit
                'email_subject': f"Copa Airlines - Baggage Update for {bag_tag}",
                'email_html': f"<html><body><p>Dear {passenger_name},</p><p>{custom_message}</p><p>Copa Airlines Baggage Operations</p></body></html>",
                'email_plain': f"Dear {passenger_name},\n\n{custom_message}\n\nCopa Airlines Baggage Operations",
                'push_title': "Baggage Update",
                'push_body': custom_message[:100]
            }

        return templates.get(notification_type, templates['high_risk'])

    def _get_high_risk_email_html(self, passenger_name: str, bag_data: Dict[str, Any]) -> str:
        """Generate HTML email for high-risk baggage alert"""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #003865;">Copa Airlines - Baggage Update</h2>
                <p>Dear {passenger_name},</p>
                <p>We're writing to inform you that we're closely monitoring your bag <strong>{bag_data.get('bag_tag')}</strong>.</p>

                <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #856404;">Current Status</h3>
                    <p><strong>Bag Tag:</strong> {bag_data.get('bag_tag')}</p>
                    <p><strong>Current Location:</strong> {bag_data.get('current_location')}</p>
                    <p><strong>Destination:</strong> {bag_data.get('destination', 'Your final destination')}</p>
                    <p><strong>Status:</strong> Attention Required</p>
                </div>

                <p>Our baggage operations team is taking proactive steps to ensure your bag reaches its destination on time. We'll keep you updated on any changes.</p>

                <p>If you have any questions, please don't hesitate to contact us.</p>

                <p>Thank you for your patience and for flying Copa Airlines.</p>

                <p style="margin-top: 30px;">
                    Best regards,<br>
                    <strong>Copa Airlines Baggage Operations Team</strong>
                </p>
            </div>
        </body>
        </html>
        """

    def _get_delayed_email_html(self, passenger_name: str, bag_data: Dict[str, Any]) -> str:
        """Generate HTML email for delayed baggage"""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #003865;">Copa Airlines - Delayed Baggage Notice</h2>
                <p>Dear {passenger_name},</p>
                <p>We regret to inform you that your bag <strong>{bag_data.get('bag_tag')}</strong> has been delayed.</p>

                <div style="background-color: #f8d7da; border-left: 4px solid #dc3545; padding: 15px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #721c24;">Baggage Information</h3>
                    <p><strong>Bag Tag:</strong> {bag_data.get('bag_tag')}</p>
                    <p><strong>Current Location:</strong> {bag_data.get('current_location')}</p>
                    <p><strong>Destination:</strong> {bag_data.get('destination')}</p>
                    <p><strong>Next Available Flight:</strong> As soon as possible</p>
                </div>

                <p>We sincerely apologize for this inconvenience. Your bag will be forwarded on the next available flight and delivered to you as quickly as possible.</p>

                <p>We'll provide updates as your bag progresses toward its destination.</p>

                <p style="margin-top: 30px;">
                    Sincerely,<br>
                    <strong>Copa Airlines Baggage Operations Team</strong>
                </p>
            </div>
        </body>
        </html>
        """

    def _get_found_email_html(self, passenger_name: str, bag_data: Dict[str, Any]) -> str:
        """Generate HTML email for found baggage"""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #003865;">Copa Airlines - Baggage Located!</h2>
                <p>Dear {passenger_name},</p>
                <p>We have great news! Your bag <strong>{bag_data.get('bag_tag')}</strong> has been located.</p>

                <div style="background-color: #d4edda; border-left: 4px solid #28a745; padding: 15px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #155724;">Good News!</h3>
                    <p><strong>Bag Tag:</strong> {bag_data.get('bag_tag')}</p>
                    <p><strong>Current Location:</strong> {bag_data.get('current_location')}</p>
                    <p><strong>Destination:</strong> {bag_data.get('destination')}</p>
                    <p><strong>Status:</strong> Being forwarded to you</p>
                </div>

                <p>Your bag is now being forwarded to {bag_data.get('destination')} and should arrive shortly.</p>

                <p>Thank you for your patience while we located your baggage.</p>

                <p style="margin-top: 30px;">
                    Best regards,<br>
                    <strong>Copa Airlines Baggage Operations Team</strong>
                </p>
            </div>
        </body>
        </html>
        """

    def _get_delivered_email_html(self, passenger_name: str, bag_data: Dict[str, Any]) -> str:
        """Generate HTML email for delivered baggage"""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #003865;">Copa Airlines - Baggage Delivered</h2>
                <p>Dear {passenger_name},</p>
                <p>Your bag <strong>{bag_data.get('bag_tag')}</strong> has been successfully delivered!</p>

                <div style="background-color: #d1ecf1; border-left: 4px solid #17a2b8; padding: 15px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #0c5460;">Delivery Confirmed</h3>
                    <p><strong>Bag Tag:</strong> {bag_data.get('bag_tag')}</p>
                    <p><strong>Delivered:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
                </div>

                <p>Thank you for flying Copa Airlines. We hope to see you again soon!</p>

                <p style="margin-top: 30px;">
                    Safe travels,<br>
                    <strong>Copa Airlines Baggage Operations Team</strong>
                </p>
            </div>
        </body>
        </html>
        """


# Singleton instance
notification_service = NotificationService()

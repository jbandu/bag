# Automated Passenger Notifications

Complete guide to the automated passenger notification system.

## 📱 Overview

The Baggage Operations Platform now includes multi-channel passenger communication capabilities:

- **SMS** via Twilio
- **Email** via SendGrid
- **Push Notifications** via Firebase Cloud Messaging

## 🚀 Quick Start

### Environment Configuration

Add these to your `.env` file:

```env
# Twilio SMS
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+15551234567

# SendGrid Email
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SENDGRID_FROM_EMAIL=noreply@copaair.com
SENDGRID_FROM_NAME=Copa Airlines Baggage Operations

# Firebase Push (optional)
FIREBASE_CREDENTIALS_PATH=/path/to/firebase-credentials.json

# Notification Settings
AUTO_NOTIFY_HIGH_RISK=true
AUTO_NOTIFY_THRESHOLD=0.7
NOTIFICATION_ENABLED=true
```

### Install Dependencies

```bash
pip install twilio sendgrid firebase-admin
```

## 📡 API Endpoints

### 1. Send Single Notification

**Endpoint:** `POST /api/v1/notifications/send`

**Request:**
```json
{
  "bag_tag": "CM123456",
  "passenger_phone": "+15551234567",
  "passenger_email": "passenger@example.com",
  "passenger_name": "John Smith",
  "notification_type": "high_risk",
  "channels": ["sms", "email", "push"],
  "device_token": "firebase_device_token_here"
}
```

**Response:**
```json
{
  "status": "success",
  "notification_result": {
    "notification_type": "high_risk",
    "bag_tag": "CM123456",
    "passenger_name": "John Smith",
    "channels": {
      "sms": {
        "status": "sent",
        "message_id": "SM1234567890",
        "sent_at": "2024-11-12T10:30:00Z"
      },
      "email": {
        "status": "sent",
        "status_code": 202,
        "sent_at": "2024-11-12T10:30:00Z"
      },
      "push": {
        "status": "sent",
        "message_id": "projects/xxx/messages/yyy",
        "sent_at": "2024-11-12T10:30:00Z"
      }
    },
    "success_count": 3,
    "total_channels": 3
  }
}
```

### 2. Send Bulk Notifications

**Endpoint:** `POST /api/v1/notifications/bulk`

**Request:**
```json
{
  "notifications": [
    {
      "bag_tag": "CM123456",
      "passenger_phone": "+15551234567",
      "passenger_email": "passenger1@example.com",
      "passenger_name": "John Smith",
      "notification_type": "high_risk",
      "channels": ["sms", "email"]
    },
    {
      "bag_tag": "CM789012",
      "passenger_email": "passenger2@example.com",
      "passenger_name": "Jane Doe",
      "notification_type": "delayed",
      "channels": ["email"]
    }
  ]
}
```

**Response:**
```json
{
  "status": "completed",
  "total_notifications": 2,
  "successful": 2,
  "failed": 0,
  "results": [
    {
      "index": 0,
      "bag_tag": "CM123456",
      "status": "success",
      "channels_sent": 2,
      "total_channels": 2
    },
    {
      "index": 1,
      "bag_tag": "CM789012",
      "status": "success",
      "channels_sent": 1,
      "total_channels": 1
    }
  ]
}
```

### 3. Get Notification History

**Endpoint:** `GET /api/v1/notifications/history/{bag_tag}?limit=10`

**Response:**
```json
{
  "bag_tag": "CM123456",
  "total_notifications": 3,
  "notifications": [
    {
      "notification_id": "notif_001",
      "bag_tag": "CM123456",
      "passenger_name": "John Smith",
      "message_type": "high_risk",
      "channels": ["sms", "email"],
      "sent_at": "2024-11-12T10:30:00Z",
      "delivery_status": {
        "sms": "delivered",
        "email": "opened"
      }
    }
  ]
}
```

## 📝 Notification Types

### 1. High Risk Alert
Sent when bag risk score exceeds threshold (default: 0.7)

**SMS:** "Copa Airlines: Your bag CM123456 requires attention. Our team is monitoring it closely. We'll keep you updated."

**Email:** Detailed HTML email with current status, location, and next steps

### 2. Delayed Baggage
Sent when bag is delayed but will arrive on next flight

**SMS:** "Copa Airlines: Your bag CM123456 is delayed but will arrive on the next available flight. We apologize for the inconvenience."

### 3. Bag Found
Sent when missing bag is located

**SMS:** "Copa Airlines: Good news! Your bag CM123456 has been located and is on its way to your destination."

### 4. Bag Delivered
Confirmation when bag is successfully delivered

**SMS:** "Copa Airlines: Your bag CM123456 has been delivered. Thank you for flying with us!"

### 5. Custom Message
Send custom notifications with your own message

```json
{
  "notification_type": "custom",
  "custom_message": "Your custom message here"
}
```

## 🎨 Email Templates

All emails include:
- Professional Copa Airlines branding
- Bag tag and current status
- Current location and destination
- Color-coded status boxes (high risk = yellow, delayed = red, found = green, delivered = blue)
- Contact information

### Customizing Templates

Edit templates in `utils/notifications.py`:
- `_get_high_risk_email_html()`
- `_get_delayed_email_html()`
- `_get_found_email_html()`
- `_get_delivered_email_html()`

## ⚙️ Configuration

### Auto-Notifications

Enable automatic notifications for high-risk bags:

```python
# config/settings.py
auto_notify_high_risk = True
auto_notify_threshold = 0.7  # Notify when risk score >= 0.7
notification_enabled = True
```

### Notification Rules

Customize when notifications are sent:

```python
# Send notification if:
# - Risk score >= 0.7 (high risk)
# - Risk score >= 0.9 (critical risk)
# - Bag delayed by > 30 minutes
# - Bag missing for > 2 hours
```

## 🧪 Testing

### Test SMS (Twilio)

```bash
curl -X POST http://localhost:8000/api/v1/notifications/send \
  -H "Content-Type: application/json" \
  -d '{
    "bag_tag": "TEST123",
    "passenger_phone": "+15551234567",
    "passenger_name": "Test Passenger",
    "notification_type": "high_risk",
    "channels": ["sms"]
  }'
```

### Test Email (SendGrid)

```bash
curl -X POST http://localhost:8000/api/v1/notifications/send \
  -H "Content-Type: application/json" \
  -d '{
    "bag_tag": "TEST123",
    "passenger_email": "test@example.com",
    "passenger_name": "Test Passenger",
    "notification_type": "delayed",
    "channels": ["email"]
  }'
```

## 📊 Monitoring

### View Notification Logs

```python
from loguru import logger

# Logs include:
# - Notification sent/failed
# - Channel results (SMS, Email, Push)
# - Message IDs for tracking
# - Delivery timestamps
```

### Metrics

Track notification metrics:
- Total notifications sent
- Success rate by channel
- Average delivery time
- Failed notifications

## 🔒 Security

### Phone Number Format
- Must be E.164 format: `+[country code][number]`
- Example: `+15551234567` (US), `+507612345678` (Panama)

### Email Validation
- Validated by Pydantic
- Bounce handling via SendGrid webhooks

### Rate Limiting
- Twilio: Configurable per account
- SendGrid: Based on plan
- Recommended: Implement application-level rate limiting

## 🚨 Error Handling

### Graceful Degradation

If a service is unavailable:
```json
{
  "channels": {
    "sms": {
      "status": "skipped",
      "reason": "twilio_not_configured"
    },
    "email": {
      "status": "sent",
      "sent_at": "2024-11-12T10:30:00Z"
    }
  }
}
```

### Retry Logic

Failed notifications can be retried:
- Automatic retry for transient errors
- Manual retry via API
- Store failed notifications for later processing

## 💰 Costs

### Twilio SMS
- $0.0075 per SMS (US/Canada)
- $0.05+ per SMS (international)

### SendGrid Email
- Free: 100 emails/day
- Essentials: $19.95/month (50k emails)
- Pro: $89.95/month (1.5M emails)

### Firebase Push
- Free for unlimited messages

## 🔗 Integration Examples

### With Risk Scoring

```python
# Automatically notify when risk exceeds threshold
if bag_risk_score >= settings.auto_notify_threshold:
    notification_service.send_multi_channel(
        channels=['sms', 'email'],
        passenger_info=passenger_data,
        notification_type='high_risk',
        bag_data=bag_info
    )
```

### With WorldTracer PIR

```python
# Notify when PIR is created
if pir_created:
    notification_service.send_multi_channel(
        channels=['email'],
        passenger_info=passenger_data,
        notification_type='delayed',
        bag_data=bag_info
    )
```

## 📞 Support

For notification issues:
- Twilio Status: https://status.twilio.com
- SendGrid Status: https://status.sendgrid.com
- Firebase Status: https://status.firebase.google.com

---

**Number Labs** | AI-Powered Baggage Operations

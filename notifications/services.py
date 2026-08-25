import requests
from django.conf import settings

def send_whatsapp_notification(phone_number: str, message: str):
    """Dispatches WhatsApp messaging using Termii API."""
    url = "https://api.ng.termii.com/api/sms/send"
    formatted_phone = phone_number.replace("+", "").strip()

    payload = {
        "to": formatted_phone,
        "from": settings.TERMII_SENDER_ID,
        "sms": message,
        "type": "plain",
        "channel": "whatsapp",
        "api_key": settings.TERMII_API_KEY,
        "device_id": settings.TERMII_DEVICE_ID
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Termii Notification Error: {e}")
        return None
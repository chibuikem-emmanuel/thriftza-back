import requests
from django.conf import settings

def send_whatsapp_notification(phone_number: str, message: str):
    """Dispatches WhatsApp messaging using Termii API."""
    if not phone_number:
        return None

    url = "https://api.ng.termii.com/api/sms/send"
    
    # Standardize to international formatting without leading symbols/zeros
    formatted_phone = str(phone_number).replace("+", "").strip().lstrip("0")
    if not formatted_phone.startswith("234") and len(formatted_phone) == 10:
        formatted_phone = f"234{formatted_phone}"

    termii_api_key = getattr(settings, 'TERMII_API_KEY', '')
    termii_sender_id = getattr(settings, 'TERMII_SENDER_ID', 'N-Alert')
    termii_device_id = getattr(settings, 'TERMII_DEVICE_ID', None)

    if not termii_api_key:
        print("Termii Notification Warning: TERMII_API_KEY is not set.")
        return None

    payload = {
        "to": formatted_phone,
        "from": termii_sender_id,
        "sms": message,
        "type": "plain",
        "channel": "whatsapp",
        "api_key": termii_api_key,
    }

    if termii_device_id:
        payload["device_id"] = termii_device_id

    try:
        response = requests.post(url, json=payload, timeout=10)
        res_data = response.json()
        print(f"Termii WhatsApp Response ({formatted_phone}): {res_data}")
        return res_data
    except Exception as e:
        print(f"Termii Notification Error: {e}")
        return None
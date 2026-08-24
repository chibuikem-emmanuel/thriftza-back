import os
import requests

TERMII_API_KEY = os.getenv('TERMII_API_KEY')
TERMII_DEVICE_ID = os.getenv('TERMII_DEVICE_ID')
TERMII_BASE_URL = "https://api.ng.termii.com/api/send/message"

def send_termii_whatsapp(to_phone: str, message: str) -> dict:
    """Sends a single WhatsApp message to a customer."""
    payload = {
        "to": to_phone,
        "from": TERMII_DEVICE_ID,
        "option": "whatsapp",
        "sms": message,
        "type": "plain",
        "api_key": TERMII_API_KEY,
    }
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(TERMII_BASE_URL, json=payload, headers=headers, timeout=10)
        return response.json()
    except requests.RequestException as e:
        return {"status": "error", "message": str(e)}

def bulk_send_termii_whatsapp(phone_numbers: list, message: str) -> dict:
    """Iterates over phone numbers to send broadcast messages."""
    results = {"success": [], "failed": []}
    
    for phone in phone_numbers:
        res = send_termii_whatsapp(phone, message)
        if res.get("message") == "Successfully Sent" or res.get("status") == 200:
            results["success"].append(phone)
        else:
            results["failed"].append({"phone": phone, "response": res})
            
    return results
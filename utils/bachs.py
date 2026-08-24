import os
import requests

BACHS_SECRET_KEY = os.getenv('BACHS_SECRET_KEY')
BACHS_API_BASE_URL = os.getenv('BACHS_API_BASE_URL', 'https://api.bachspay.com/v1')

def initialize_bachs_payment(
    amount: float,
    email: str,
    reference: str,
    callback_url: str,
    currency: str = "NGN"
) -> dict:
    """Initializes a transaction session with Bachs Pay."""
    url = f"{BACHS_API_BASE_URL}/transaction/initialize"
    
    headers = {
        "Authorization": f"Bearer {BACHS_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "amount": int(amount * 100),  # Converts NGN to Kobo
        "currency": currency,
        "email": email,
        "reference": reference,
        "callback_url": callback_url
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        return response.json()
    except requests.RequestException as e:
        return {"status": False, "message": str(e)}
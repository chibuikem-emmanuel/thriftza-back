import requests
from django.conf import settings

def initialize_bachs_payment(amount: float, reference: str, email: str, currency: str = "NGN"):
    url = f"{settings.BACHS_BASE_URL}/checkouts"
    headers = {
        "Authorization": f"Bearer {settings.BACHS_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "amount": amount,
        "currency": currency,
        "reference": reference,
        "email": email,
        "redirect_url": f"{settings.FRONTEND_URL}/checkout/verify?reference={reference}",
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Bachs Payment Initialization Error: {e}")
        return {"status": False, "message": str(e)}

def verify_bachs_payment(reference: str):
    url = f"{settings.BACHS_BASE_URL}/checkouts/verify/{reference}"
    headers = {
        "Authorization": f"Bearer {settings.BACHS_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Bachs Payment Verification Error: {e}")
        return {"status": False, "message": str(e)}
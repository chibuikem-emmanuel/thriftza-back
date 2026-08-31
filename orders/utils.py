import os
import urllib.parse
import threading
import resend
from django.conf import settings

RESEND_API_KEY = getattr(settings, 'RESEND_API_KEY', os.getenv('RESEND_API_KEY'))
resend.api_key = RESEND_API_KEY


def build_whatsapp_url(phone_number, message_text):
    """
    Sanitizes phone numbers to international format (e.g. 234...) 
    and constructs a wa.me Click-to-Chat deep link.
    """
    if not phone_number:
        return None

    clean_phone = "".join(filter(str.isdigit, str(phone_number)))

    # Automatically handle local Nigerian 0... format to 234...
    if clean_phone.startswith("0") and len(clean_phone) == 11:
        clean_phone = "234" + clean_phone[1:]

    encoded_msg = urllib.parse.quote(message_text)
    return f"https://wa.me/{clean_phone}?text={encoded_msg}"


def _send_resend_email_task(subject, recipient_list, html_message, plain_message=None):
    if not resend.api_key:
        print("[EMAIL ERROR] RESEND_API_KEY is not configured.")
        return

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'Thriftza <onboarding@resend.dev>')
    params = {"from": from_email, "to": recipient_list, "subject": subject, "html": html_message}
    if plain_message:
        params["text"] = plain_message

    try:
        response = resend.Emails.send(params)
        print(f"[EMAIL SUCCESS] Delivered to {recipient_list}: {response}")
    except Exception as e:
        print(f"[EMAIL ERROR] Failed sending to {recipient_list}: {str(e)}")


def send_email_async(subject, recipient_list, html_message, message=None):
    thread = threading.Thread(
        target=_send_resend_email_task,
        args=(subject, recipient_list, html_message, message)
    )
    thread.daemon = True
    thread.start()
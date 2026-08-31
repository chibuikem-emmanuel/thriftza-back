import os
import threading
import resend
from django.conf import settings

# Retrieve API key from Django settings or environment
RESEND_API_KEY = getattr(settings, 'RESEND_API_KEY', os.getenv('RESEND_API_KEY'))
resend.api_key = RESEND_API_KEY


def _send_resend_email_task(subject, recipient_list, html_message, plain_message=None):
    """
    Internal task executing HTTPS POST to Resend API.
    """
    if not resend.api_key:
        print("[EMAIL ERROR] RESEND_API_KEY is not set.")
        return

    # Use onboarding sender for testing, or set RESEND_FROM_EMAIL in settings
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'Thriftza <onboarding@resend.dev>')

    params = {
        "from": from_email,
        "to": recipient_list,
        "subject": subject,
        "html": html_message,
    }

    if plain_message:
        params["text"] = plain_message

    try:
        response = resend.Emails.send(params)
        print(f"[EMAIL SUCCESS] Sent to {recipient_list}. Response: {response}")
    except Exception as e:
        print(f"[EMAIL FAILURE] Failed sending to {recipient_list}: {str(e)}")


def send_email_async(subject, recipient_list, html_message, message=None):
    """
    Asynchronously triggers email delivery in a separate thread.
    """
    thread = threading.Thread(
        target=_send_resend_email_task,
        args=(subject, recipient_list, html_message, message)
    )
    thread.daemon = True
    thread.start()
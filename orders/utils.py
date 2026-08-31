import threading
from django.core.mail import send_mail
from django.conf import settings

def send_email_async(subject, message, recipient_list, html_message=None, from_email=None):
    """Executes email dispatch inside a background thread to prevent RAM spikes."""
    if not recipient_list:
        return

    sender = from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', getattr(settings, 'EMAIL_HOST_USER', ''))

    def _dispatch():
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=sender,
                recipient_list=recipient_list,
                html_message=html_message,
                fail_silently=True
            )
        except Exception as e:
            print(f"Async Email Dispatch Failed: {e}")

    thread = threading.Thread(target=_dispatch, daemon=True)
    thread.start()
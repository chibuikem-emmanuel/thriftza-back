from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from orders.notifications import send_whatsapp_notification

User = get_user_model()

@receiver(post_save, sender=User)
def send_registration_whatsapp(sender, instance, created, **kwargs):
    if created:
        phone = getattr(instance, 'phone_number', None) or getattr(instance, 'phone', None)
        if phone:
            first_name = instance.first_name or instance.username or "there"
            welcome_msg = (
                f"Welcome to Thriftza, {first_name}!\n\n"
                "Your account has been successfully created. Browse our catalog and start shopping today."
            )
            send_whatsapp_notification(phone, welcome_msg)
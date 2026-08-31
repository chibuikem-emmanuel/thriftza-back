from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings

User = get_user_model()

@receiver(post_save, sender=User)
def send_registration_email(sender, instance, created, **kwargs):
    if created and instance.email:
        first_name = instance.first_name or instance.username or "there"
        subject = "Welcome to Thriftza!"
        
        # Plain-text fallback
        message = (
            f"Hello {first_name},\n\n"
            "Your account has been successfully created at Thriftza! "
            "Explore our latest fashion collections today.\n\n"
            "Best regards,\n"
            "The Thriftza Team"
        )

        # HTML Email Body
        html_message = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
            <h2 style="color: #e53935; text-align: center;">Welcome to Thriftza!</h2>
            <p style="font-size: 16px; color: #333;">Hello <strong>{first_name}</strong>,</p>
            <p style="font-size: 14px; color: #555; line-height: 1.6;">
                Your account has been successfully created. You can now log in, save items to your wishlist, and make purchases smoothly.
            </p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="https://thriftza-59hct6blk-chibuikem-emmanuels-projects.vercel.app/" 
                   style="background-color: #e53935; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                   Start Shopping
                </a>
            </div>
            <p style="font-size: 12px; color: #888; text-align: center;">
                If you did not create this account, please ignore this email.
            </p>
        </div>
        """

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER),
                recipient_list=[instance.email],
                html_message=html_message,
                fail_silently=True
            )
        except Exception as e:
            print(f"Failed to send registration email: {e}")
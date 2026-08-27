import logging

logger = logging.getLogger(__name__)

def send_whatsapp_notification(phone_number: str, message: str) -> bool:
    """
    Utility function to send WhatsApp/SMS notifications to customers upon payment.
    Integrate your provider API (e.g., Twilio, Termii, Infobip) here.
    """
    try:
        # Format or normalize phone number if needed (e.g., ensure international format)
        formatted_phone = phone_number.strip()
        
        # Log outbound message dispatch
        logger.info(f"[NOTIFICATION SENT] To: {formatted_phone} | Message: {message}")
        print(f"--> [Mock SMS/WhatsApp Notification] Sent to {formatted_phone}: {message}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to send notification to {phone_number}: {str(e)}")
        return False
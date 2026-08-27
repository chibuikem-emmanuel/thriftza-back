import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from orders.models import Order
from .models import PaymentTransaction

# Import notification utility with a fallback if needed
try:
    from .utils import send_whatsapp_notification
except ImportError:
    def send_whatsapp_notification(phone_number, message):
        print(f"[Fallback Notification] To: {phone_number} | Msg: {message}")
        return True


class VerifyPaymentView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        reference = request.data.get('reference')
        if not reference:
            return Response({'status': 'FAILED', 'message': 'Reference is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = Order.objects.get(reference=reference)
        except Order.DoesNotExist:
            return Response({'status': 'FAILED', 'message': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

        if order.status == 'PAID':
            return Response({'status': 'SUCCESS', 'message': 'Payment already verified'}, status=status.HTTP_200_OK)

        # Query Bachs API directly to verify payment status
        headers = {
            "Authorization": f"Bearer {settings.BACHS_SECRET_KEY}",
            "Content-Type": "application/json"
        }

        try:
            res = requests.get(
                f"{settings.BACHS_BASE_URL}/checkouts/verify/{reference}",
                headers=headers,
                timeout=15
            ).json()

            payment_status = res.get('data', {}).get('status') or res.get('status')

            if payment_status in ['success', 'successful', True]:
                order.status = 'PAID'
                order.save()

                PaymentTransaction.objects.create(
                    order=order,
                    reference=reference,
                    amount=order.total_amount,
                    status='SUCCESS',
                    raw_response=res
                )

                # Send order notification via phone
                target_phone = order.customer_phone or getattr(order.user, 'phone_number', None)
                if target_phone:
                    msg = f"Payment Successful! Order {reference} of ₦{order.total_amount:,.2f} has been confirmed."
                    try:
                        send_whatsapp_notification(target_phone, msg)
                    except Exception as e:
                        print(f"WhatsApp notification exception: {e}")

                return Response({'status': 'SUCCESS', 'message': 'Payment verified successfully'}, status=status.HTTP_200_OK)
            else:
                order.status = 'FAILED'
                order.save()
                return Response({'status': 'FAILED', 'message': 'Payment failed or pending gateway clearance'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'FAILED', 'message': f"Verification error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
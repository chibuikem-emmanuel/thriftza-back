from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from orders.models import Order
from .models import PaymentTransaction
from .services import verify_bachs_payment
from notifications.services import send_whatsapp_notification

class VerifyPaymentView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        reference = request.data.get('reference')
        if not reference:
            return Response({"error": "Reference is required"}, status=status.HTTP_400_BAD_REQUEST)

        res = verify_bachs_payment(reference)
        payment_status = res.get('status') or res.get('data', {}).get('status')

        try:
            order = Order.objects.get(reference=reference)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

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

            if order.user.phone_number:
                msg = f"Payment Successful! Order {reference} of ₦{order.total_amount:,.2f} completed."
                send_whatsapp_notification(order.user.phone_number, msg)

            return Response({"status": "SUCCESS", "message": "Payment verified"}, status=status.HTTP_200_OK)

        order.status = 'FAILED'
        order.save()
        return Response({"status": "FAILED", "message": "Verification failed"}, status=status.HTTP_400_BAD_REQUEST)
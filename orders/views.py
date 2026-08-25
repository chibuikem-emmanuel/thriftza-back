from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
import uuid
from .models import Order
from .serializers import OrderSerializer
from payments.services import initialize_bachs_payment
from notifications.services import send_whatsapp_notification

class OrderCheckoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        amount = request.data.get('amount')
        if not amount:
            return Response({"error": "Amount is required"}, status=status.HTTP_400_BAD_REQUEST)

        reference = f"THRIFT-{uuid.uuid4().hex[:10].upper()}"
        order = Order.objects.create(
            user=request.user,
            reference=reference,
            total_amount=amount,
            status='PENDING'
        )

        payment_res = initialize_bachs_payment(
            amount=float(amount),
            reference=reference,
            email=request.user.email
        )

        if request.user.phone_number:
            msg = f"Order {reference} generated for ₦{float(amount):,.2f}. Complete payment to process."
            send_whatsapp_notification(request.user.phone_number, msg)

        return Response({
            "order": OrderSerializer(order).data,
            "payment": payment_res
        }, status=status.HTTP_201_CREATED)

class AdminOrderListView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        orders = Order.objects.all().order_by('-created_at')
        return Response(OrderSerializer(orders, many=True).data)
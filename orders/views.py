from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
import uuid
from .models import Order, OrderItem
from .serializers import OrderSerializer, CreateCheckoutSerializer
from payments.services import initialize_bachs_payment
from notifications.services import send_whatsapp_notification

class OrderCheckoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CreateCheckoutSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        amount = serializer.validated_data['amount']
        customer_info = serializer.validated_data.get('customer', {})
        items_data = serializer.validated_data.get('items', [])

        customer_name = customer_info.get('full_name') or f"{request.user.first_name} {request.user.last_name}".strip()
        customer_email = customer_info.get('email') or request.user.email
        customer_phone = customer_info.get('phone') or getattr(request.user, 'phone_number', '')

        reference = f"THRIFT-{uuid.uuid4().hex[:10].upper()}"

        # Initialize Bachs Payment Gateway
        payment_res = initialize_bachs_payment(
            amount=float(amount),
            reference=reference,
            email=customer_email
        )

        checkout_url = (
            payment_res.get('checkout_url')
            or payment_res.get('data', {}).get('checkout_url')
            if isinstance(payment_res, dict) else None
        )

        # Create main Order record
        order = Order.objects.create(
            user=request.user,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            reference=reference,
            total_amount=amount,
            checkout_url=checkout_url,
            status='PENDING'
        )

        # Save order items
        for item in items_data:
            OrderItem.objects.create(
                order=order,
                product_name=item.get('title'),
                unit_price=item.get('price'),
                quantity=item.get('quantity', 1),
                size=item.get('size', '')
            )

        # WhatsApp Notification
        phone_to_notify = customer_phone or getattr(request.user, 'phone_number', None)
        if phone_to_notify:
            msg = f"Order {reference} generated for ₦{float(amount):,.2f}. Complete payment to process."
            try:
                send_whatsapp_notification(phone_to_notify, msg)
            except Exception as e:
                print(f"WhatsApp notification failed: {e}")

        return Response({
            "order": OrderSerializer(order).data,
            "payment": payment_res,
            "checkout_url": checkout_url
        }, status=status.HTTP_201_CREATED)


class AdminOrderListView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        orders = Order.objects.all().order_by('-created_at')
        return Response(OrderSerializer(orders, many=True).data)
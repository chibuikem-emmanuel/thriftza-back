import uuid
from decimal import Decimal
from django.db import transaction
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from utils.bachs import initialize_bachs_payment
from utils.termii import send_termii_whatsapp
from .models import Order, OrderItem
from .serializers import CreateCheckoutSerializer, OrderSerializer


class CreateCheckoutView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = CreateCheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        items_data = data['items']
        total_amount = sum(
            Decimal(str(item['unit_price'])) * item['quantity']
            for item in items_data
        )

        payment_ref = f"TRF-{uuid.uuid4().hex[:10].upper()}"
        user = request.user if request.user.is_authenticated else None

        with transaction.atomic():
            order = Order.objects.create(
                user=user,
                customer_name=data['customer_name'],
                customer_email=data['customer_email'],
                customer_phone=data['customer_phone'],
                total_amount=total_amount,
                payment_reference=payment_ref,
                status='PENDING'
            )

            for item in items_data:
                OrderItem.objects.create(
                    order=order,
                    product_name=item['product_name'],
                    quantity=item['quantity'],
                    unit_price=item['unit_price']
                )

        # Initialize payment gateway (Bachs Pay)
        payment_res = initialize_bachs_payment(
            amount=float(total_amount),
            email=data['customer_email'],
            reference=payment_ref,
            callback_url="http://localhost:3000/checkout/success"
        )

        if payment_res.get('status') is True:
            checkout_url = payment_res['data']['authorization_url']
            order.checkout_url = checkout_url
            order.save()
            return Response(
                {
                    "message": "Checkout initialized successfully",
                    "order_id": str(order.id),
                    "payment_reference": payment_ref,
                    "checkout_url": checkout_url
                },
                status=status.HTTP_201_CREATED
            )

        return Response(
            {"error": "Payment initialization failed", "details": payment_res},
            status=status.HTTP_400_BAD_REQUEST
        )


class BachsWebhookView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        payload = request.data
        event = payload.get('event')
        data = payload.get('data', {})

        if event == 'charge.success':
            reference = data.get('reference')
            try:
                order = Order.objects.get(payment_reference=reference)
                if order.status != 'PAID':
                    order.status = 'PAID'
                    order.save()

                    # Send WhatsApp notification via Termii
                    msg = (
                        f"Hi {order.customer_name}, your order #{str(order.id)[:8]} "
                        f"for NGN {order.total_amount} has been confirmed! Thank you."
                    )
                    send_termii_whatsapp(order.customer_phone, msg)

                return Response({"status": "success"}, status=status.HTTP_200_OK)
            except Order.DoesNotExist:
                return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response({"status": "ignored"}, status=status.HTTP_200_OK)


class UserOrdersListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-created_at')
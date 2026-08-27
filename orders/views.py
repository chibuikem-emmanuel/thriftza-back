import uuid
import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import Order, OrderItem

class OrderCheckoutView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        data = request.data
        items_data = data.get('items', [])
        
        if not items_data:
            return Response({'error': 'No items in order.'}, status=status.HTTP_400_BAD_REQUEST)

        reference = f"THRIFT-{uuid.uuid4().hex[:8].upper()}"

        # 1. Create Order Record
        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            customer_name=data.get('customer_name'),
            customer_email=data.get('customer_email'),
            customer_phone=data.get('customer_phone'),
            shipping_address=data.get('shipping_address'),
            city=data.get('city', 'Lagos'),
            state=data.get('state', 'Lagos State'),
            total_amount=data.get('total_amount'),
            reference=reference,
            status='PENDING'
        )

        for item in items_data:
            OrderItem.objects.create(
                order=order,
                product_id=item['product_id'],
                quantity=item['quantity'],
                price=item['price']
            )

        # 2. Call Bachs Checkout API
        headers = {
            "Authorization": f"Bearer {settings.BACHS_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        
        callback_url = f"{settings.FRONTEND_URL}/checkout/verify"

        payload = {
            "amount": int(float(data.get('total_amount')) * 100),  # Amount in kobo
            "email": data.get('customer_email'),
            "reference": reference,
            "callback_url": callback_url,
            "metadata": {
                "customer_name": data.get('customer_name'),
                "customer_phone": data.get('customer_phone')
            }
        }

        try:
            bachs_response = requests.post(
                f"{settings.BACHS_BASE_URL}/checkouts",
                json=payload,
                headers=headers,
                timeout=15
            )
            res_data = bachs_response.json()

            if bachs_response.status_code in [200, 201] and res_data.get('status') is True:
                checkout_url = res_data['data']['checkout_url']
                return Response({'checkout_url': checkout_url, 'reference': reference}, status=status.HTTP_201_CREATED)
            else:
                order.status = 'FAILED'
                order.save()
                return Response({'error': res_data.get('message', 'Failed to initialize payment gateway')}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            order.status = 'FAILED'
            order.save()
            return Response({'error': f"Connection to payment gateway failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminOrderListView(APIView):
    """View for listing all orders in admin dashboard."""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        orders = Order.objects.all().order_by('-created_at')
        data = []
        for order in orders:
            data.append({
                'id': order.id,
                'reference': order.reference,
                'customer_name': order.customer_name,
                'customer_email': order.customer_email,
                'customer_phone': order.customer_phone,
                'total_amount': str(order.total_amount),
                'status': order.status,
                'created_at': order.created_at.isoformat(),
            })
        return Response(data, status=status.HTTP_200_OK)
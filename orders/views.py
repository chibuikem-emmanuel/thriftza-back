import uuid
import requests
from django.conf import settings
from django.db import transaction
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

        try:
            with transaction.atomic():
                # Build fields dynamically based on model attributes to prevent kwarg errors
                order_kwargs = {
                    'user': request.user if request.user.is_authenticated else None,
                    'customer_name': data.get('customer_name'),
                    'customer_email': data.get('customer_email'),
                    'customer_phone': data.get('customer_phone'),
                    'total_amount': data.get('total_amount'),
                    'reference': reference,
                    'status': 'PENDING'
                }

                # Optional location fields (only assigned if model defines them)
                if hasattr(Order, 'shipping_address'):
                    order_kwargs['shipping_address'] = data.get('shipping_address')
                elif hasattr(Order, 'address'):
                    # Fallback if your model uses 'address' instead
                    full_address = f"{data.get('shipping_address', '')}, {data.get('city', '')}, {data.get('state', '')}".strip(", ")
                    order_kwargs['address'] = full_address

                if hasattr(Order, 'city'):
                    order_kwargs['city'] = data.get('city', 'Lagos')
                if hasattr(Order, 'state'):
                    order_kwargs['state'] = data.get('state', 'Lagos State')

                # 1. Create Order Record
                order = Order.objects.create(**order_kwargs)

                # 2. Create Order Items
                for item in items_data:
                    OrderItem.objects.create(
                        order=order,
                        product_id=item.get('product_id') or item.get('id'),
                        quantity=item.get('quantity', 1),
                        price=item.get('price', 0)
                    )

            # 3. Call Bachs Checkout API
            secret_key = getattr(settings, 'BACHS_SECRET_KEY', None)
            base_url = getattr(settings, 'BACHS_BASE_URL', '')
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')

            headers = {
                "Authorization": f"Bearer {secret_key}",
                "Content-Type": "application/json"
            }
            
            callback_url = f"{frontend_url}/checkout/verify"

            payload = {
                "amount": int(float(data.get('total_amount', 0)) * 100),  # Amount in kobo
                "email": data.get('customer_email'),
                "reference": reference,
                "callback_url": callback_url,
                "metadata": {
                    "customer_name": data.get('customer_name'),
                    "customer_phone": data.get('customer_phone'),
                    "shipping_address": data.get('shipping_address'),
                }
            }

            bachs_response = requests.post(
                f"{base_url}/checkouts",
                json=payload,
                headers=headers,
                timeout=15
            )
            res_data = bachs_response.json()

            if bachs_response.status_code in [200, 201] and (res_data.get('status') is True or 'checkout_url' in res_data.get('data', {})):
                checkout_url = res_data.get('data', {}).get('checkout_url') or res_data.get('checkout_url')
                return Response({'checkout_url': checkout_url, 'reference': reference}, status=status.HTTP_201_CREATED)
            else:
                order.status = 'FAILED'
                order.save()
                return Response({'error': res_data.get('message', 'Failed to initialize payment gateway')}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            if 'order' in locals():
                order.status = 'FAILED'
                order.save()
            return Response({'error': f"Order processing failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
                'customer_name': getattr(order, 'customer_name', ''),
                'customer_email': getattr(order, 'customer_email', ''),
                'customer_phone': getattr(order, 'customer_phone', ''),
                'total_amount': str(order.total_amount),
                'status': order.status,
                'created_at': order.created_at.isoformat() if hasattr(order, 'created_at') else None,
            })
        return Response(data, status=status.HTTP_200_OK)
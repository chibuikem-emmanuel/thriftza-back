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
                # 1. Create Order Record matching Order model fields
                order = Order.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    customer_name=data.get('customer_name'),
                    customer_email=data.get('customer_email'),
                    customer_phone=data.get('customer_phone'),
                    total_amount=data.get('total_amount'),
                    reference=reference,
                    status='PENDING'
                )

                # Extract shipping details from request body
                shipping_address = data.get('shipping_address')
                city = data.get('city', 'Lagos')
                state = data.get('state', 'Lagos State')

                # 2. Create Order Items matching OrderItem model fields
                for item in items_data:
                    product_name = item.get('product_name') or item.get('name') or item.get('title') or f"Product {item.get('id', '')}"
                    unit_price = item.get('unit_price') or item.get('price', 0)

                    OrderItem.objects.create(
                        order=order,
                        product_name=product_name,
                        unit_price=unit_price,
                        quantity=item.get('quantity', 1),
                        size=item.get('size'),
                        shipping_address=shipping_address,
                        city=city,
                        state=state
                    )

            # 3. Call Bachs Checkout API
            secret_key = getattr(settings, 'BACHS_SECRET_KEY', None)
            base_url = (getattr(settings, 'BACHS_BASE_URL', '') or 'https://api.bachs.io/v1').rstrip('/')
            frontend_url = (getattr(settings, 'FRONTEND_URL', '') or 'http://localhost:3000').rstrip('/')

            # Ensure schema is present if user enters a domain without https://
            if not base_url.startswith(('http://', 'https://')):
                base_url = f"https://{base_url}"

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
                    "shipping_address": shipping_address,
                    "city": city,
                    "state": state
                }
            }

            # If base_url already contains checkout endpoint path, call it directly; otherwise append /checkout-sessions
            checkout_endpoint = base_url if "checkout" in base_url else f"{base_url}/checkout-sessions"

            bachs_response = requests.post(
                checkout_endpoint,
                json=payload,
                headers=headers,
                timeout=15
            )
            res_data = bachs_response.json()

            if bachs_response.status_code in [200, 201] and (res_data.get('status') is True or 'checkout_url' in res_data.get('data', {})):
                checkout_url = res_data.get('data', {}).get('checkout_url') or res_data.get('checkout_url')
                order.checkout_url = checkout_url
                order.save(update_fields=['checkout_url'])
                return Response({'checkout_url': checkout_url, 'reference': reference}, status=status.HTTP_201_CREATED)
            else:
                order.status = 'FAILED'
                order.save(update_fields=['status'])
                return Response({'error': res_data.get('message', 'Failed to initialize payment gateway')}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            if 'order' in locals():
                order.status = 'FAILED'
                order.save(update_fields=['status'])
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
                'customer_name': order.customer_name or '',
                'customer_email': order.customer_email or '',
                'customer_phone': order.customer_phone or '',
                'total_amount': str(order.total_amount),
                'checkout_url': order.checkout_url,
                'status': order.status,
                'created_at': order.created_at.isoformat() if order.created_at else None,
            })
        return Response(data, status=status.HTTP_200_OK)
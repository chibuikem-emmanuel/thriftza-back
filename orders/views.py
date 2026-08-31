import traceback
import uuid
import requests
from django.conf import settings
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import Order, OrderItem
from .notifications import send_whatsapp_notification

class OrderCheckoutView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        data = request.data or {}
        items_data = data.get('items', [])
        
        if not items_data:
            return Response({'error': 'No items in order.'}, status=status.HTTP_400_BAD_REQUEST)

        reference = f"THRIFT-{uuid.uuid4().hex[:8].upper()}"

        try:
            with transaction.atomic():
                # 1. Create Order Record
                order = Order.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    customer_name=data.get('customer_name', ''),
                    customer_email=data.get('customer_email', ''),
                    customer_phone=data.get('customer_phone', ''),
                    total_amount=data.get('total_amount', 0),
                    reference=reference,
                    status='PENDING'
                )

                shipping_address = data.get('shipping_address', '')
                city = data.get('city', 'Lagos')
                state = data.get('state', 'Lagos State')

                # 2. Create Order Items
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

            # Send WhatsApp Notification on Order Creation
            customer_phone = data.get('customer_phone', '')
            customer_name = data.get('customer_name', 'Customer')
            try:
                raw_amount_val = float(data.get('total_amount', 0))
                formatted_amount = f"{raw_amount_val:,.2f}"
            except (ValueError, TypeError):
                formatted_amount = "0.00"

            if customer_phone:
                order_msg = (
                    f"Hello {customer_name},\n\n"
                    f"Your order {reference} has been placed!\n"
                    f"Total Amount: NGN {formatted_amount}\n\n"
                    "Please proceed to complete payment."
                )
                send_whatsapp_notification(customer_phone, order_msg)

            # 3. Resolve Bachs API Configuration
            raw_secret = getattr(settings, 'BACHS_SECRET_KEY', None)
            if not raw_secret:
                print("ERROR: BACHS_SECRET_KEY is missing or empty in Django settings.")
                return Response({'error': 'BACHS_SECRET_KEY is missing from environment.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            secret_key = str(raw_secret).strip().strip("'").strip('"')

            raw_base_url = getattr(settings, 'BACHS_BASE_URL', None) or 'https://api.bachs.io/v1'
            base_url = str(raw_base_url).strip().rstrip('/')

            raw_frontend = getattr(settings, 'FRONTEND_URL', None) or 'https://thriftza-59hct6blk-chibuikem-emmanuels-projects.vercel.app'
            frontend_url = str(raw_frontend).strip().rstrip('/')

            if not base_url.startswith(('http://', 'https://')):
                base_url = f"https://{base_url}"

            headers = {
                "Authorization": f"Bearer {secret_key}",
                "Content-Type": "application/json"
            }
            
            callback_url = f"{frontend_url}/checkout/verify"
            payload_amount = f"{raw_amount_val:.2f}"

            # Payload formatted as explicit strings for Bachs validation
            payload = {
                "pricing": {
                    "type": "fixed_price",
                    "currency": "NGN",
                    "amount": payload_amount,
                    "local": {
                        "amount": payload_amount,
                        "currency": "NGN"
                    }
                },
                "reference": reference,
                "callback_url": callback_url,
                "customer": {
                    "email": data.get('customer_email', ''),
                    "name": customer_name,
                    "phone": customer_phone,
                },
                "metadata": {
                    "shipping_address": shipping_address,
                    "city": city,
                    "state": state
                }
            }

            checkout_endpoint = base_url if "checkout" in base_url else f"{base_url}/checkout-sessions"

            bachs_response = requests.post(
                checkout_endpoint,
                json=payload,
                headers=headers,
                timeout=15
            )

            print(f"--- BACHS GATEWAY RESPONSE ---")
            print(f"Status Code: {bachs_response.status_code}")
            print(f"Response Body: {bachs_response.text}")
            print(f"------------------------------")

            res_data = {}
            try:
                res_data = bachs_response.json()
            except Exception:
                res_data = {'message': bachs_response.text or 'Invalid server response'}

            if bachs_response.status_code in [200, 201] and (
                res_data.get('status') is True 
                or 'checkout_url' in res_data.get('data', {}) 
                or 'checkout_url' in res_data 
                or 'url' in res_data
            ):
                checkout_url = (
                    res_data.get('data', {}).get('checkout_url') 
                    or res_data.get('checkout_url') 
                    or res_data.get('url')
                )
                order.checkout_url = checkout_url
                order.save(update_fields=['checkout_url'])
                return Response({'checkout_url': checkout_url, 'reference': reference}, status=status.HTTP_201_CREATED)
            else:
                order.status = 'FAILED'
                order.save(update_fields=['status'])
                error_msg = res_data.get('detail') or res_data.get('message') or res_data.get('error') or res_data
                return Response({'error': f"Gateway error ({bachs_response.status_code}): {error_msg}"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print("!!! INTERNAL SERVER ERROR EXCEPTION !!!")
            traceback.print_exc()
            if 'order' in locals():
                order.status = 'FAILED'
                order.save(update_fields=['status'])
            return Response({'error': f"Order processing failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OrderVerifyView(APIView):
    """Verifies transaction reference and notifies user on successful payment."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, reference):
        try:
            order = Order.objects.get(reference=reference)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

        order.status = 'SUCCESSFUL'
        order.save(update_fields=['status'])

        if order.customer_phone:
            payment_msg = (
                f"Payment Confirmed!\n\n"
                f"Hi {order.customer_name or 'Customer'},\n"
                f"Your payment for Order #{order.reference} was successful.\n"
                f"Amount Paid: NGN {float(order.total_amount):,.2f}\n\n"
                "We are processing your delivery."
            )
            send_whatsapp_notification(order.customer_phone, payment_msg)

        return Response({'status': 'SUCCESSFUL', 'reference': reference}, status=status.HTTP_200_OK)


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
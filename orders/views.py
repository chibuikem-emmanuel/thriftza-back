import traceback
import uuid
import requests
from django.conf import settings
from django.db import transaction
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import Order, OrderItem
from .utils import send_email_async

User = get_user_model()


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

                order_items_html = ""

                for item in items_data:
                    product_name = item.get('product_name') or item.get('name') or item.get('title') or f"Product {item.get('id', '')}"
                    unit_price = item.get('unit_price') or item.get('price', 0)
                    quantity = item.get('quantity', 1)
                    size = item.get('size', 'N/A')

                    OrderItem.objects.create(
                        order=order,
                        product_name=product_name,
                        unit_price=unit_price,
                        quantity=quantity,
                        size=size,
                        shipping_address=shipping_address,
                        city=city,
                        state=state
                    )

                    order_items_html += f"""
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">{product_name} ({size})</td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: center;">{quantity}</td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">NGN {float(unit_price):,.2f}</td>
                    </tr>
                    """

            customer_email = data.get('customer_email', '')
            customer_name = data.get('customer_name', 'Customer')
            
            try:
                raw_amount_val = float(data.get('total_amount', 0))
                formatted_amount = f"{raw_amount_val:,.2f}"
            except (ValueError, TypeError):
                formatted_amount = "0.00"

            if customer_email:
                subject = f"Order Received - #{reference}"
                plain_message = (
                    f"Hello {customer_name},\n\n"
                    f"Your order #{reference} has been created successfully!\n"
                    f"Total Amount: NGN {formatted_amount}\n\n"
                    "Please complete your payment to initiate delivery."
                )

                html_message = f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                    <h2 style="color: #333;">Order Received</h2>
                    <p>Hi <strong>{customer_name}</strong>,</p>
                    <p>Thank you for your order! Your reference code is <strong>{reference}</strong>.</p>
                    <h3>Order Details</h3>
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                        <thead>
                            <tr style="background-color: #f8f8f8;">
                                <th style="padding: 8px; text-align: left;">Item</th>
                                <th style="padding: 8px; text-align: center;">Qty</th>
                                <th style="padding: 8px; text-align: right;">Price</th>
                            </tr>
                        </thead>
                        <tbody>
                            {order_items_html}
                        </tbody>
                    </table>
                    <p style="font-size: 16px; text-align: right;"><strong>Total: NGN {formatted_amount}</strong></p>
                    <p style="color: #666; font-size: 14px;"><strong>Shipping Address:</strong> {shipping_address}, {city}, {state}</p>
                </div>
                """

                send_email_async(
                    subject=subject,
                    message=plain_message,
                    recipient_list=[customer_email],
                    html_message=html_message
                )

            # Gateway Integration
            raw_secret = getattr(settings, 'BACHS_SECRET_KEY', None)
            if not raw_secret:
                return Response({'error': 'BACHS_SECRET_KEY missing.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
            
            payload = {
                "pricing": {
                    "type": "fixed_price",
                    "currency": "NGN",
                    "amount": f"{raw_amount_val:.2f}",
                    "local": {
                        "amount": f"{raw_amount_val:.2f}",
                        "currency": "NGN"
                    }
                },
                "reference": reference,
                "callback_url": f"{frontend_url}/checkout/verify",
                "customer": {
                    "email": customer_email,
                    "name": customer_name,
                    "phone": data.get('customer_phone', ''),
                },
                "metadata": {
                    "shipping_address": shipping_address,
                    "city": city,
                    "state": state
                }
            }

            checkout_endpoint = base_url if "checkout" in base_url else f"{base_url}/checkout-sessions"

            bachs_response = requests.post(checkout_endpoint, json=payload, headers=headers, timeout=10)
            
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
            traceback.print_exc()
            if 'order' in locals():
                order.status = 'FAILED'
                order.save(update_fields=['status'])
            return Response({'error': f"Order processing failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OrderVerifyView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, reference):
        try:
            order = Order.objects.get(reference=reference)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

        order.status = 'SUCCESSFUL'
        order.save(update_fields=['status'])

        if order.customer_email:
            subject = f"Payment Confirmed - Order #{order.reference}"
            plain_message = (
                f"Hi {order.customer_name or 'Customer'},\n\n"
                f"We received your payment for Order #{order.reference}.\n"
                f"Amount Paid: NGN {float(order.total_amount):,.2f}\n\n"
                "We are preparing your items for delivery."
            )

            html_message = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #4caf50; border-radius: 8px;">
                <h2 style="color: #4caf50; text-align: center;">Payment Successful!</h2>
                <p>Hi <strong>{order.customer_name or 'Customer'}</strong>,</p>
                <p>We received your payment of <strong>NGN {float(order.total_amount):,.2f}</strong> for order <strong>#{order.reference}</strong>.</p>
                <p>Your order is being processed for delivery.</p>
            </div>
            """

            send_email_async(
                subject=subject,
                message=plain_message,
                recipient_list=[order.customer_email],
                html_message=html_message
            )

        return Response({'status': 'SUCCESSFUL', 'reference': reference}, status=status.HTTP_200_OK)


class AdminOrderListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        orders = Order.objects.prefetch_related('items').all().order_by('-created_at')
        total_users = User.objects.count()

        data = []
        for order in orders:
            items_payload = [
                {
                    'id': item.id,
                    'product_name': item.product_name,
                    'unit_price': str(item.unit_price),
                    'quantity': item.quantity,
                    'size': item.size,
                    'shipping_address': item.shipping_address,
                    'city': item.city,
                    'state': item.state,
                }
                for item in order.items.all()
            ]

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
                'items': items_payload,
            })

        return Response({
            'total_users': total_users,
            'total_orders': len(data),
            'orders': data
        }, status=status.HTTP_200_OK)


class AdminOrderDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def delete(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
            order.delete()
            return Response({'message': 'Order deleted successfully.'}, status=status.HTTP_200_OK)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
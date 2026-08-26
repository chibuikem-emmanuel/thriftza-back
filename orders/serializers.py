from rest_framework import serializers
from .models import Order, OrderItem

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ('id', 'product_name', 'quantity', 'unit_price', 'size')


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            'id', 'user', 'customer_name', 'customer_email', 'customer_phone',
            'total_amount', 'status', 'reference',
            'checkout_url', 'created_at', 'items'
        )
        read_only_fields = ('reference', 'user', 'created_at')


class CheckoutItemInputSerializer(serializers.Serializer):
    id = serializers.CharField(required=False, allow_blank=True)
    title = serializers.CharField(max_length=255)
    quantity = serializers.IntegerField(min_value=1, default=1)
    price = serializers.DecimalField(max_digits=12, decimal_places=2)
    size = serializers.CharField(max_length=50, required=False, allow_blank=True)


class CreateCheckoutSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    customer = serializers.DictField(required=False)
    items = CheckoutItemInputSerializer(many=True, required=False)
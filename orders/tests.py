from rest_framework import serializers
from .models import Order

class OrderSerializer(serializers.ModelSerializer):
    user_email = serializers.ReadOnlyField(source='user.email')

    class Meta:
        model = Order
        fields = ['id', 'user', 'user_email', 'reference', 'total_amount', 'status', 'created_at']
        read_only_fields = ['reference', 'user']
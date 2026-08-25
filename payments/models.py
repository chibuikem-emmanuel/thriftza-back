from django.db import models
from orders.models import Order

class PaymentTransaction(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='transactions')
    reference = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=50)
    raw_response = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
from django.urls import path
from .views import OrderCheckoutView, AdminOrderListView

urlpatterns = [
    path('checkout/', OrderCheckoutView.as_view(), name='order-checkout'),
    path('admin/orders/', AdminOrderListView.as_view(), name='admin-order-list'),
]
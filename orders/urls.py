from django.urls import path
from .views import OrderCheckoutView, AdminOrderListView

urlpatterns = [
    path('checkout/', OrderCheckoutView.as_view(), name='order_checkout'),
    path('admin/list/', AdminOrderListView.as_view(), name='admin_orders'),
]
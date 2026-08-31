from django.urls import path
from .views import (
    OrderCheckoutView,
    OrderVerifyView,
    AdminOrderListView,
    AdminOrderDetailView,
)

urlpatterns = [
    path('checkout/', OrderCheckoutView.as_view(), name='order-checkout'),
    path('verify/<str:reference>/', OrderVerifyView.as_view(), name='order-verify'),
    path('admin/orders/', AdminOrderListView.as_view(), name='admin-order-list'),
    path('admin/orders/<int:pk>/', AdminOrderDetailView.as_view(), name='admin-order-detail'),
]
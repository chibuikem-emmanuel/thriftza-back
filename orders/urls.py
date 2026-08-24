from django.urls import path
from .views import BachsWebhookView, CreateCheckoutView, UserOrdersListView

urlpatterns = [
    path('checkout/', CreateCheckoutView.as_view(), name='orders_checkout'),
    path('webhook/bachs/', BachsWebhookView.as_view(), name='orders_bachs_webhook'),
    path('my-orders/', UserOrdersListView.as_view(), name='orders_user_list'),
]
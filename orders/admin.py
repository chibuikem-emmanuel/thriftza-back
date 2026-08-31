from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product_name', 'unit_price', 'quantity', 'size', 'shipping_address', 'city', 'state')
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'reference',
        'customer_name',
        'customer_email',
        'customer_phone',
        'total_amount',
        'status',
        'created_at',
    )
    list_filter = ('status', 'created_at')
    search_fields = ('reference', 'customer_email', 'customer_name', 'customer_phone', 'user__email')
    readonly_fields = ('reference', 'created_at', 'checkout_url')
    inlines = [OrderItemInline]
    ordering = ('-created_at',)
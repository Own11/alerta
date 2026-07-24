from django.contrib import admin
from .models import Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'status', 'polar_customer_id', 'cancel_at_period_end', 'current_period_end']
    list_filter = ['status', 'cancel_at_period_end']
    search_fields = ['user__username', 'polar_customer_id', 'polar_subscription_id']

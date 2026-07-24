import uuid
from django.db import models
from django.conf import settings

class Subscription(models.Model):
    """
    Модель подписки Polar для отслеживания статуса оплаты пользователя.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscription')
    polar_customer_id = models.CharField(max_length=255, blank=True, null=True)
    polar_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    polar_product_id = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=50, default='inactive') # active, trialing, past_due, canceled, inactive
    cancel_at_period_end = models.BooleanField(default=False)
    current_period_end = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'billing_subscription'

    def __str__(self):
        return f"Subscription for {self.user.username} ({self.status})"

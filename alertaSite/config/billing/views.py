import json
from django.conf import settings
from django.http import HttpResponse
from rest_framework import views, permissions, status
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from standardwebhooks.webhooks import Webhook
from polar_sdk import Polar

from .models import Subscription
from .subscription_utils import sync_subscription_from_polar, create_customer_portal_session, get_polar_client

User = get_user_model()

class CreateCheckoutSessionView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        plan_type = request.data.get('plan')
        if plan_type not in ['pro', 'business']:
            return Response({"error": "Неверный тарифный план."}, status=status.HTTP_400_BAD_REQUEST)

        price_id = getattr(settings, f'POLAR_{plan_type.upper()}_PRODUCT_ID', '')
        if not price_id or price_id.endswith('_dummy'):
            return Response(
                {"error": "Polar не настроен. Укажите POLAR_* ключи в settings или .env."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        client = get_polar_client()
        if not client:
             return Response({"error": "Polar клиент не настроен."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        sub, _ = Subscription.objects.get_or_create(user=request.user)
        domain_url = request.build_absolute_uri('/')[:-1]

        try:
            # Polar API allows creating checkouts
            checkout = client.checkouts.create(
                product_id=price_id,
                customer_email=None if sub.polar_customer_id else request.user.email,
                success_url=domain_url + '/billing/success/?session_id={CHECKOUT_SESSION_ID}',
                metadata={'user_id': str(request.user.id), 'plan': plan_type},
            )
            return Response({'sessionId': checkout.id, 'url': checkout.url})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CustomerPortalView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        return_url = request.build_absolute_uri('/settings/')
        url = create_customer_portal_session(request.user, return_url)
        if not url:
            return Response(
                {"error": "Портал управления подпиской недоступен. Оформите подписку или настройте Polar."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({'url': url})


class PolarWebhookView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        payload = request.body
        sig_headers = {
            'webhook-id': request.headers.get('webhook-id'),
            'webhook-timestamp': request.headers.get('webhook-timestamp'),
            'webhook-signature': request.headers.get('webhook-signature')
        }
        
        endpoint_secret = getattr(settings, 'POLAR_WEBHOOK_SECRET', '')

        try:
            wh = Webhook(endpoint_secret)
            wh.verify(payload, sig_headers)
        except Exception:
            return HttpResponse(status=400)

        data = json.loads(payload)
        event_type = data.get('type')
        event_data = data.get('data', {})

        if event_type == 'subscription.created':
            # Handle new subscription
            user_id = event_data.get('metadata', {}).get('user_id')
            plan = event_data.get('metadata', {}).get('plan')
            customer_id = event_data.get('customer_id')
            subscription_id = event_data.get('id')
            
            # Subscriptions don't necessarily have plan in metadata if checkout metadata didn't pass it over,
            # but assuming it did or we sync it later via sync_subscription_from_polar
            if subscription_id:
                 sync_subscription_from_polar(subscription_id)
                 
        elif event_type in ['subscription.updated', 'subscription.active', 'subscription.canceled', 'subscription.revoked']:
            subscription_id = event_data.get('id')
            if subscription_id:
                sync_subscription_from_polar(subscription_id)

        return HttpResponse(status=200)

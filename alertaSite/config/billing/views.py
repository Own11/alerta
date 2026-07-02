import stripe
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import views, permissions, status
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .models import Subscription
from .subscription_utils import sync_subscription_from_stripe, create_customer_portal_session

User = get_user_model()
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')


class CreateCheckoutSessionView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        plan_type = request.data.get('plan')
        if plan_type not in ['pro', 'business']:
            return Response({"error": "Неверный тарифный план."}, status=status.HTTP_400_BAD_REQUEST)

        price_id = getattr(settings, f'STRIPE_{plan_type.upper()}_PRICE_ID', '')
        if not price_id or price_id.endswith('_dummy'):
            return Response(
                {"error": "Stripe не настроен. Укажите STRIPE_* ключи в settings или .env."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        sub, _ = Subscription.objects.get_or_create(user=request.user)
        domain_url = request.build_absolute_uri('/')[:-1]

        try:
            checkout_session = stripe.checkout.Session.create(
                customer=sub.stripe_customer_id or None,
                customer_email=None if sub.stripe_customer_id else request.user.email,
                payment_method_types=['card'],
                line_items=[{'price': price_id, 'quantity': 1}],
                mode='subscription',
                success_url=domain_url + '/billing/success/?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=domain_url + '/billing/cancel/',
                metadata={'user_id': str(request.user.id), 'plan': plan_type},
            )
            return Response({'sessionId': checkout_session.id, 'url': checkout_session.url})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CustomerPortalView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        return_url = request.build_absolute_uri('/settings/')
        url = create_customer_portal_session(request.user, return_url)
        if not url:
            return Response(
                {"error": "Портал управления подпиской недоступен. Оформите подписку или настройте Stripe."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({'url': url})


class StripeWebhookView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        endpoint_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        except (ValueError, stripe.error.SignatureVerificationError):
            return HttpResponse(status=400)

        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            user_id = session.get('metadata', {}).get('user_id')
            plan = session.get('metadata', {}).get('plan')
            customer_id = session.get('customer')
            subscription_id = session.get('subscription')

            if user_id and plan:
                try:
                    user = User.objects.get(id=user_id)
                    user.plan = plan
                    user.save()

                    sub, _ = Subscription.objects.get_or_create(user=user)
                    sub.stripe_customer_id = customer_id
                    sub.stripe_subscription_id = subscription_id
                    sub.status = 'active'
                    sub.stripe_price_id = getattr(settings, f'STRIPE_{plan.upper()}_PRICE_ID', '')
                    sub.save()

                    if subscription_id:
                        sync_subscription_from_stripe(subscription_id)
                except User.DoesNotExist:
                    pass

        elif event['type'] in ['customer.subscription.updated', 'customer.subscription.deleted']:
            subscription = event['data']['object']
            sync_subscription_from_stripe(subscription.get('id'))

        return HttpResponse(status=200)

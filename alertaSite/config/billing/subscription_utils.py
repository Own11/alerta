import stripe
from django.conf import settings
from django.utils import timezone

stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')


from datetime import datetime, timezone as dt_tz


def user_has_active_subscription(user):
    from billing.plan_limits import get_effective_plan
    if get_effective_plan(user) == 'free':
        return False
    try:
        return user.subscription.status in ('active', 'trialing')
    except Exception:
        return user.plan != 'free'


def sync_subscription_from_stripe(subscription_id):
    """Fetch subscription from Stripe and update local Subscription + User.plan."""
    from billing.models import Subscription
    from accounts.models import User

    if not subscription_id or not stripe.api_key or stripe.api_key == 'sk_test_dummy':
        return None

    sub_data = stripe.Subscription.retrieve(subscription_id)
    try:
        local_sub = Subscription.objects.get(stripe_subscription_id=subscription_id)
    except Subscription.DoesNotExist:
        return None

    local_sub.status = sub_data.get('status', local_sub.status)
    local_sub.cancel_at_period_end = sub_data.get('cancel_at_period_end', False)
    period_end = sub_data.get('current_period_end')
    if period_end:
        local_sub.current_period_end = datetime.fromtimestamp(period_end, tz=dt_tz.utc)

    price_id = sub_data['items']['data'][0]['price']['id'] if sub_data.get('items', {}).get('data') else local_sub.stripe_price_id
    local_sub.stripe_price_id = price_id

    user = local_sub.user
    if local_sub.status in ('active', 'trialing'):
        pro_price = getattr(settings, 'STRIPE_PRO_PRICE_ID', '')
        biz_price = getattr(settings, 'STRIPE_BUSINESS_PRICE_ID', '')
        if price_id == biz_price:
            user.plan = 'business'
        elif price_id == pro_price:
            user.plan = 'pro'
    elif local_sub.status in ('canceled', 'unpaid', 'incomplete_expired'):
        user.plan = 'free'

    local_sub.save()
    user.save()
    return local_sub


def create_customer_portal_session(user, return_url):
    if not stripe.api_key or stripe.api_key == 'sk_test_dummy':
        return None
    try:
        sub = user.subscription
        customer_id = sub.stripe_customer_id
    except Exception:
        return None
    if not customer_id:
        return None
    session = stripe.billing_portal.Session.create(customer=customer_id, return_url=return_url)
    return session.url

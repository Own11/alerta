import os
from django.conf import settings
from datetime import datetime, timezone as dt_tz
from polar_sdk import Polar

def get_polar_client():
    token = getattr(settings, 'POLAR_ACCESS_TOKEN', '')
    if not token or token.endswith('_dummy'):
        return None
    # For testing, we might want to pass environment='sandbox' if configured, but default is fine here
    return Polar(access_token=token)

def user_has_active_subscription(user):
    from billing.plan_limits import get_effective_plan
    if get_effective_plan(user) == 'free':
        return False
    try:
        return user.subscription.status in ('active', 'trialing')
    except Exception:
        return user.plan != 'free'

def sync_subscription_from_polar(subscription_id):
    """Fetch subscription from Polar and update local Subscription + User.plan."""
    from billing.models import Subscription
    from accounts.models import User

    client = get_polar_client()
    if not client or not subscription_id:
        return None

    try:
        sub_data = client.subscriptions.get(id=subscription_id)
    except Exception as e:
        return None

    try:
        local_sub = Subscription.objects.get(polar_subscription_id=subscription_id)
    except Subscription.DoesNotExist:
        return None

    local_sub.status = sub_data.status.value if hasattr(sub_data.status, 'value') else str(sub_data.status)
    local_sub.cancel_at_period_end = sub_data.cancel_at_period_end
    
    if sub_data.current_period_end:
        # Polar returns a datetime object
        local_sub.current_period_end = sub_data.current_period_end
    
    price_id = sub_data.product_id
    local_sub.polar_product_id = price_id

    user = local_sub.user
    if local_sub.status in ('active', 'trialing'):
        pro_price = getattr(settings, 'POLAR_PRO_PRODUCT_ID', '')
        biz_price = getattr(settings, 'POLAR_BUSINESS_PRODUCT_ID', '')
        if price_id == biz_price:
            user.plan = 'business'
        elif price_id == pro_price:
            user.plan = 'pro'
    elif local_sub.status in ('canceled', 'past_due', 'incomplete_expired', 'revoked'):
        user.plan = 'free'

    local_sub.save()
    user.save()
    return local_sub

def create_customer_portal_session(user, return_url):
    client = get_polar_client()
    if not client:
        return None
    try:
        sub = user.subscription
        customer_id = sub.polar_customer_id
    except Exception:
        return None
    if not customer_id:
        return None
        
    try:
        session = client.customer_portal.customer_sessions.create(
            customer_id=customer_id
        )
        return session.customer_portal_url
    except Exception:
        return None

"""Central plan limits and effective plan resolution."""

PLAN_LIMITS = {
    'free': {
        'max_monitors': 5,
        'min_interval': 300,
        'max_interval': 86400,
        'default_interval': 300,
        'reports_enabled': False,
        'ai_daily_limit': 0,
        'ai_rca_enabled': False,
        'latency_radar': False,
        'status_page_whitelabel': False,
        'post_mortem_enabled': False,
        'chaos_mode_enabled': False,
    },
    'pro': {
        'max_monitors': 50,
        'min_interval': 60,
        'max_interval': 86400,
        'default_interval': 60,
        'reports_enabled': True,
        'ai_daily_limit': 50,
        'ai_rca_enabled': True,
        'latency_radar': True,
        'status_page_whitelabel': True,
        'post_mortem_enabled': False,
        'chaos_mode_enabled': False,
    },
    'business': {
        'max_monitors': 200,
        'min_interval': 30,
        'max_interval': 86400,
        'default_interval': 30,
        'reports_enabled': True,
        'ai_daily_limit': 500,
        'ai_rca_enabled': True,
        'latency_radar': True,
        'status_page_whitelabel': True,
        'post_mortem_enabled': True,
        'chaos_mode_enabled': True,
    },
}


def get_effective_plan(user):
    """Return plan key if subscription is active, otherwise free."""
    plan = getattr(user, 'plan', 'free') or 'free'
    if plan == 'free':
        return 'free'
    try:
        sub = user.subscription
    except Exception:
        return plan if plan in PLAN_LIMITS else 'free'
    if sub.status in ('active', 'trialing'):
        return plan if plan in PLAN_LIMITS else 'free'
    return 'free'


def get_plan_limits(user):
    return PLAN_LIMITS[get_effective_plan(user)]


def validate_check_interval(user, interval):
    limits = get_plan_limits(user)
    interval = int(interval)
    if interval < limits['min_interval']:
        return False, f"Минимальный интервал для вашего тарифа: {limits['min_interval']} сек."
    if interval > limits['max_interval']:
        return False, f"Максимальный интервал: {limits['max_interval']} сек."
    return True, None


def can_add_monitor(user, current_count=None):
    from monitors.models import Monitor

    limits = get_plan_limits(user)
    if current_count is None:
        current_count = Monitor.objects.filter(project__user=user).count()
    if current_count >= limits['max_monitors']:
        return False, f"Превышен лимит мониторов ({limits['max_monitors']}) для тарифа {get_effective_plan(user).upper()}."
    return True, None

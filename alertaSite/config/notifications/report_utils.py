from django.utils import timezone
from monitors.models import Monitor


def build_uptime_report(user):
    """Build report text grouped by project."""
    from billing.plan_limits import get_effective_plan, PLAN_LIMITS

    plan = get_effective_plan(user)
    if not PLAN_LIMITS[plan]['reports_enabled']:
        return None

    lines = []
    projects = user.projects.all().prefetch_related('monitors')

    if not projects.exists():
        monitors = Monitor.objects.filter(project__user=user)
        if monitors.exists():
            lines.append('=== Мониторы ===')
            for m in monitors:
                lines.append(_monitor_line(m))
        else:
            return None
    else:
        for project in projects:
            project_monitors = project.monitors.all()
            if not project_monitors.exists():
                continue
            lines.append(f'\n=== Проект: {project.name} ===')
            for m in project_monitors:
                lines.append(_monitor_line(m))

    if not lines:
        return None
    return '\n'.join(lines)


def _monitor_line(monitor):
    ssl_info = ''
    if monitor.ssl_enabled and monitor.ssl_status not in ('unknown', 'disabled'):
        if monitor.ssl_days_left is not None:
            ssl_info = f', SSL: {monitor.ssl_status} ({monitor.ssl_days_left} дн.)'
    paused = ' [ПАУЗА]' if monitor.is_paused else ''
    return (
        f"  - {monitor.name} ({monitor.url}): "
        f"Uptime {monitor.uptime_percentage}%, Status {monitor.last_status.upper()}{ssl_info}{paused}"
    )


def dispatch_report(user, title, message, report_type='report'):
    """Create in-app notification and send via enabled external channels."""
    from notifications.models import Notification
    from monitors.tasks import send_external_notifications

    Notification.objects.create(
        user=user,
        type='report',
        title=title,
        message=message,
        data={'report_type': report_type},
    )
    send_external_notifications(user, title, message, notification_type='report')

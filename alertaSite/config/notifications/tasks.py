from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
from billing.plan_limits import get_effective_plan, PLAN_LIMITS
from notifications.report_utils import build_uptime_report, dispatch_report

User = get_user_model()


def _send_reports(expected_frequency, report_type):
    users = User.objects.filter(plan__in=['pro', 'business'])
    sent_count = 0

    for user in users:
        plan = get_effective_plan(user)
        if not PLAN_LIMITS[plan]['reports_enabled']:
            continue

        freq = getattr(user, 'report_frequency', 'daily')
        if freq == 'off' or freq != expected_frequency:
            continue

        report_content = build_uptime_report(user)
        if not report_content:
            continue

        if expected_frequency == 'daily':
            title = f"Daily Uptime Report - {timezone.localdate().strftime('%Y-%m-%d')}"
        else:
            title = f"Weekly Uptime Report - {timezone.localdate().strftime('%Y-%m-%d')}"

        message = (
            f"Здравствуйте, {user.username}!\n\n"
            f"Отчёт о состоянии ваших сервисов ({expected_frequency}):\n"
            f"{report_content}\n\n"
            f"С уважением,\nКоманда Alerta"
        )
        dispatch_report(user, title, message, report_type=report_type)
        sent_count += 1

    return sent_count


@shared_task
def daily_report():
    count = _send_reports('daily', 'daily')
    return f"Daily reports dispatched to {count} users."


@shared_task
def weekly_report():
    count = _send_reports('weekly', 'weekly')
    return f"Weekly reports dispatched to {count} users."

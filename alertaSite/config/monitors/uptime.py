from django.utils import timezone
from monitors.models import Monitor, MonitorCheck


def update_monitor_uptime(monitor, window=500):
    """Recalculate uptime from recent check history."""
    checks = MonitorCheck.objects.filter(monitor=monitor).order_by('-checked_at')[:window]
    checks = list(checks)
    if not checks:
        return
    up_count = sum(1 for c in checks if c.status == 'up')
    monitor.uptime_percentage = round(up_count / len(checks) * 100, 2)
    monitor.save(update_fields=['uptime_percentage'])


def prune_old_checks(monitor, keep=1000):
    """Keep only the most recent N checks per monitor."""
    ids_to_keep = MonitorCheck.objects.filter(monitor=monitor).order_by('-checked_at')[:keep].values_list('id', flat=True)
    MonitorCheck.objects.filter(monitor=monitor).exclude(id__in=list(ids_to_keep)).delete()

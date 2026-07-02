import socket
import subprocess
import platform
import requests
import ssl
from datetime import datetime, timezone as dt_timezone
from urllib.parse import urlparse
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from celery import shared_task
from .models import Monitor, MonitorCheck
from .uptime import update_monitor_uptime, prune_old_checks
from .task_utils import enqueue_task
from incidents.models import Incident
from notifications.models import Notification

SSL_RECHECK_SECONDS = 6 * 3600  # 6 hours


def _resolve_hostname(monitor):
    parsed = urlparse(monitor.url if '://' in monitor.url else f"http://{monitor.url}")
    return parsed.hostname or monitor.url


def _is_local_ip(ip):
    if ip in ('127.0.0.1', '0.0.0.0', '::1'):
        return True
    return ip.startswith((
        '127.', '10.', '192.168.', '0.',
        '169.254.', '100.64.',
        '172.16.', '172.17.', '172.18.', '172.19.', '172.20.',
        '172.21.', '172.22.', '172.23.', '172.24.', '172.25.',
        '172.26.', '172.27.', '172.28.', '172.29.', '172.30.', '172.31.',
        'fc00:', 'fe80:', '::ffff:127.',
    ))


def _ping_host(hostname, timeout):
    """Run a single ICMP ping when the ping utility is available."""
    system = platform.system().lower()
    if system == 'windows':
        cmd = ['ping', '-n', '1', '-w', str(max(timeout, 1) * 1000), hostname]
    elif system == 'darwin':
        cmd = ['ping', '-c', '1', '-t', str(max(timeout, 1)), hostname]
    else:
        cmd = ['ping', '-c', '1', '-W', str(max(timeout, 1)), hostname]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            timeout=max(timeout, 1) + 5,
            check=False,
        )
        output = (proc.stdout or proc.stderr or b'').decode(errors='ignore').strip()
        return proc.returncode == 0, output[:200] or 'Ping failed'
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        return False, str(exc)


@shared_task
def schedule_checks():
    now = timezone.now()
    monitors = Monitor.objects.filter(is_active=True, is_paused=False)
    triggered_count = 0
    for monitor in monitors:
        if not monitor.last_check_at or (now - monitor.last_check_at).total_seconds() >= monitor.check_interval:
            enqueue_task(check_monitor, str(monitor.id))
            triggered_count += 1
    return f"Triggered check for {triggered_count} monitors."


@shared_task
def schedule_ssl_checks():
    """Run SSL certificate checks on a schedule independent of HTTP checks."""
    now = timezone.now()
    monitors = Monitor.objects.filter(ssl_enabled=True, is_active=True, is_paused=False)
    triggered = 0
    for monitor in monitors:
        if not monitor.ssl_last_checked_at or (now - monitor.ssl_last_checked_at).total_seconds() >= SSL_RECHECK_SECONDS:
            enqueue_task(check_ssl_expiry, str(monitor.id), _resolve_hostname(monitor))
            triggered += 1
    return f"Triggered SSL check for {triggered} monitors."


@shared_task
def check_monitor(monitor_id):
    try:
        monitor = Monitor.objects.get(id=monitor_id)
    except Monitor.DoesNotExist:
        return "Monitor not found."

    status_ok = False
    reason = ""
    response_time_ms = None
    parsed_url = urlparse(monitor.url if '://' in monitor.url else f"http://{monitor.url}")
    hostname = parsed_url.hostname or monitor.url

    try:
        resolved_ip = socket.gethostbyname(hostname)
        if _is_local_ip(resolved_ip):
            status_ok = False
            reason = "SSRF Protection: Local IP addresses are not allowed."
        elif monitor.monitor_type == 'http':
            target_url = monitor.url if '://' in monitor.url else f"https://{monitor.url}"
            session = requests.Session()
            adapter = requests.adapters.HTTPAdapter(max_retries=monitor.retries)
            session.mount('http://', adapter)
            session.mount('https://', adapter)
            start = datetime.now()
            resp = session.get(target_url, timeout=monitor.timeout, allow_redirects=True)
            response_time_ms = int((datetime.now() - start).total_seconds() * 1000)
            if 200 <= resp.status_code < 400:
                status_ok = True
            else:
                reason = f"HTTP Status {resp.status_code}"

            if monitor.ssl_enabled:
                ssl_host = urlparse(resp.url).hostname or hostname
                enqueue_task(check_ssl_expiry, str(monitor.id), ssl_host)

        elif monitor.monitor_type == 'port':
            port = parsed_url.port or 80
            host = hostname.split(':')[0] if ':' in hostname else hostname
            if ':' in monitor.url and not parsed_url.port:
                parts = monitor.url.split(':')
                if len(parts) >= 2:
                    try:
                        port = int(parts[-1])
                        host = parts[0]
                    except ValueError:
                        pass
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(monitor.timeout)
            start = datetime.now()
            result = sock.connect_ex((host, port))
            response_time_ms = int((datetime.now() - start).total_seconds() * 1000)
            status_ok = result == 0
            if not status_ok:
                reason = f"Port check failed with error code {result}"
            sock.close()

        elif monitor.monitor_type == 'icmp':
            start = datetime.now()
            ping_ok, ping_reason = _ping_host(hostname, monitor.timeout)
            if ping_ok:
                status_ok = True
            else:
                # Fallback: DNS resolution proves the host exists even if ping is blocked.
                try:
                    socket.gethostbyname(hostname)
                    status_ok = True
                    ping_reason = ''
                except Exception as dns_error:
                    status_ok = False
                    reason = ping_reason or str(dns_error)
            response_time_ms = int((datetime.now() - start).total_seconds() * 1000)
    except Exception as e:
        status_ok = False
        reason = str(e)

    new_status = 'up' if status_ok else 'down'
    old_status = monitor.last_status

    MonitorCheck.objects.create(
        monitor=monitor,
        status=new_status,
        response_time_ms=response_time_ms,
        reason=reason or '',
    )
    prune_old_checks(monitor)
    update_monitor_uptime(monitor)

    monitor.last_check_at = timezone.now()
    monitor.last_status = new_status
    monitor.response_time_ms = response_time_ms
    monitor.save()

    if old_status != 'unknown' and old_status != new_status:
        handle_status_change(monitor, new_status, reason)

    return f"Monitor {monitor.name} is {new_status}. Reason: {reason or 'N/A'}"


def handle_status_change(monitor, new_status, reason):
    user = monitor.project.user

    if new_status == 'down':
        incident = Incident.objects.create(monitor=monitor, reason=reason)
        title = f"Alert: Monitor {monitor.name} is DOWN!"
        message = f"Monitor {monitor.name} ({monitor.url}) has failed. Reason: {reason}."
        Notification.objects.create(
            user=user,
            type='alert',
            title=title,
            message=message,
            data={'incident_id': str(incident.id), 'monitor_id': str(monitor.id)},
        )
        send_external_notifications(user, title, message, notification_type='alert')

    elif new_status == 'up':
        open_incidents = Incident.objects.filter(monitor=monitor, resolved_at__isnull=True)
        for incident in open_incidents:
            incident.resolved_at = timezone.now()
            incident.duration = int((incident.resolved_at - incident.started_at).total_seconds())
            incident.save()

        title = f"Resolved: Monitor {monitor.name} is UP!"
        message = f"Monitor {monitor.name} ({monitor.url}) has recovered and is now online."
        Notification.objects.create(
            user=user,
            type='alert',
            title=title,
            message=message,
            data={'monitor_id': str(monitor.id)},
        )
        send_external_notifications(user, title, message, notification_type='alert')


@shared_task
def check_ssl_expiry(monitor_id, hostname=None):
    try:
        monitor = Monitor.objects.get(id=monitor_id)
    except Monitor.DoesNotExist:
        return

    if not monitor.ssl_enabled:
        monitor.ssl_status = 'disabled'
        monitor.save(update_fields=['ssl_status'])
        return

    hostname = hostname or _resolve_hostname(monitor)
    context = ssl.create_default_context()
    monitor.ssl_last_checked_at = timezone.now()

    try:
        import OpenSSL.crypto
        with socket.create_connection((hostname, 443), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert_bin = ssock.getpeercert(True)
                x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_ASN1, cert_bin)
                not_after_str = x509.get_notAfter().decode('ascii')
                expiry_date = datetime.strptime(not_after_str, '%Y%m%d%H%M%SZ').replace(tzinfo=dt_timezone.utc)
                days_left = (expiry_date - timezone.now()).days

                monitor.ssl_expires_at = expiry_date
                monitor.ssl_days_left = days_left
                if days_left <= 0:
                    monitor.ssl_status = 'expired'
                elif days_left <= monitor.ssl_expiry_threshold:
                    monitor.ssl_status = 'warning'
                else:
                    monitor.ssl_status = 'ok'

                monitor.save(update_fields=[
                    'ssl_expires_at', 'ssl_days_left', 'ssl_last_checked_at', 'ssl_status',
                ])

                if days_left <= monitor.ssl_expiry_threshold:
                    title = f"SSL Expiry Warning: {monitor.name}"
                    message = (
                        f"SSL certificate for {monitor.url} will expire in {days_left} days "
                        f"(on {expiry_date.strftime('%Y-%m-%d')})."
                    )
                    recent = Notification.objects.filter(
                        user=monitor.project.user,
                        type='ssl',
                        title=title,
                        created_at__gte=timezone.now() - timezone.timedelta(days=1),
                    ).exists()
                    if not recent:
                        Notification.objects.create(
                            user=monitor.project.user,
                            type='ssl',
                            title=title,
                            message=message,
                            data={'monitor_id': str(monitor.id), 'days_left': days_left},
                        )
                        send_external_notifications(
                            monitor.project.user, title, message, notification_type='ssl',
                        )
    except Exception as e:
        monitor.ssl_status = 'error'
        monitor.ssl_days_left = None
        monitor.save(update_fields=['ssl_last_checked_at', 'ssl_status', 'ssl_days_left'])


def send_external_notifications(user, title, message, notification_type='alert'):
    """Send to configured channels respecting user preferences."""
    channels = {
        'telegram': getattr(user, 'notify_telegram', True) and user.telegram_chat_id,
        'slack': getattr(user, 'notify_slack', True) and user.slack_webhook_url,
        'email': getattr(user, 'notify_email', True) and user.email,
        'push': getattr(user, 'notify_push', True) and user.fcm_device_token,
    }

    if channels['telegram']:
        tg_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        if tg_token and tg_token != '123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ':
            try:
                requests.post(
                    f"https://api.telegram.org/bot{tg_token}/sendMessage",
                    json={
                        'chat_id': user.telegram_chat_id,
                        'text': f"🔔 *{title}*\n{message}",
                        'parse_mode': 'Markdown',
                    },
                    timeout=10,
                )
            except Exception:
                pass

    if channels['slack']:
        try:
            requests.post(
                user.slack_webhook_url,
                json={'text': f"*{title}*\n{message}"},
                timeout=10,
            )
        except Exception:
            pass

    if channels['email']:
        try:
            send_mail(
                subject=title,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception:
            pass

    if channels['push']:
        enqueue_task(send_push_notification, str(user.id), title, message)


@shared_task
def send_push_notification(user_id, title, message):
    """FCM push — uses Firebase when FIREBASE_CREDENTIALS_PATH is set."""
    cred_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', '')
    if not cred_path:
        return f"FCM skipped (no credentials): User {user_id}: {title}"

    try:
        import firebase_admin
        from firebase_admin import credentials, messaging
        from accounts.models import User

        if not firebase_admin._apps:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)

        user = User.objects.get(id=user_id)
        if not user.fcm_device_token:
            return "No FCM token"

        messaging.send(messaging.Message(
            notification=messaging.Notification(title=title, body=message),
            token=user.fcm_device_token,
        ))
        return f"FCM sent to User {user_id}"
    except Exception as e:
        return f"FCM error: {e}"

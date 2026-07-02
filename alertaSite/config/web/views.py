import json
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q
from django.http import JsonResponse, FileResponse, Http404
from accounts.models import User
from projects.models import Project
from billing.plan_limits import get_plan_limits, can_add_monitor, get_effective_plan
from billing.subscription_utils import create_customer_portal_session, sync_subscription_from_stripe
from monitors.models import Monitor, MonitorCheck
from incidents.models import Incident
from notifications.models import Notification
from ai_assistant.models import AIChatSession
from billing.models import Subscription
from django.conf import settings
from .forms import LoginForm, RegisterForm, ProjectForm, MonitorForm

# ----------------- AUTHENTICATION -----------------

def login_view(request):
    if request.user.is_authenticated:
        return redirect('web:dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Добро пожаловать назад, {username}!")
                return redirect('web:dashboard')
            else:
                messages.error(request, "Неверное имя пользователя или пароль.")
    else:
        form = LoginForm()
    return render(request, 'web/auth/login.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('web:dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Регистрация завершена успешно!")
            return redirect('web:dashboard')
    else:
        form = RegisterForm()
    return render(request, 'web/auth/register.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "Вы вышли из системы.")
    return redirect('web:landing')


# ----------------- LANDING & DOWNLOADS -----------------

def landing_view(request):
    apk_download_url = request.build_absolute_uri(reverse('web:download_apk'))
    apk_available = settings.ANDROID_APK_PATH.exists()
    return render(request, 'web/landing.html', {
        'apk_download_url': apk_download_url,
        'apk_available': apk_available,
    })


def download_apk_view(request):
    apk_path = settings.ANDROID_APK_PATH
    if not apk_path.exists():
        raise Http404('APK файл пока недоступен для скачивания.')

    return FileResponse(
        apk_path.open('rb'),
        as_attachment=True,
        filename=settings.ANDROID_APK_FILENAME,
        content_type='application/vnd.android.package-archive',
    )


# ----------------- DASHBOARD & PROFILE -----------------

@login_required
def dashboard_view(request):
    user = request.user
    projects = Project.objects.filter(user=user).prefetch_related('monitors')
    monitors = Monitor.objects.filter(project__user=user).select_related('project')
    
    monitors_count = monitors.count()
    monitors_up = monitors.filter(last_status='up').count()
    monitors_down = monitors.filter(last_status='down').count()
    monitors_paused = monitors.filter(is_paused=True).count()
    
    active_incidents = Incident.objects.filter(monitor__project__user=user, resolved_at__isnull=True)
    latest_notifications = Notification.objects.filter(user=user)[:5]

    project_groups = []
    for project in projects:
        project_monitors = list(project.monitors.all())
        if project_monitors:
            project_groups.append({
                'project': project,
                'monitors': project_monitors,
                'monitor_count': len(project_monitors),
                'up': sum(1 for m in project_monitors if m.last_status == 'up' and not m.is_paused),
                'down': sum(1 for m in project_monitors if m.last_status == 'down' and not m.is_paused),
            })
    
    context = {
        'projects': projects,
        'project_groups': project_groups,
        'monitors': monitors,
        'monitors_count': monitors_count,
        'monitors_up': monitors_up,
        'monitors_down': monitors_down,
        'monitors_paused': monitors_paused,
        'active_incidents_count': active_incidents.count(),
        'latest_notifications': latest_notifications,
        'active_incidents': active_incidents[:5],
    }
    return render(request, 'web/dashboard.html', context)


@login_required
def settings_view(request):
    user = request.user
    subscription = None
    try:
        subscription = user.subscription
    except Subscription.DoesNotExist:
        pass

    if request.method == 'POST':
        user.telegram_chat_id = request.POST.get('telegram_chat_id', '')
        user.slack_webhook_url = request.POST.get('slack_webhook_url', '')
        fcm_token = request.POST.get('fcm_device_token', '')
        if fcm_token:
            user.fcm_device_token = fcm_token
        user.report_frequency = request.POST.get('report_frequency', 'daily')
        user.notify_telegram = request.POST.get('notify_telegram') == 'on'
        user.notify_slack = request.POST.get('notify_slack') == 'on'
        user.notify_email = request.POST.get('notify_email') == 'on'
        user.notify_push = request.POST.get('notify_push') == 'on'
        user.save()
        messages.success(request, "Настройки уведомлений сохранены.")
        return redirect('web:settings')

    plan_limits = get_plan_limits(user)
    return render(request, 'web/settings.html', {
        'user': user,
        'subscription': subscription,
        'plan_limits': plan_limits,
        'effective_plan': get_effective_plan(user),
    })


@login_required
def billing_portal(request):
    url = create_customer_portal_session(request.user, request.build_absolute_uri('/settings/'))
    if url:
        return redirect(url)
    messages.error(request, "Управление подпиской недоступно. Сначала оформите платный тариф.")
    return redirect('web:pricing')


# ----------------- PROJECTS CRUD -----------------

@login_required
def projects_list(request):
    projects = Project.objects.filter(user=request.user).annotate(
        monitor_count=Count('monitors')
    )
    return render(request, 'web/projects/list.html', {
        'projects': projects,
        'projects_count': projects.count(),
    })


@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk, user=request.user)
    monitors = project.monitors.all()
    active_incidents = Incident.objects.filter(
        monitor__project=project, resolved_at__isnull=True,
    )
    return render(request, 'web/projects/detail.html', {
        'project': project,
        'monitors': monitors,
        'monitors_count': monitors.count(),
        'active_incidents_count': active_incidents.count(),
    })


@login_required
def project_create(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.user = request.user
            project.save()
            messages.success(request, f"Проект '{project.name}' создан.")
            return redirect('web:projects_list')
    else:
        form = ProjectForm()
    return render(request, 'web/projects/form.html', {'form': form, 'title': 'Создать проект'})


@login_required
def project_edit(request, pk):
    project = get_object_or_404(Project, pk=pk, user=request.user)
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, f"Проект '{project.name}' обновлен.")
            return redirect('web:projects_list')
    else:
        form = ProjectForm(instance=project)
    return render(request, 'web/projects/form.html', {'form': form, 'title': 'Редактировать проект'})


@login_required
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk, user=request.user)
    if request.method == 'POST':
        project.delete()
        messages.success(request, "Проект удален.")
        return redirect('web:projects_list')
    return render(request, 'web/projects/confirm_delete.html', {'project': project})


# ----------------- MONITORS CRUD & ACTIONS -----------------

@login_required
def monitor_create(request):
    user = request.user
    ok, err = can_add_monitor(user)
    if not ok:
        messages.error(request, err)
        return redirect('web:pricing' if 'лимит' in err.lower() else 'web:dashboard')

    limits = get_plan_limits(user)
    initial = {'check_interval': limits['default_interval']}
    project_id = request.GET.get('project')
    if project_id:
        try:
            initial['project'] = Project.objects.get(pk=project_id, user=user)
        except Project.DoesNotExist:
            pass

    if request.method == 'POST':
        form = MonitorForm(request.POST, user=user)
        if form.is_valid():
            monitor = form.save()
            from monitors.tasks import check_monitor
            from monitors.task_utils import enqueue_task
            enqueue_task(check_monitor, str(monitor.id))
            messages.success(request, f"Монитор '{monitor.name}' успешно добавлен.")
            return redirect('web:project_detail', pk=monitor.project_id)
    else:
        form = MonitorForm(user=user, initial=initial)
    return render(request, 'web/monitors/form.html', {
        'form': form,
        'title': 'Добавить монитор',
        'plan_limits': limits,
    })


@login_required
def monitor_detail(request, pk):
    monitor = get_object_or_404(Monitor, pk=pk, project__user=request.user)
    
    # Фильтр инцидентов по дням
    days_filter = request.GET.get('days', '7')
    try:
        days = int(days_filter)
    except ValueError:
        days = 7
        
    start_date = timezone.now() - timezone.timedelta(days=days)
    incidents = Incident.objects.filter(monitor=monitor, started_at__gte=start_date)
    recent_checks = list(MonitorCheck.objects.filter(monitor=monitor).order_by('-checked_at')[:20])
    recent_checks.reverse()
    chart_labels = [c.checked_at.strftime('%H:%M') for c in recent_checks]
    chart_data = [100 if c.status == 'up' else 0 for c in recent_checks]

    return render(request, 'web/monitors/detail.html', {
        'monitor': monitor,
        'incidents': incidents,
        'incidents_count': incidents.count(),
        'days': days,
        'recent_checks': recent_checks,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
    })


@login_required
def monitor_edit(request, pk):
    monitor = get_object_or_404(Monitor, pk=pk, project__user=request.user)
    if request.method == 'POST':
        form = MonitorForm(request.POST, instance=monitor, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f"Монитор '{monitor.name}' обновлен.")
            return redirect('web:monitor_detail', pk=monitor.pk)
    else:
        form = MonitorForm(instance=monitor, user=request.user)
    return render(request, 'web/monitors/form.html', {
        'form': form,
        'title': 'Редактировать монитор',
        'plan_limits': get_plan_limits(request.user),
    })


@login_required
def monitor_delete(request, pk):
    monitor = get_object_or_404(Monitor, pk=pk, project__user=request.user)
    if request.method == 'POST':
        monitor.delete()
        messages.success(request, "Монитор удален.")
        return redirect('web:dashboard')
    return render(request, 'web/monitors/confirm_delete.html', {'monitor': monitor})


@login_required
def monitor_run_check(request, pk):
    monitor = get_object_or_404(Monitor, pk=pk, project__user=request.user)
    from monitors.tasks import check_monitor
    from monitors.task_utils import enqueue_task
    enqueue_task(check_monitor, str(monitor.id))
    messages.success(request, f"Проверка монитора '{monitor.name}' выполнена.")
    return redirect('web:monitor_detail', pk=monitor.pk)


@login_required
def monitor_toggle(request, pk):
    monitor = get_object_or_404(Monitor, pk=pk, project__user=request.user)
    monitor.is_paused = not monitor.is_paused
    monitor.save()
    status_str = "приостановлен" if monitor.is_paused else "запущен"
    messages.success(request, f"Монитор '{monitor.name}' {status_str}.")
    return redirect(request.META.get('HTTP_REFERER') or reverse('web:dashboard'))


# ----------------- INCIDENTS -----------------

@login_required
def incidents_list(request):
    incidents = Incident.objects.filter(monitor__project__user=request.user)
    active_count = incidents.filter(resolved_at__isnull=True).count()
    return render(request, 'web/incidents/list.html', {
        'incidents': incidents,
        'incidents_count': incidents.count(),
        'active_count': active_count,
    })


@login_required
def incident_acknowledge(request, pk):
    incident = get_object_or_404(Incident, pk=pk, monitor__project__user=request.user)
    incident.is_acknowledged = True
    incident.save()
    messages.success(request, "Инцидент подтвержден (Acknowledged).")
    return redirect(request.META.get('HTTP_REFERER') or reverse('web:incidents_list'))


@login_required
def incident_resolve(request, pk):
    incident = get_object_or_404(Incident, pk=pk, monitor__project__user=request.user)
    if not incident.resolved_at:
        incident.resolved_at = timezone.now()
        incident.duration = int((incident.resolved_at - incident.started_at).total_seconds())
        incident.save()
        
        monitor = incident.monitor
        monitor.last_status = 'up'
        monitor.save()
        messages.success(request, "Инцидент закрыт.")
    return redirect(request.META.get('HTTP_REFERER') or reverse('web:incidents_list'))


# ----------------- NOTIFICATIONS -----------------

@login_required
def notifications_list(request):
    notifications = Notification.objects.filter(user=request.user)
    unread_count = notifications.filter(is_read=False).count()
    return render(request, 'web/notifications/list.html', {
        'notifications': notifications,
        'notifications_count': notifications.count(),
        'unread_count': unread_count,
    })


@login_required
def notification_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save()
    return redirect('web:notifications_list')


@login_required
def notifications_read_all(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, "Все уведомления помечены как прочитанные.")
    return redirect('web:notifications_list')


# ----------------- AI ASSISTANT -----------------

@login_required
def ai_chat_view(request):
    sessions = AIChatSession.objects.filter(user=request.user)
    active_session_id = request.GET.get('session_id')
    active_session = None
    if active_session_id:
        active_session = get_object_or_404(AIChatSession, id=active_session_id, user=request.user)
    elif sessions.exists():
        active_session = sessions.first()

    monitors = Monitor.objects.filter(project__user=request.user)
    
    return render(request, 'web/ai_assistant/chat.html', {
        'sessions': sessions,
        'sessions_count': sessions.count(),
        'active_session': active_session,
        'monitors': monitors,
        'ai_used_today': request.user.ai_used_today,
        'ai_daily_limit': request.user.ai_daily_limit,
    })


@login_required
def ai_chat_create_session(request):
    if request.method == 'POST':
        title = request.POST.get('title', 'Новый чат с AI')
        monitor_id = request.POST.get('monitor_id')
        
        monitor = None
        if monitor_id:
            monitor = get_object_or_404(Monitor, id=monitor_id, project__user=request.user)

        session = AIChatSession.objects.create(
            user=request.user,
            monitor=monitor,
            title=title,
            messages=[]
        )
        return redirect(f"/ai-chat/?session_id={session.id}")
    return redirect('web:ai_chat')


# ----------------- BILLING & SUBSCRIPTIONS -----------------

@login_required
def pricing_view(request):
    return render(request, 'web/billing/pricing.html', {
        'stripe_public_key': getattr(settings, 'STRIPE_PUBLIC_KEY', '')
    })


@login_required
def billing_success(request):
    session_id = request.GET.get('session_id')
    if session_id:
        try:
            import stripe
            stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')
            session = stripe.checkout.Session.retrieve(session_id)
            plan = session.metadata.get('plan')
            user_id = session.metadata.get('user_id')
            subscription_id = session.get('subscription')
            if user_id and plan and str(request.user.id) == str(user_id):
                request.user.plan = plan
                request.user.save()
                sub, _ = Subscription.objects.get_or_create(user=request.user)
                sub.stripe_customer_id = session.get('customer')
                sub.stripe_subscription_id = subscription_id
                sub.status = 'active'
                sub.save()
                if subscription_id:
                    sync_subscription_from_stripe(subscription_id)
                messages.success(request, f"Поздравляем! Ваш тариф успешно обновлен до {plan.upper()}!")
        except Exception:
            pass
    return render(request, 'web/billing/success.html')


@login_required
def billing_cancel(request):
    messages.warning(request, "Оплата тарифа была отменена.")
    return render(request, 'web/billing/cancel.html')


# ----------------- PUBLIC STATUS PAGE -----------------

def public_status_api(request, slug):
    project = get_object_or_404(Project, slug=slug, status_page_enabled=True)
    monitors = project.monitors.filter(is_active=True)
    start_date = timezone.now() - timezone.timedelta(days=7)
    incidents = Incident.objects.filter(monitor__project=project, started_at__gte=start_date)

    monitor_data = []
    for m in monitors:
        monitor_data.append({
            'name': m.name,
            'url': m.url,
            'status': 'paused' if m.is_paused else m.last_status,
            'uptime_percentage': float(m.uptime_percentage),
            'response_time_ms': m.response_time_ms,
            'ssl_enabled': m.ssl_enabled,
            'ssl_status': m.ssl_status,
            'ssl_days_left': m.ssl_days_left,
            'ssl_expires_at': m.ssl_expires_at.isoformat() if m.ssl_expires_at else None,
        })

    has_down = any(
        m['status'] == 'down' for m in monitor_data
    )

    return JsonResponse({
        'project': project.name,
        'title': project.status_page_title or project.name,
        'overall_status': 'down' if has_down else 'up',
        'monitors': monitor_data,
        'incidents_count': incidents.count(),
        'updated_at': timezone.now().isoformat(),
    })


def public_status_page(request, slug):
    project = get_object_or_404(Project, slug=slug, status_page_enabled=True)
    monitors = project.monitors.all()
    has_down_monitors = monitors.filter(last_status='down', is_paused=False).exists()

    # История инцидентов проекта за последние 7 дней
    start_date = timezone.now() - timezone.timedelta(days=7)
    incidents = Incident.objects.filter(monitor__project=project, started_at__gte=start_date)

    return render(request, 'web/projects/status_page.html', {
        'project': project,
        'monitors': monitors,
        'monitors_count': monitors.count(),
        'incidents': incidents,
        'has_down_monitors': has_down_monitors,
    })

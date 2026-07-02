from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from billing.plan_limits import can_add_monitor, get_plan_limits
from .models import Monitor
from .serializers import MonitorSerializer


class MonitorViewSet(viewsets.ModelViewSet):
    serializer_class = MonitorSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Monitor.objects.filter(project__user=self.request.user)
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['request'] = self.request
        return ctx

    def perform_create(self, serializer):
        user = self.request.user
        project = serializer.validated_data['project']
        if project.user != user:
            raise PermissionDenied("Этот проект не принадлежит вам.")

        ok, err = can_add_monitor(user)
        if not ok:
            raise ValidationError({"error": err})

        limits = get_plan_limits(user)
        extra = {}
        if 'check_interval' not in serializer.validated_data:
            extra['check_interval'] = limits['default_interval']
        serializer.save(**extra)
        from monitors.tasks import check_monitor
        from monitors.task_utils import enqueue_task
        enqueue_task(check_monitor, str(serializer.instance.id))

    def perform_update(self, serializer):
        user = self.request.user
        project = serializer.validated_data.get('project', serializer.instance.project)
        if project.user != user:
            raise PermissionDenied("Этот проект не принадлежит вам.")
        serializer.save()

    @action(detail=True, methods=['post'])
    def toggle(self, request, pk=None):
        monitor = self.get_object()
        monitor.is_paused = not monitor.is_paused
        monitor.save()
        status_str = "приостановлен" if monitor.is_paused else "запущен"
        return Response({
            'status': f'Монитор успешно {status_str}.',
            'is_paused': monitor.is_paused,
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def run_check(self, request, pk=None):
        from monitors.tasks import check_monitor
        from monitors.task_utils import enqueue_task
        monitor = self.get_object()
        enqueue_task(check_monitor, str(monitor.id))
        return Response({'status': 'Проверка запущена.'})

    @action(detail=True, methods=['post'])
    def check_ssl(self, request, pk=None):
        from monitors.tasks import check_ssl_expiry, _resolve_hostname
        from monitors.task_utils import enqueue_task
        monitor = self.get_object()
        if not monitor.ssl_enabled:
            return Response({'error': 'SSL проверка отключена для этого монитора.'}, status=400)
        enqueue_task(check_ssl_expiry, str(monitor.id), _resolve_hostname(monitor))
        return Response({'status': 'SSL проверка запущена.'})

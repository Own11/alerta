from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Incident
from .serializers import IncidentSerializer

class IncidentViewSet(viewsets.ModelViewSet):
    """
    API эндпоинт для просмотра инцидентов.
    """
    serializer_class = IncidentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Incident.objects.filter(monitor__project__user=self.request.user)

    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """
        Отмечает инцидент как подтвержденный.
        """
        incident = self.get_object()
        incident.is_acknowledged = True
        incident.save()
        return Response({'status': 'Инцидент успешно подтвержден (acknowledged).'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """
        Закрывает инцидент вручную.
        """
        incident = self.get_object()
        if not incident.resolved_at:
            incident.resolved_at = timezone.now()
            incident.duration = int((incident.resolved_at - incident.started_at).total_seconds())
            incident.save()
            # Обновим статус самого монитора на UP
            monitor = incident.monitor
            monitor.last_status = 'up'
            monitor.save()
        return Response({'status': 'Инцидент успешно разрешен (resolved).'}, status=status.HTTP_200_OK)

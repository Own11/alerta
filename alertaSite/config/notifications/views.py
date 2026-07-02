from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Notification
from .serializers import NotificationSerializer

class NotificationViewSet(viewsets.ModelViewSet):
    """
    API эндпоинт для истории уведомлений пользователя.
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """
        Отмечает конкретное уведомление как прочитанное.
        """
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'Уведомление отмечено как прочитанное.'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """
        Отмечает все уведомления пользователя как прочитанные.
        """
        Notification.objects.filter(user=self.request.user, is_read=False).update(is_read=True)
        return Response({'status': 'Все уведомления отмечены как прочитанные.'}, status=status.HTTP_200_OK)

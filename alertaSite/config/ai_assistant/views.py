import openai
from django.conf import settings
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import AIChatSession
from .serializers import AIChatSessionSerializer
from monitors.models import Monitor

class AIChatSessionViewSet(viewsets.ModelViewSet):
    """
    API эндпоинт для работы с сессиями ИИ-чата и отправки сообщений.
    """
    serializer_class = AIChatSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return AIChatSession.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """
        Отправка сообщения в чат-сессию и получение ответа от OpenAI.
        Лимиты: дневной лимит зависит от тарифа, а также общая защита от флуда.
        """
        session = self.get_object()
        user = request.user
        
        # Сброс дневного счетчика, если настал новый день
        today = timezone.localdate()
        if user.last_ai_reset != today:
            user.ai_used_today = 0
            user.last_ai_reset = today
            user.save()

        # Проверка лимитов
        if user.ai_used_today >= user.ai_daily_limit:
            return Response(
                {"error": f"Превышен дневной лимит запросов к ИИ для тарифа {user.plan.upper()} (макс. {user.ai_daily_limit})."},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        message_content = request.data.get('message')
        if not message_content:
            return Response({"error": "Поле message обязательно."}, status=status.HTTP_400_BAD_REQUEST)

        # Собираем контекст системы о мониторе (если сессия привязана к монитору)
        system_prompt = "Вы — профессиональный ИИ-ассистент мониторинга сайтов Alerta. Помогаете пользователям анализировать ошибки, давать советы по оптимизации и инфраструктурным проблемам."
        if session.monitor:
            monitor = session.monitor
            system_prompt += f" Вы консультируете по монитору: {monitor.name} (URL: {monitor.url}, Тип: {monitor.monitor_type}, Текущий статус: {monitor.last_status}, Uptime: {monitor.uptime_percentage}%)."

        # Подготовка сообщений для OpenAI API
        api_messages = [{"role": "system", "content": system_prompt}]
        for msg in session.messages:
            api_messages.append({"role": msg.get("role"), "content": msg.get("content")})
        
        # Добавляем новое сообщение пользователя в историю
        user_msg = {
            "role": "user",
            "content": message_content,
            "timestamp": timezone.now().isoformat()
        }
        api_messages.append({"role": "user", "content": message_content})

        try:
            # Инициализируем клиент OpenAI
            client = openai.OpenAI(api_key=getattr(settings, 'OPENAI_API_KEY', ''))
            chat_completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=api_messages,
                max_tokens=500
            )
            assistant_response = chat_completion.choices[0].message.content
        except Exception as e:
            assistant_response = f"Ошибка при подключении к ИИ-сервису: {str(e)}"

        # Добавляем ответ ассистента в историю
        assistant_msg = {
            "role": "assistant",
            "content": assistant_response,
            "timestamp": timezone.now().isoformat()
        }
        
        session.messages.append(user_msg)
        session.messages.append(assistant_msg)
        session.save()

        # Инкрементируем использование ИИ
        user.ai_used_today += 1
        user.save()

        return Response({
            "session_id": session.id,
            "messages": session.messages,
            "ai_used_today": user.ai_used_today,
            "ai_daily_limit": user.ai_daily_limit
        }, status=status.HTTP_200_OK)

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import SupabaseProfile

User = get_user_model()

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'plan',
            'telegram_chat_id', 'slack_webhook_url', 'fcm_device_token',
            'report_frequency', 'notify_telegram', 'notify_slack', 'notify_email', 'notify_push',
            'ai_daily_limit', 'ai_used_today', 'last_ai_reset',
        ]
        read_only_fields = ['id', 'plan', 'ai_daily_limit', 'ai_used_today', 'last_ai_reset']

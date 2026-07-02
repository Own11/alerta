from rest_framework import serializers
from .models import AIChatSession

class AIChatSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIChatSession
        fields = ['id', 'user', 'monitor', 'title', 'messages', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']

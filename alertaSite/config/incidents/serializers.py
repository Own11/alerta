from rest_framework import serializers
from .models import Incident

class IncidentSerializer(serializers.ModelSerializer):
    monitor_name = serializers.CharField(source='monitor.name', read_only=True)

    class Meta:
        model = Incident
        fields = [
            'id', 'monitor', 'monitor_name', 'started_at', 
            'resolved_at', 'duration', 'reason', 'is_acknowledged'
        ]
        read_only_fields = ['id', 'started_at', 'duration']

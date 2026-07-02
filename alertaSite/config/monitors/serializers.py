from rest_framework import serializers
from billing.plan_limits import get_plan_limits, validate_check_interval
from .models import Monitor


class MonitorSerializer(serializers.ModelSerializer):
    ssl_expires_at = serializers.DateTimeField(read_only=True)
    ssl_days_left = serializers.IntegerField(read_only=True)
    ssl_status = serializers.CharField(read_only=True)
    response_time_ms = serializers.IntegerField(read_only=True)

    class Meta:
        model = Monitor
        fields = [
            'id', 'project', 'name', 'url', 'monitor_type',
            'check_interval', 'timeout', 'retries',
            'ssl_enabled', 'ssl_expiry_threshold',
            'is_active', 'is_paused', 'last_status',
            'last_check_at', 'uptime_percentage',
            'response_time_ms', 'ssl_expires_at', 'ssl_days_left', 'ssl_status',
        ]
        read_only_fields = [
            'id', 'last_status', 'last_check_at', 'uptime_percentage',
            'response_time_ms', 'ssl_expires_at', 'ssl_days_left', 'ssl_status',
        ]

    def validate_check_interval(self, value):
        user = self.context['request'].user
        ok, err = validate_check_interval(user, value)
        if not ok:
            raise serializers.ValidationError(err)
        return value

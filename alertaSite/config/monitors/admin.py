from django.contrib import admin
from .models import Monitor, MonitorCheck


class MonitorCheckInline(admin.TabularInline):
    model = MonitorCheck
    extra = 0
    readonly_fields = ['status', 'response_time_ms', 'reason', 'checked_at']
    can_delete = False


@admin.register(Monitor)
class MonitorAdmin(admin.ModelAdmin):
    list_display = ['name', 'url', 'project', 'monitor_type', 'check_interval', 'last_status', 'ssl_status', 'uptime_percentage']
    list_filter = ['monitor_type', 'last_status', 'ssl_status', 'is_active', 'is_paused']
    search_fields = ['name', 'url', 'project__name']
    inlines = [MonitorCheckInline]


@admin.register(MonitorCheck)
class MonitorCheckAdmin(admin.ModelAdmin):
    list_display = ['monitor', 'status', 'response_time_ms', 'checked_at']
    list_filter = ['status']
    readonly_fields = ['monitor', 'status', 'response_time_ms', 'reason', 'checked_at']

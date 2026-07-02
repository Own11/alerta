from django.contrib import admin
from .models import Incident


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ['monitor', 'started_at', 'resolved_at', 'duration', 'is_acknowledged']
    list_filter = ['is_acknowledged']
    search_fields = ['monitor__name', 'reason']
    readonly_fields = ['started_at']

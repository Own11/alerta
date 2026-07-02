from django.contrib import admin
from .models import AIChatSession


@admin.register(AIChatSession)
class AIChatSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'monitor', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'title']

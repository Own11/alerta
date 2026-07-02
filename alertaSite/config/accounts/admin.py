from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, SupabaseProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Администрирование пользователей с расширенными полями."""
    list_display = ['username', 'email', 'plan', 'ai_used_today', 'ai_daily_limit', 'is_staff']
    list_filter = ['plan', 'is_staff', 'is_active']
    search_fields = ['username', 'email']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Тариф и AI', {
            'fields': ('plan', 'ai_daily_limit', 'ai_used_today', 'last_ai_reset')
        }),
        ('Интеграции уведомлений', {
            'fields': ('telegram_chat_id', 'slack_webhook_url', 'fcm_device_token')
        }),
        ('Supabase', {
            'fields': ('profile_id',)
        }),
    )


@admin.register(SupabaseProfile)
class SupabaseProfileAdmin(admin.ModelAdmin):
    list_display = ['username', 'user', 'auth_users_id']
    search_fields = ['username']

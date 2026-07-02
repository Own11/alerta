from django.contrib import admin
from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'slug', 'status_page_enabled']
    list_filter = ['status_page_enabled']
    search_fields = ['name', 'user__username']
    prepopulated_fields = {'slug': ('name',)}

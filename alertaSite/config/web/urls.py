from django.urls import path
from . import views

app_name = 'web'

urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    
    # Landing & Downloads
    path('', views.landing_view, name='landing'),
    path('download/android/', views.download_apk_view, name='download_apk'),

    # Dashboard & Profile
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('settings/', views.settings_view, name='settings'),
    
    # Projects CRUD
    path('projects/', views.projects_list, name='projects_list'),
    path('projects/create/', views.project_create, name='project_create'),
    path('projects/<uuid:pk>/', views.project_detail, name='project_detail'),
    path('projects/<uuid:pk>/edit/', views.project_edit, name='project_edit'),
    path('projects/<uuid:pk>/delete/', views.project_delete, name='project_delete'),
    
    # Monitors CRUD & Actions
    path('monitors/create/', views.monitor_create, name='monitor_create'),
    path('monitors/<uuid:pk>/', views.monitor_detail, name='monitor_detail'),
    path('monitors/<uuid:pk>/edit/', views.monitor_edit, name='monitor_edit'),
    path('monitors/<uuid:pk>/delete/', views.monitor_delete, name='monitor_delete'),
    path('monitors/<uuid:pk>/toggle/', views.monitor_toggle, name='monitor_toggle'),
    path('monitors/<uuid:pk>/check/', views.monitor_run_check, name='monitor_run_check'),
    
    # Incidents
    path('incidents/', views.incidents_list, name='incidents_list'),
    path('incidents/<uuid:pk>/acknowledge/', views.incident_acknowledge, name='incident_acknowledge'),
    path('incidents/<uuid:pk>/resolve/', views.incident_resolve, name='incident_resolve'),
    
    # Notifications Center
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/<uuid:pk>/read/', views.notification_read, name='notification_read'),
    path('notifications/read-all/', views.notifications_read_all, name='notifications_read_all'),
    
    # AI Assistant
    path('ai-chat/', views.ai_chat_view, name='ai_chat'),
    path('ai-chat/create-session/', views.ai_chat_create_session, name='ai_chat_create_session'),
    
    # Billing & Subscriptions
    path('pricing/', views.pricing_view, name='pricing'),
    path('billing/success/', views.billing_success, name='billing_success'),
    path('billing/cancel/', views.billing_cancel, name='billing_cancel'),
    path('billing/portal/', views.billing_portal, name='billing_portal'),
    
    # Public Status Page
    path('status/<slug:slug>/', views.public_status_page, name='status_page'),
    path('api/status/<slug:slug>/', views.public_status_api, name='status_page_api'),
]

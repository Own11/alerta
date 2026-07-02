from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from accounts.views import RegisterView, UserDetailView
from projects.views import ProjectViewSet
from monitors.views import MonitorViewSet
from incidents.views import IncidentViewSet
from ai_assistant.views import AIChatSessionViewSet
from notifications.views import NotificationViewSet
from billing.views import CreateCheckoutSessionView, StripeWebhookView, CustomerPortalView

# Настройка REST API Роутера
router = routers.DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'monitors', MonitorViewSet, basename='monitor')
router.register(r'incidents', IncidentViewSet, basename='incident')
router.register(r'ai', AIChatSessionViewSet, basename='ai')
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/auth/register/', RegisterView.as_view(), name='api_register'),
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/profile/', UserDetailView.as_view(), name='api_profile'),
    path('api/', include(router.urls)),
    
    # Billing API / Webhooks
    path('api/billing/create-checkout-session/', CreateCheckoutSessionView.as_view(), name='api_create_checkout'),
    path('api/billing/customer-portal/', CustomerPortalView.as_view(), name='api_customer_portal'),
    path('api/billing/webhook/', StripeWebhookView.as_view(), name='stripe_webhook'),

    # Веб-интерфейс (Django Templates)
    path('', include('web.urls')),
]

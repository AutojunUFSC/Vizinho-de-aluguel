from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ServiceOrderViewSet

router = DefaultRouter()
router.register(r'service-orders', ServiceOrderViewSet, basename='service-order')

urlpatterns = [
    path('', include(router.urls)),
]
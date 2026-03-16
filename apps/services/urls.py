from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ServiceCategoryListView, ServiceCategoryDetailView,
    ServiceRequestViewSet, ServiceRequestMediaView
)

router = DefaultRouter()
router.register('service-requests', ServiceRequestViewSet, basename='service-request')

urlpatterns = [
    # Categorias
    path('categories/', ServiceCategoryListView.as_view(), name='category_list'),
    path('categories/<slug:slug>/', ServiceCategoryDetailView.as_view(), name='category_detail'),

    # Service Requests
    path('', include(router.urls)),

    # Mídia
    path('service-requests/<uuid:request_pk>/media/', ServiceRequestMediaView.as_view(), name='service_request_media'),
]
from django.contrib import admin
from .models import ServiceCategory, ServiceRequest, ServiceRequestMedia


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'order')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ('title', 'citizen', 'category', 'urgency', 'status', 'created_at')
    list_filter = ('status', 'urgency', 'category')
    search_fields = ('title', 'citizen__user__full_name')


@admin.register(ServiceRequestMedia)
class ServiceRequestMediaAdmin(admin.ModelAdmin):
    list_display = ('service_request', 'media_type', 'order', 'uploaded_at')
    list_filter = ('media_type',)
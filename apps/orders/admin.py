from django.contrib import admin
from .models import ServiceOrder

@admin.register(ServiceOrder)
class ServiceOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'service_request', 'citizen', 'mei_profile', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('citizen__user__full_name', 'mei_profile__razao_social')
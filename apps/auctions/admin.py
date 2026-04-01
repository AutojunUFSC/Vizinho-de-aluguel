from django.contrib import admin
from .models import MEICategorySubscription, Bid


@admin.register(MEICategorySubscription)
class MEICategorySubscriptionAdmin(admin.ModelAdmin):
    list_display = ('mei_profile', 'category', 'is_active', 'subscribed_at')
    list_filter = ('is_active',)


@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ('mei_profile', 'service_request', 'amount', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('mei_profile__user__full_name',)
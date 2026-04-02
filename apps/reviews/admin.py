from django.contrib import admin
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'service_order', 'reviewer', 'review_type', 'rating', 'created_at')
    list_filter = ('review_type', 'rating', 'created_at')
    search_fields = ('reviewer__full_name', 'comment')
    readonly_fields = ('created_at',)

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, CitizenProfile, MEIProfile, Address


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'full_name', 'user_type', 'is_active', 'is_staff')
    list_filter = ('user_type', 'is_active', 'is_staff')
    search_fields = ('email', 'full_name', 'cpf')
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Informações Pessoais', {'fields': ('full_name', 'phone', 'cpf', 'avatar', 'user_type')}),
        ('Permissões', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'user_type', 'password1', 'password2'),
        }),
    )


@admin.register(CitizenProfile)
class CitizenProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'rating_avg')
    search_fields = ('user__email', 'user__full_name')


@admin.register(MEIProfile)
class MEIProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'nome_fantasia', 'cnpj', 'verification_status', 'is_available')
    list_filter = ('verification_status', 'is_available')
    search_fields = ('user__email', 'user__full_name', 'cnpj', 'nome_fantasia')


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'label', 'street', 'city', 'is_primary')
    search_fields = ('user__email', 'street', 'city')
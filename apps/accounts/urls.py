from django.urls import path
from django.contrib.auth.views import PasswordResetDoneView
from . import views

urlpatterns = [
    # Auth
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('cadastro/cidadao/', views.register_citizen, name='register_citizen'),
    path('cadastro/mei/', views.register_mei, name='register_mei'),
    path('recuperar-senha/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('recuperar-senha/enviado/', PasswordResetDoneView.as_view(template_name='accounts/password_reset_done.html'), name='password_reset_done'),
    path('resetar-senha/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),

    # Dashboard
    path('dashboard/', views.dashboard_citizen, name='dashboard_citizen'),
    path('dashboard/mei/', views.dashboard_mei, name='dashboard_mei'),

    # Perfil
    path('meu-perfil/', views.my_profile, name='my_profile'),
    path('perfil/mei/<uuid:pk>/', views.mei_public_profile, name='mei_public_profile'),
    path('perfil/cidadao/<uuid:pk>/', views.citizen_public_profile, name='citizen_public_profile'),

    # Endereços
    path('meu-perfil/enderecos/novo/', views.address_create, name='address_create'),
    path('meu-perfil/enderecos/<uuid:pk>/editar/', views.address_update, name='address_update'),
    path('meu-perfil/enderecos/<uuid:pk>/excluir/', views.address_delete, name='address_delete'),
]

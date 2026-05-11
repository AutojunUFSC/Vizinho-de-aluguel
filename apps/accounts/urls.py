from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Perfil do usuário autenticado
    path('usuario/perfil/', views.profile_view, name='profile'),

    # Endereços
    path('usuario/enderecos/', views.address_list, name='address_list'),
    path('usuario/enderecos/novo/', views.address_create, name='address_create'),
    path('usuario/enderecos/<uuid:pk>/editar/', views.address_update, name='address_update'),
    path('usuario/enderecos/<uuid:pk>/excluir/', views.address_delete, name='address_delete'),

    # Diretório público de MEIs
    path('mei/', views.mei_list, name='mei_list'),
    path('mei/<uuid:pk>/', views.mei_detail, name='mei_detail'),

    # Configurações do Profissional
    path('profissional/disponibilidade/toggle/', views.toggle_availability, name='toggle_availability'),
]

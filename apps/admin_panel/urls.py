from django.urls import path

from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('meis/', views.mei_verification_list, name='mei_verification_list'),
    path('meis/<uuid:pk>/', views.mei_verification_detail, name='mei_verification_detail'),
    path('usuarios/', views.user_list, name='user_list'),
    path('pedidos/', views.order_list, name='order_list'),
]

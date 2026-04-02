from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='admin_dashboard'),
    path('verificacoes/', views.mei_verification_list, name='admin_mei_verification_list'),
    path('verificacoes/<uuid:pk>/', views.mei_verification_detail, name='admin_mei_verification_detail'),
    path('usuarios/', views.user_list, name='admin_user_list'),
    path('ordens/', views.order_list, name='admin_order_list'),
]

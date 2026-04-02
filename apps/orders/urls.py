from django.urls import path
from . import views

urlpatterns = [
    path('ordens/<uuid:pk>/', views.order_detail, name='order_detail'),
    path('ordens/<uuid:pk>/iniciar/', views.order_start, name='order_start'),
    path('ordens/<uuid:pk>/concluir/', views.order_complete, name='order_complete'),
    path('ordens/<uuid:pk>/confirmar/', views.order_confirm, name='order_confirm'),
    path('ordens/<uuid:pk>/cancelar/', views.order_cancel, name='order_cancel'),
]

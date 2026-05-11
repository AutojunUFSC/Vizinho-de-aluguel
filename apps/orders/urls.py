from django.urls import path

from . import views

app_name = 'orders'

urlpatterns = [
    path('pedidos/', views.order_list, name='order_list'),
    path('pedidos/<uuid:pk>/', views.order_detail, name='order_detail'),
    path('pedidos/<uuid:pk>/iniciar/', views.order_start, name='order_start'),
    path('pedidos/<uuid:pk>/concluir/', views.order_complete, name='order_complete'),
    path('pedidos/<uuid:pk>/confirmar/', views.order_confirm, name='order_confirm'),
    path('pedidos/<uuid:pk>/cancelar/', views.order_cancel, name='order_cancel'),
]

from django.urls import path
from . import views

urlpatterns = [
    # Inscrição em categorias
    path('meu-perfil/categorias/', views.mei_categories, name='mei_categories'),

    # Lances
    path('feed/<uuid:request_id>/lance/', views.bid_create, name='bid_create'),
    path('meus-lances/', views.my_bids, name='my_bids'),
    path('meus-lances/<uuid:bid_id>/editar/', views.bid_update, name='bid_update'),
    path('meus-lances/<uuid:bid_id>/retirar/', views.bid_withdraw, name='bid_withdraw'),
]

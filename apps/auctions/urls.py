from django.urls import path

from . import views

app_name = 'auctions'

urlpatterns = [
    # Inscrições do MEI em categorias
    path('categorias/inscricoes/', views.subscription_list, name='subscription_list'),
    path('categorias/inscrever/', views.subscription_create, name='subscription_create'),
    path('categorias/<uuid:category_id>/cancelar/', views.subscription_delete, name='subscription_delete'),

    # Lances do MEI
    path('lances/', views.my_bids, name='my_bids'),
    path('solicitacoes/<uuid:request_pk>/lance/', views.bid_create, name='bid_create'),
    path('lances/<uuid:pk>/editar/', views.bid_update, name='bid_update'),
    path('lances/<uuid:pk>/retirar/', views.bid_withdraw, name='bid_withdraw'),
    path('lances/<uuid:pk>/excluir/', views.bid_delete, name='bid_delete'),
]

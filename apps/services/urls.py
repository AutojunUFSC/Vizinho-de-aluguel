from django.urls import path
from . import views

urlpatterns = [
    # Categorias
    path('categorias/', views.category_list, name='category_list'),

    # Solicitações (Cidadão)
    path('solicitacoes/nova/', views.service_request_create, name='service_request_create'),
    path('solicitacoes/<uuid:pk>/', views.service_request_detail, name='service_request_detail'),
    path('solicitacoes/<uuid:pk>/editar/', views.service_request_update, name='service_request_update'),
    path('solicitacoes/<uuid:pk>/cancelar/', views.service_request_cancel, name='service_request_cancel'),
    path('solicitacoes/<uuid:pk>/aceitar/<uuid:bid_id>/', views.award_bid, name='award_bid'),
    path('solicitacoes/<uuid:pk>/media/<uuid:media_id>/excluir/', views.media_delete, name='media_delete'),

    # Feed (MEI)
    path('feed/', views.feed, name='feed'),
    path('feed/<uuid:pk>/', views.feed_detail, name='feed_detail'),
]

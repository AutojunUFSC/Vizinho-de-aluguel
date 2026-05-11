from django.urls import path

from . import views

app_name = 'services'

urlpatterns = [
    # Catálogo público de categorias
    path('categorias/', views.category_list, name='category_list'),
    path('categorias/<slug:slug>/', views.category_detail, name='category_detail'),

    # Solicitações do cidadão
    path('solicitacoes/minhas/', views.my_requests, name='my_requests'),
    path('solicitacoes/nova/', views.service_request_create, name='service_request_create'),
    path('solicitacoes/<uuid:pk>/', views.service_request_detail, name='service_request_detail'),
    path('solicitacoes/<uuid:pk>/editar/', views.service_request_update, name='service_request_update'),
    path('solicitacoes/<uuid:pk>/cancelar/', views.service_request_cancel, name='service_request_cancel'),

    # Mídias de uma solicitação
    path('solicitacoes/<uuid:request_pk>/midias/', views.request_media, name='request_media'),

    # Feed do MEI
    path('feed/', views.request_feed, name='request_feed'),

    # Adjudicação (cidadão escolhe lance vencedor → cria ServiceOrder)
    path('propostas/<uuid:bid_pk>/aceitar/', views.award_bid, name='award_bid'),
]

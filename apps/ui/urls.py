# ui/urls.py

from django.urls import path

from apps.auctions import views as auctions_views
from apps.orders import views as orders_views
from apps.services import views as services_views

from . import views

urlpatterns = [
    path("",                                        views.home),
    path('home/',                                   views.home,                     name='home'),
    path('usuario/',                                views.home_usuario,             name='home_usuario'),
    path('profissional/',                           views.home_profissional,        name='home_profissional'),

    # Solicitações — agora servidas pelas views Django de apps.services
    path('nova_solicitacao/',                       services_views.service_request_create, name='nova_solicitacao'),
    path('minhas_solicitacoes/',                    services_views.my_requests,            name='minhas_solicitacoes'),

    path('servicos/',                               views.servicos,                 name='servicos'),
    path('institucional/',                          views.institucional,            name='institucional'),
    path('contato/',                                views.contato,                  name='contato'),

    # Propostas e detalhes de solicitação — server-render via apps.services.service_request_detail
    path('solicitacao/<uuid:pk>/propostas/',        services_views.service_request_detail, name='propostas_solicitacao'),

    # Envio de lance pelo MEI — apps.auctions.bid_create
    path('solicitacao/<uuid:request_pk>/proposta/', auctions_views.bid_create,             name='fazer_proposta'),

    path('pedido/<uuid:pk>/',                       orders_views.order_detail,      name='acompanhamento_pedido'),
    path('mapa-do-site/',                           views.sitemap,                  name='sitemap'),
]

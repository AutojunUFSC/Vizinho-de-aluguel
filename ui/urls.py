from django.urls import path
from . import views

urlpatterns = [
    path("", views.home),
    path('home/', views.home, name='home'),
    path('cadastro/', views.cadastro, name='cadastro'),
    path('usuario/', views.home_usuario, name='home_usuario'),
    path('profissional/', views.home_profissional, name='home_profissional'),
    path('nova_solicitacao/', views.nova_solicitacao, name='nova_solicitacao'),
    path('minhas_solicitacoes/', views.minhas_solicitacoes, name='minhas_solicitacoes'),
    path('servicos/', views.servicos, name='servicos'),
    path('institucional/', views.institucional, name='institucional'),
    path('solicitacao/<str:pk>/propostas/', views.propostas_solicitacao, name='propostas_solicitacao'),
    path('solicitacao/<str:pk>/proposta/', views.fazer_proposta, name='fazer_proposta'),
    path('pedido/<str:pk>/', views.acompanhamento_pedido, name='acompanhamento_pedido'),
]

from django.urls import path
from . import views

urlpatterns = [
    path("", views.home),
    path('home/', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('cadastro/', views.cadastro, name='cadastro'),
    path('usuario/', views.home_usuario, name='home_usuario'),
    path('home-usuario/', views.home_usuario, name='home_usuario_alias'),
    path('profissional/', views.home_profissional, name='home_profissional'),
    path('feed/', views.home_profissional, name='feed'),
    path('nova_solicitacao/', views.nova_solicitacao, name='nova_solicitacao'),
    path('minhas_solicitacoes/', views.minhas_solicitacoes, name='minhas_solicitacoes'),
    path('servicos/', views.servicos, name='servicos'),
    path('institucional/', views.institucional, name='institucional'),
]

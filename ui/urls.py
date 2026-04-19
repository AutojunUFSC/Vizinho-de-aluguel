from django.urls import path
from . import views

urlpatterns = [
    path("", views.home),
    path('cadastro/', views.cadastro, name='cadastro'),
    path('usuario/', views.home_usuario, name='home_usuario'),
    path('home/', views.home, name='home'),
    path('nova_solicitacao/', views.nova_solicitacao, name='nova_solicitacao'),
    path('minhas_solicitacoes/', views.minhas_solicitacoes, name='minhas_solicitacoes')
]
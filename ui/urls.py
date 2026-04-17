from django.urls import path
from . import views

urlpatterns = [
    path("", views.home),
    path('cadastro/', views.cadastro, name='cadastro'),
    path('usuario/', views.home_usuario, name='home_usuario'),
    path('home/', views.home, name='home')
]
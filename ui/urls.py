from django.urls import path
from . import views

urlpatterns = [
    path("", views.home),
    path("contato/", views.contato, name = 'contato'),
]
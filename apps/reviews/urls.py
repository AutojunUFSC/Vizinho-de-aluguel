from django.urls import path
from . import views

urlpatterns = [
    path('ordens/<uuid:order_pk>/avaliar/', views.review_create, name='review_create'),
    path('minhas-avaliacoes/', views.my_reviews, name='my_reviews'),
]

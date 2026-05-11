from django.urls import path

from . import views

app_name = 'reviews'

urlpatterns = [
    path('avaliar/<uuid:order_pk>/', views.review_create, name='review_create'),
    path('minhas/', views.my_reviews, name='my_reviews'),
]

from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    RegisterView, UserMeView, CitizenProfileMeView,
    MEIProfileMeView, MEIProfileDetailView, MEIProfileListView,
    AddressViewSet
)

urlpatterns = [
    # Auth
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', TokenObtainPairView.as_view(), name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # User
    path('users/me/', UserMeView.as_view(), name='user_me'),

    # Perfis
    path('citizen-profiles/me/', CitizenProfileMeView.as_view(), name='citizen_profile_me'),
    path('mei-profiles/me/', MEIProfileMeView.as_view(), name='mei_profile_me'),
    path('mei-profiles/', MEIProfileListView.as_view(), name='mei_profile_list'),
    path('mei-profiles/<uuid:pk>/', MEIProfileDetailView.as_view(), name='mei_profile_detail'),

    # Endereços
    path('addresses/', AddressViewSet.as_view(), name='addresses'),
]

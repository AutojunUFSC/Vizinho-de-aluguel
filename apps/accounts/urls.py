from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    RegisterView, UserMeView, CitizenProfileMeView,
    MEIProfileMeView, MEIProfileDetailView, MEIProfileListView,
    AddressViewSet
)

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('users/me/', UserMeView.as_view(), name='user_me'),
    path('citizen-profiles/me/', CitizenProfileMeView.as_view(), name='citizen_profile_me'),
    path('mei-profiles/me/', MEIProfileMeView.as_view(), name='mei_profile_me'),
    path('mei-profiles/', MEIProfileListView.as_view(), name='mei_profile_list'),
    path('mei-profiles/<uuid:pk>/', MEIProfileDetailView.as_view(), name='mei_profile_detail'),
    path('addresses/', AddressViewSet.as_view(), name='addresses'),
]
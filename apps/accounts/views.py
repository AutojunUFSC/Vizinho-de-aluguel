from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
<<<<<<< HEAD
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
=======
>>>>>>> origin/feature/services-models
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, CitizenProfile, MEIProfile, Address
from .serializers import (
    RegisterSerializer, UserSerializer, UserMeSerializer,
    CitizenProfileSerializer, MEIProfileSerializer, AddressSerializer
)
<<<<<<< HEAD
from .permissions import IsCitizen, IsMEI, IsAdmin, IsOwner
=======
>>>>>>> origin/feature/services-models


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)


class UserMeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserMeSerializer
<<<<<<< HEAD
    permission_classes = (IsAuthenticated, IsOwner)
=======
    permission_classes = (IsAuthenticated,)
>>>>>>> origin/feature/services-models

    def get_object(self):
        return self.request.user


class CitizenProfileMeView(generics.RetrieveUpdateAPIView):
    serializer_class = CitizenProfileSerializer
<<<<<<< HEAD
    permission_classes = (IsAuthenticated, IsCitizen)
=======
    permission_classes = (IsAuthenticated,)
>>>>>>> origin/feature/services-models

    def get_object(self):
        return self.request.user.citizen_profile


class MEIProfileMeView(generics.RetrieveUpdateAPIView):
    serializer_class = MEIProfileSerializer
<<<<<<< HEAD
    permission_classes = (IsAuthenticated, IsMEI)
=======
    permission_classes = (IsAuthenticated,)
>>>>>>> origin/feature/services-models

    def get_object(self):
        return self.request.user.mei_profile


class MEIProfileDetailView(generics.RetrieveAPIView):
    serializer_class = MEIProfileSerializer
    permission_classes = (AllowAny,)
    queryset = MEIProfile.objects.filter(user__is_active=True)


class MEIProfileListView(generics.ListAPIView):
    serializer_class = MEIProfileSerializer
    permission_classes = (AllowAny,)

    def get_queryset(self):
        queryset = MEIProfile.objects.filter(user__is_active=True)
        city = self.request.query_params.get('city')
        is_available = self.request.query_params.get('is_available')
        if city:
            queryset = queryset.filter(city__icontains=city)
        if is_available:
            queryset = queryset.filter(is_available=True)
        return queryset


class AddressViewSet(generics.ListCreateAPIView):
    serializer_class = AddressSerializer
<<<<<<< HEAD
    permission_classes = (IsAuthenticated, IsOwner)
=======
    permission_classes = (IsAuthenticated,)
>>>>>>> origin/feature/services-models

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
<<<<<<< HEAD
        serializer.save(user=self.request.user)
=======
        serializer.save(user=self.request.user)
>>>>>>> origin/feature/services-models

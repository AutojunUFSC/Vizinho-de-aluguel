from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import ServiceCategory, ServiceRequest, ServiceRequestMedia
from .serializers import (
    ServiceCategorySerializer, ServiceRequestSerializer, ServiceRequestMediaSerializer
)
from apps.accounts.models import CitizenProfile


class ServiceCategoryListView(generics.ListAPIView):
    serializer_class = ServiceCategorySerializer
    permission_classes = (AllowAny,)
    queryset = ServiceCategory.objects.filter(is_active=True).order_by('order')


class ServiceCategoryDetailView(generics.RetrieveAPIView):
    serializer_class = ServiceCategorySerializer
    permission_classes = (AllowAny,)
    queryset = ServiceCategory.objects.filter(is_active=True)
    lookup_field = 'slug'


class ServiceRequestViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceRequestSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return ServiceRequest.objects.filter(
            citizen__user=self.request.user
        ).order_by('-created_at')

    def perform_create(self, serializer):
        citizen = CitizenProfile.objects.get(user=self.request.user)
        serializer.save(citizen=citizen)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @action(detail=False, methods=['get'], url_path='mine')
    def mine(self, request):
        status_filter = request.query_params.get('status')
        queryset = self.get_queryset()
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        service_request = self.get_object()
        if service_request.status in ['COMPLETED', 'CANCELLED']:
            return Response(
                {'error': 'Não é possível cancelar esta solicitação.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        service_request.status = 'CANCELLED'
        service_request.save()
        return Response({'status': 'Solicitação cancelada com sucesso.'})

    @action(detail=False, methods=['get'], url_path='feed', permission_classes=[IsAuthenticated])
    def feed(self, request):
        queryset = ServiceRequest.objects.filter(
            status__in=['OPEN', 'IN_AUCTION']
        ).order_by('-created_at')
        category = request.query_params.get('category')
        city = request.query_params.get('city')
        urgency = request.query_params.get('urgency')
        if category:
            queryset = queryset.filter(category__slug=category)
        if city:
            queryset = queryset.filter(address__city__icontains=city)
        if urgency:
            queryset = queryset.filter(urgency=urgency)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class ServiceRequestMediaView(generics.ListCreateAPIView):
    serializer_class = ServiceRequestMediaSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return ServiceRequestMedia.objects.filter(
            service_request_id=self.kwargs['request_pk']
        )

    def perform_create(self, serializer):
        service_request = ServiceRequest.objects.get(
            id=self.kwargs['request_pk'],
            citizen__user=self.request.user
        )
        serializer.save(service_request=service_request)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['service_request_id'] = self.kwargs['request_pk']
        return context

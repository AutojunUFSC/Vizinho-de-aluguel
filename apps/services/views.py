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
    """Lista todas as categorias de serviço ativas, ordenadas pelo campo order. Acessível sem autenticação."""

    serializer_class = ServiceCategorySerializer
    permission_classes = (AllowAny,)
    queryset = ServiceCategory.objects.filter(is_active=True).order_by('order')


class ServiceCategoryDetailView(generics.RetrieveAPIView):
    """Exibe os detalhes de uma categoria de serviço ativa pelo slug. Acessível sem autenticação."""

    serializer_class = ServiceCategorySerializer
    permission_classes = (AllowAny,)
    queryset = ServiceCategory.objects.filter(is_active=True)
    lookup_field = 'slug'


class ServiceRequestViewSet(viewsets.ModelViewSet):
    """
    Gerencia solicitações de serviço do cidadão autenticado.

    O queryset é restrito às solicitações do próprio cidadão.
    - mine: lista solicitações do cidadão com filtro opcional por status.
    - feed: lista solicitações OPEN e IN_AUCTION de todos os cidadãos (visível a MEIs),
            com filtros opcionais por category (slug), city e urgency.
    - cancel: cancela uma solicitação que não esteja COMPLETED ou CANCELLED.
    - award: adjudica um lance vencedor, cria a ServiceOrder, rejeita os demais lances
             e muda o status da solicitação para AWARDED.
    """

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

    @action(detail=True, methods=['post'], url_path='award')
    def award(self, request, pk=None):
        from django.utils import timezone
        from apps.auctions.models import Bid
        from apps.orders.models import ServiceOrder
        from apps.orders.serializers import ServiceOrderSerializer

        service_request = self.get_object()

        if service_request.status not in ['OPEN', 'IN_AUCTION']:
            return Response(
                {'error': 'Esta solicitação não pode ser adjudicada no estado atual.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bid_id = request.data.get('bid_id')
        if not bid_id:
            return Response({'error': 'bid_id é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            winning_bid = Bid.objects.get(
                id=bid_id, service_request=service_request, status='ACTIVE'
            )
        except Bid.DoesNotExist:
            return Response(
                {'error': 'Lance não encontrado ou não está ativo.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        Bid.objects.filter(
            service_request=service_request, status='ACTIVE'
        ).exclude(id=winning_bid.id).update(status='REJECTED')

        winning_bid.status = 'WINNER'
        winning_bid.save()

        service_request.status = 'AWARDED'
        service_request.awarded_at = timezone.now()
        service_request.save()

        order = ServiceOrder.objects.create(
            service_request=service_request,
            winning_bid=winning_bid,
            citizen=service_request.citizen,
            mei_profile=winning_bid.mei_profile,
            agreed_amount=winning_bid.amount,
            agreed_deadline=winning_bid.proposed_deadline,
        )
        return Response(ServiceOrderSerializer(order).data, status=status.HTTP_201_CREATED)

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
    """Lista e faz upload de mídias (imagem ou vídeo) de uma solicitação de serviço. Máximo de 5 mídias por solicitação."""

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

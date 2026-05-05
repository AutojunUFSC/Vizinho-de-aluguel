from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from apps.accounts.models import User
from .models import ServiceOrder
from .serializers import ServiceOrderSerializer


class ServiceOrderViewSet(viewsets.ModelViewSet):
    """
    Ordens são criadas automaticamente pela action award em ServiceRequestViewSet.
    """

    serializer_class = ServiceOrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = ServiceOrder.objects.select_related('citizen__user', 'mei_profile__user')
        if user.user_type == User.UserType.CIDADAO:
            return qs.filter(citizen__user=user)
        if user.user_type == User.UserType.MEI:
            return qs.filter(mei_profile__user=user)
        return ServiceOrder.objects.none()

    @action(detail=False, methods=['get'])
    def mine(self, request):
        return self.list(request)

    def _transition(self, order, owner, required_status, new_status, timestamp_field, message, error_msg):
        if owner != self.request.user:
            return Response({'error': error_msg}, status=status.HTTP_403_FORBIDDEN)
        if order.status != required_status:
            return Response({'error': 'Status inválido para esta operação.'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = new_status
        setattr(order, timestamp_field, timezone.now())
        order.save()
        return Response({'status': message})

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        order = self.get_object()
        return self._transition(
            order, order.mei_profile.user,
            ServiceOrder.Status.PENDING_START, ServiceOrder.Status.IN_PROGRESS,
            'started_at', 'Serviço iniciado com sucesso!',
            'Apenas o MEI responsável pode iniciar o serviço.',
        )

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        order = self.get_object()
        return self._transition(
            order, order.mei_profile.user,
            ServiceOrder.Status.IN_PROGRESS, ServiceOrder.Status.COMPLETED,
            'completed_at', 'Serviço concluído com sucesso!',
            'Apenas o MEI responsável pode concluir o serviço.',
        )

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        order = self.get_object()
        return self._transition(
            order, order.citizen.user,
            ServiceOrder.Status.COMPLETED, ServiceOrder.Status.COMPLETED,
            'citizen_confirmed_at', 'Serviço confirmado pelo cidadão!',
            'Apenas o cidadão pode confirmar o serviço.',
        )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        if order.citizen.user != request.user and order.mei_profile.user != request.user:
            return Response({'error': 'Sem permissão para cancelar esta ordem.'}, status=status.HTTP_403_FORBIDDEN)
        if order.status in (ServiceOrder.Status.COMPLETED, ServiceOrder.Status.CANCELLED):
            return Response({'error': 'Não é possível cancelar esta ordem.'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = ServiceOrder.Status.CANCELLED
        order.save()
        return Response({'status': 'Serviço cancelado!'})

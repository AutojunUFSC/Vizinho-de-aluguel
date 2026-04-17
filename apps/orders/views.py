from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import ServiceOrder
from .serializers import ServiceOrderSerializer


class ServiceOrderViewSet(viewsets.ModelViewSet):
    """
    Gerencia ordens de serviço. Ordens são criadas automaticamente pela action award
    em ServiceRequestViewSet e não devem ser criadas ou editadas diretamente.

    - mine: retorna as ordens do usuário autenticado (filtra por citizen ou mei_profile conforme user_type).
    - start: transição PENDING_START → IN_PROGRESS; registra started_at.
    - complete: transição IN_PROGRESS → COMPLETED; registra completed_at.
    - confirm: registra citizen_confirmed_at em uma ordem COMPLETED.
    - cancel: cancela a ordem independentemente do status atual.
    """

    queryset = ServiceOrder.objects.all()
    serializer_class = ServiceOrderSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def mine(self, request):
        user = request.user
        if getattr(user, 'user_type', None) == 'CIDADAO':
            orders = self.queryset.filter(citizen__user=user)
        else:
            orders = self.queryset.filter(mei_profile__user=user)
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        order = self.get_object()
        if order.status == 'PENDING_START':
            order.status = 'IN_PROGRESS'
            order.started_at = timezone.now()
            order.save()
            return Response({'status': 'Serviço iniciado com sucesso!'})
        return Response({'error': 'Não é possível iniciar esta ordem.'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        order = self.get_object()
        if order.status == 'IN_PROGRESS':
            order.status = 'COMPLETED'
            order.completed_at = timezone.now()
            order.save()
            return Response({'status': 'Serviço concluído com sucesso!'})
        return Response({'error': 'Não é possível concluir esta ordem.'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        order = self.get_object()
        if order.status == 'COMPLETED':
            order.citizen_confirmed_at = timezone.now()
            order.save()
            return Response({'status': 'Serviço confirmado pelo cidadão!'})
        return Response({'error': 'Não é possível confirmar esta ordem.'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        order.status = 'CANCELLED'
        order.save()
        return Response({'status': 'Serviço cancelado!'})

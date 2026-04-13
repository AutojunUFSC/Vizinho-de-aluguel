from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import ServiceOrder
from .serializers import ServiceOrderSerializer

class ServiceOrderViewSet(viewsets.ModelViewSet):
    queryset = ServiceOrder.objects.all()
    serializer_class = ServiceOrderSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def mine(self, request):
        # Retorna apenas as ordens do usuário logado (seja Cidadão ou MEI)
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
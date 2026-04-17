from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import MEICategorySubscription, Bid
from .serializers import MEICategorySubscriptionSerializer, BidSerializer


class MEICategorySubscriptionViewSet(viewsets.ViewSet):
    """
    Gerencia as inscrições do MEI em categorias de serviço.

    - list: retorna as categorias em que o MEI autenticado está inscrito.
    - create: inscreve o MEI em uma ou mais categorias de uma vez (body: {category_ids: [...]}).
    - destroy: remove a inscrição do MEI em uma categoria pelo ID da categoria.
    """

    permission_classes = (IsAuthenticated,)

    def list(self, request):
        queryset = MEICategorySubscription.objects.filter(
            mei_profile=request.user.mei_profile
        )
        serializer = MEICategorySubscriptionSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request):
        category_ids = request.data.get('category_ids', [])
        mei = request.user.mei_profile
        created = []
        for cat_id in category_ids:
            obj, _ = MEICategorySubscription.objects.get_or_create(
                mei_profile=mei,
                category_id=cat_id,
                defaults={'is_active': True}
            )
            created.append(obj)
        serializer = MEICategorySubscriptionSerializer(created, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk=None):
        try:
            sub = MEICategorySubscription.objects.get(
                mei_profile=request.user.mei_profile,
                category_id=pk
            )
            sub.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except MEICategorySubscription.DoesNotExist:
            return Response({'error': 'Inscrição não encontrada.'}, status=status.HTTP_404_NOT_FOUND)


class BidViewSet(viewsets.ModelViewSet):
    """
    Gerencia lances (bids) de MEIs em solicitações de serviço.

    Criação valida: verificação do MEI, inscrição ativa na categoria da solicitação,
    ausência de lance ACTIVE duplicado e respeito ao budget_max.
    - mine: lista os lances do MEI autenticado.
    - withdraw: retira um lance ACTIVE, marcando-o como WITHDRAWN.
    """

    serializer_class = BidSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Bid.objects.filter(mei_profile=self.request.user.mei_profile)

    def perform_create(self, serializer):
        serializer.save(mei_profile=self.request.user.mei_profile)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @action(detail=False, methods=['get'], url_path='mine')
    def mine(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='withdraw')
    def withdraw(self, request, pk=None):
        bid = self.get_object()
        if bid.status != 'ACTIVE':
            return Response(
                {'error': 'Só é possível retirar lances ativos.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        bid.status = 'WITHDRAWN'
        bid.save()
        return Response({'status': 'Lance retirado com sucesso.'})
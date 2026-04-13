from rest_framework import viewsets
from rest_framework.response import Response

class ReviewViewSet(viewsets.ViewSet):
    # View fantasma só pro roteador parar de travar e o servidor ligar
    def list(self, request):
        return Response([])
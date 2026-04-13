from rest_framework import serializers
from .models import ServiceOrder

class ServiceOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceOrder
        fields = '__all__'
        # Conforme a T-088, ordens não são editadas diretamente por aqui, só via actions
        read_only_fields = [f.name for f in ServiceOrder._meta.fields]
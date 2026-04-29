from rest_framework import serializers
from .models import ServiceCategory, ServiceRequest, ServiceRequestMedia
from apps.accounts.serializers import AddressSerializer


class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = ('id', 'name', 'slug', 'icon')


class ServiceRequestMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceRequestMedia
        fields = ('id', 'file', 'media_type', 'order', 'uploaded_at')
        read_only_fields = ('id', 'uploaded_at')

    def validate(self, data):
        request = self.context.get('request')
        service_request_id = self.context.get('service_request_id')
        count = ServiceRequestMedia.objects.filter(
            service_request_id=service_request_id
        ).count()
        if count >= 5:
            raise serializers.ValidationError('Máximo de 5 mídias por solicitação.')
        return data


class ServiceRequestSerializer(serializers.ModelSerializer):
    media = ServiceRequestMediaSerializer(many=True, read_only=True)
    category_detail = ServiceCategorySerializer(source='category', read_only=True)
    address_detail = AddressSerializer(source='address', read_only=True)

    class Meta:
        model = ServiceRequest
        fields = (
            'id', 'title', 'description', 'category', 'category_detail',
            'address', 'address_detail', 'urgency', 'status', 'budget_max',
            'auction_end_at', 'desired_deadline', 'created_at',
            'awarded_at', 'media'
        )
        read_only_fields = ('id', 'status', 'created_at', 'awarded_at')

    def validate_auction_end_at(self, value):
        from django.utils import timezone
        if value and value <= timezone.now():
            raise serializers.ValidationError('A data do leilão deve ser no futuro.')
        return value

    def validate_address(self, value):
        request = self.context.get('request')
        if value and value.user != request.user:
            raise serializers.ValidationError('Este endereço não pertence ao usuário.')
        return value
from rest_framework import serializers
from .models import MEICategorySubscription, Bid
from apps.services.models import ServiceRequest


class MEICategorySubscriptionSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)

    class Meta:
        model = MEICategorySubscription
        fields = ['id', 'category', 'category_name', 'category_slug', 'is_active', 'subscribed_at']
        read_only_fields = ['id', 'subscribed_at']


class BidSerializer(serializers.ModelSerializer):
    mei_name = serializers.CharField(source='mei_profile.user.full_name', read_only=True)
    service_request_title = serializers.CharField(source='service_request.title', read_only=True)

    class Meta:
        model = Bid
        fields = [
            'id', 'service_request', 'service_request_title',
            'mei_profile', 'mei_name', 'amount', 'estimated_hours',
            'proposed_deadline', 'notes', 'status', 'created_at',
        ]
        read_only_fields = ['id', 'mei_profile', 'status', 'created_at']

    def validate(self, data):
        request = self.context['request']
        mei = request.user.mei_profile

        if mei.verification_status != 'VERIFIED':
            raise serializers.ValidationError("Apenas MEIs verificados podem enviar lances.")

        service_request = data.get('service_request')
        if service_request:
            if not mei.category_subscriptions.filter(
                category=service_request.category, is_active=True
            ).exists():
                raise serializers.ValidationError("MEI não está inscrito nesta categoria.")

            if Bid.objects.filter(
                service_request=service_request, mei_profile=mei, status='ACTIVE'
            ).exists():
                raise serializers.ValidationError("Você já possui um lance ativo nesta solicitação.")

            if data.get('amount') and service_request.budget_max:
                if data['amount'] > service_request.budget_max:
                    raise serializers.ValidationError("O valor do lance não pode exceder o orçamento máximo.")

        return data

    def create(self, validated_data):
        validated_data['mei_profile'] = self.context['request'].user.mei_profile
        return super().create(validated_data)

from rest_framework import serializers
from .models import MEICategorySubscription, Bid
from apps.services.models import ServiceCategory


class MEICategorySubscriptionSerializer(serializers.ModelSerializer):
    category_detail = serializers.SerializerMethodField()

    class Meta:
        model = MEICategorySubscription
        fields = ('id', 'category', 'category_detail', 'is_active', 'subscribed_at')
        read_only_fields = ('id', 'subscribed_at')

    def get_category_detail(self, obj):
        return {'id': str(obj.category.id), 'name': obj.category.name, 'slug': obj.category.slug}


class BidSerializer(serializers.ModelSerializer):
    mei_profile_detail = serializers.SerializerMethodField()

    class Meta:
        model = Bid
        fields = (
            'id', 'service_request', 'amount', 'estimated_hours',
            'proposed_deadline', 'notes', 'status', 'created_at', 'mei_profile_detail'
        )
        read_only_fields = ('id', 'status', 'created_at')

    def get_mei_profile_detail(self, obj):
        return {
            'id': str(obj.mei_profile.id),
            'nome_fantasia': obj.mei_profile.nome_fantasia,
            'rating_avg': str(obj.mei_profile.rating_avg),
        }

    def validate(self, data):
        request = self.context.get('request')
        user = request.user

        if not hasattr(user, 'mei_profile'):
            raise serializers.ValidationError('Apenas MEIs podem enviar lances.')

        mei = user.mei_profile

        if mei.verification_status != 'VERIFIED':
            raise serializers.ValidationError('Seu perfil MEI precisa estar verificado para enviar lances.')

        service_request = data.get('service_request')

        if service_request.status not in ['OPEN', 'IN_AUCTION']:
            raise serializers.ValidationError('Esta solicitação não está aceitando lances.')

        subscribed = mei.category_subscriptions.filter(
            category=service_request.category, is_active=True
        ).exists()
        if not subscribed:
            raise serializers.ValidationError('Você não está inscrito na categoria desta solicitação.')

        already_bid = Bid.objects.filter(
            service_request=service_request, mei_profile=mei, status='ACTIVE'
        ).exists()
        if already_bid:
            raise serializers.ValidationError('Você já possui um lance ativo nesta solicitação.')

        if service_request.budget_max and data.get('amount') > service_request.budget_max:
            raise serializers.ValidationError('Seu lance excede o orçamento máximo do cliente.')

        return data
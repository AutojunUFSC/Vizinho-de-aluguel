from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, CitizenProfile, MEIProfile, Address


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('email', 'full_name', 'phone', 'cpf', 'user_type', 'password', 'password_confirm')

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({'password': 'As senhas não coincidem.'})
        if data['user_type'] == User.UserType.ADMIN:
            raise serializers.ValidationError({'user_type': 'Não é possível se cadastrar como admin.'})
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'phone', 'avatar', 'user_type', 'created_at')
        read_only_fields = ('id', 'created_at')


class CitizenProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CitizenProfile
        fields = ('id', 'rating_avg', 'total_services_requested', 'default_address')
        read_only_fields = ('id', 'rating_avg', 'total_services_requested')


class MEIProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MEIProfile
        fields = (
            'id', 'cnpj', 'razao_social', 'nome_fantasia', 'verification_status',
            'bio', 'service_radius_km', 'city', 'rating_avg',
            'total_services_completed', 'is_available', 'cnpj_file', 'whatsapp_link'
        )
        read_only_fields = ('id', 'verification_status', 'rating_avg', 'total_services_completed')


class UserMeSerializer(serializers.ModelSerializer):
    citizen_profile = CitizenProfileSerializer(read_only=True)
    mei_profile = MEIProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'phone', 'avatar', 'user_type', 'created_at', 'citizen_profile', 'mei_profile')
        read_only_fields = ('id', 'email', 'user_type', 'created_at')


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ('id', 'label', 'cep', 'street', 'number', 'complement', 'neighborhood', 'city', 'state', 'latitude', 'longitude', 'is_primary')
        read_only_fields = ('id',)

    def validate_cep(self, value):
        cep = value.replace('-', '').replace(' ', '')
        if len(cep) != 8 or not cep.isdigit():
            raise serializers.ValidationError('CEP inválido. Use o formato 00000-000.')
        return value
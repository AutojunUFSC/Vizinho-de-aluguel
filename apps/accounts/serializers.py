# apps/accounts/serializers.py

import re
import urllib.request
import json

from rest_framework import serializers
from .models import User, CitizenProfile, MEIProfile, Address


# ─────────────────────────────────────────────────────────────
#  Helpers de validação
# ─────────────────────────────────────────────────────────────

def _cnpj_digits_valid(cnpj: str) -> bool:
    """
    Valida os dígitos verificadores do CNPJ (algoritmo oficial).
    Pesos de 2 a 9 aplicados da direita para esquerda, ciclicamente.
    """
    if len(cnpj) != 14 or len(set(cnpj)) == 1:
        return False

    def calc(cnpj: str, n: int) -> int:
        weights = [0] * n
        p = 2
        for i in range(n - 1, -1, -1):
            weights[i] = p
            p = 2 if p == 9 else p + 1
        s = sum(int(cnpj[i]) * weights[i] for i in range(n))
        r = s % 11
        return 0 if r < 2 else 11 - r

    return (
        calc(cnpj, 12) == int(cnpj[12]) and
        calc(cnpj, 13) == int(cnpj[13])
    )


def _clean_cnpj(value: str) -> str:
    """Remove máscara e valida formato do CNPJ."""
    digits = re.sub(r'\D', '', value)
    if len(digits) != 14:
        raise serializers.ValidationError('CNPJ deve conter 14 dígitos.')
    if not _cnpj_digits_valid(digits):
        raise serializers.ValidationError('CNPJ inválido. Verifique os dígitos.')
    return digits


def _validate_cnpj_receita(cnpj_digits: str) -> dict:
    """
    Consulta a API pública ReceitaWS.
    Retorna {} silenciosamente se a API estiver fora do ar.
    Levanta ValidationError com string simples se inativo.
    """
    url = f'https://www.receitaws.com.br/v1/cnpj/{cnpj_digits}'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'VizinhoDeAluguel/1.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
    except Exception:
        return {}

    situacao = data.get('situacao', '')
    if data.get('status') == 'ERROR' or situacao != 'ATIVA':
        raise serializers.ValidationError(
            f'CNPJ com situação "{situacao or "não encontrado"}" na Receita Federal. '
            f'Apenas CNPJs ativos são aceitos.'
        )

    return data


def _clean_phone(value: str) -> str:
    """Valida e normaliza telefone brasileiro."""
    if not value:
        return value
    digits = re.sub(r'\D', '', value)
    if digits.startswith('55') and len(digits) in (12, 13):
        digits = digits[2:]
    if len(digits) not in (10, 11):
        raise serializers.ValidationError('Telefone inválido. Use o formato (48) 99999-9999.')
    ddd = int(digits[:2])
    if not (11 <= ddd <= 99):
        raise serializers.ValidationError('DDD inválido.')
    return digits


# ─────────────────────────────────────────────────────────────
#  Serializers
# ─────────────────────────────────────────────────────────────

class RegisterSerializer(serializers.ModelSerializer):
    password         = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True)
    cnpj             = serializers.CharField(write_only=True, required=False, allow_blank=True, default='')

    class Meta:
        model  = User
        fields = ('email', 'full_name', 'phone', 'cpf', 'user_type', 'password', 'password_confirm', 'cnpj')
        extra_kwargs = {'cpf': {'write_only': True}}

    def validate_phone(self, value):
        if value:
            return _clean_phone(value)
        return value

    def validate_cnpj(self, value):
        """Valida dígitos — chamado por campo antes do validate()."""
        if value:
            return _clean_cnpj(value)
        return value

    def validate(self, data):
        # Senhas
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({'password': 'As senhas não coincidem.'})

        # Bloqueio de admin
        if data['user_type'] == User.UserType.ADMIN:
            raise serializers.ValidationError({'user_type': 'Não é possível se cadastrar como admin.'})

        # Validações extras para MEI
        if data['user_type'] == User.UserType.MEI:
            cnpj_digits = data.get('cnpj', '')

            if not cnpj_digits:
                raise serializers.ValidationError({'cnpj': 'CNPJ é obrigatório para MEI.'})

            # Duplicata
            if MEIProfile.objects.filter(cnpj=cnpj_digits).exists():
                raise serializers.ValidationError({'cnpj': 'Este CNPJ já está cadastrado na plataforma.'})

            # Receita Federal
            try:
                receita_data = _validate_cnpj_receita(cnpj_digits)
            except serializers.ValidationError as e:
                raise serializers.ValidationError({'cnpj': e.detail})

            # Preenche razao_social automaticamente
            if receita_data.get('nome'):
                data['_razao_social']  = receita_data['nome']
                data['_nome_fantasia'] = receita_data.get('fantasia') or receita_data['nome']

        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        cnpj          = validated_data.pop('cnpj', '')
        razao_social  = validated_data.pop('_razao_social', '')
        nome_fantasia = validated_data.pop('_nome_fantasia', '')
        password      = validated_data.pop('password')

        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()

        if user.user_type == User.UserType.MEI:
            MEIProfile.objects.create(
                user=user,
                cnpj=cnpj,
                razao_social=razao_social,
                nome_fantasia=nome_fantasia,
            )

        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model            = User
        fields           = ('id', 'email', 'full_name', 'phone', 'avatar', 'user_type', 'created_at')
        read_only_fields = ('id', 'created_at')


class CitizenProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model            = CitizenProfile
        fields           = ('id', 'rating_avg', 'total_services_requested', 'default_address')
        read_only_fields = ('id', 'rating_avg', 'total_services_requested')


class MEIProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model  = MEIProfile
        fields = (
            'id', 'cnpj', 'razao_social', 'nome_fantasia', 'verification_status',
            'bio', 'service_radius_km', 'city', 'rating_avg',
            'total_services_completed', 'is_available', 'cnpj_file', 'whatsapp_link'
        )
        read_only_fields = ('id', 'verification_status', 'rating_avg', 'total_services_completed')
        extra_kwargs     = {'cnpj_file': {'write_only': True}}


class UserMeSerializer(serializers.ModelSerializer):
    citizen_profile = CitizenProfileSerializer(read_only=True)
    mei_profile     = MEIProfileSerializer(read_only=True)

    class Meta:
        model            = User
        fields           = ('id', 'email', 'full_name', 'phone', 'avatar', 'user_type', 'created_at', 'citizen_profile', 'mei_profile')
        read_only_fields = ('id', 'email', 'user_type', 'created_at')


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model            = Address
        fields           = ('id', 'label', 'cep', 'street', 'number', 'complement', 'neighborhood', 'city', 'state', 'latitude', 'longitude', 'is_primary')
        read_only_fields = ('id',)

    def validate_cep(self, value):
        cep = value.replace('-', '').replace(' ', '')
        if len(cep) != 8 or not cep.isdigit():
            raise serializers.ValidationError('CEP inválido. Use o formato 00000-000.')
        return value
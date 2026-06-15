import json
import re
import urllib.request

from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import Address, CitizenProfile, MEIProfile, User


# ─── Helpers de validação (preservados de serializers.py) ────────────────────

def _cnpj_digits_valid(cnpj: str) -> bool:
    if len(cnpj) != 14 or len(set(cnpj)) == 1:
        return False

    def calc(cnpj_str: str, n: int) -> int:
        weights = [0] * n
        p = 2
        for i in range(n - 1, -1, -1):
            weights[i] = p
            p = 2 if p == 9 else p + 1
        s = sum(int(cnpj_str[i]) * weights[i] for i in range(n))
        r = s % 11
        return 0 if r < 2 else 11 - r

    return calc(cnpj, 12) == int(cnpj[12]) and calc(cnpj, 13) == int(cnpj[13])


def _clean_cnpj_digits(value: str) -> str:
    digits = re.sub(r'\D', '', value or '')
    if len(digits) != 14:
        raise forms.ValidationError('CNPJ deve conter 14 dígitos.')
    if not _cnpj_digits_valid(digits):
        raise forms.ValidationError('CNPJ inválido. Verifique os dígitos.')
    return digits


def _query_receita(cnpj_digits: str) -> dict:
    """Consulta ReceitaWS. Retorna {} se a API estiver fora; valida ATIVO."""
    url = f'https://www.receitaws.com.br/v1/cnpj/{cnpj_digits}'
    try:
        req = urllib.request.Request(
            url, headers={'User-Agent': 'VizinhoDeAluguel/1.0'}
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
    except Exception:
        return {}

    situacao = data.get('situacao', '')
    if data.get('status') == 'ERROR' or situacao != 'ATIVA':
        raise forms.ValidationError(
            f'CNPJ com situação "{situacao or "não encontrado"}" na Receita Federal. '
            f'Apenas CNPJs ativos são aceitos.'
        )
    return data


def _clean_phone(value: str) -> str:
    if not value:
        return value
    digits = re.sub(r'\D', '', value)
    if digits.startswith('55') and len(digits) in (12, 13):
        digits = digits[2:]
    if len(digits) not in (10, 11):
        raise forms.ValidationError('Telefone inválido. Use o formato (48) 99999-9999.')
    ddd = int(digits[:2])
    if not (11 <= ddd <= 99):
        raise forms.ValidationError('DDD inválido.')
    return digits


# ─── Forms ───────────────────────────────────────────────────────────────────

class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'placeholder': 'seu@email.com', 'autocomplete': 'email'}),
    )
    password = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={'placeholder': 'Sua senha', 'autocomplete': 'current-password'}),
    )


class CitizenRegisterForm(forms.ModelForm):
    password = forms.CharField(
        label='Senha',
        min_length=6,
        widget=forms.PasswordInput(attrs={'placeholder': 'Mínimo 6 caracteres'}),
    )
    password_confirm = forms.CharField(
        label='Confirmar Senha',
        widget=forms.PasswordInput(attrs={'placeholder': 'Repita a senha'}),
    )

    class Meta:
        model = User
        fields = ('email', 'full_name', 'phone', 'cpf')

    def clean_phone(self):
        return _clean_phone(self.cleaned_data.get('phone'))

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get('password')
        password_confirm = cleaned.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', 'As senhas não coincidem.')
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = User.UserType.CIDADAO
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            # Signal create_user_profile cria o CitizenProfile automaticamente.
        return user


class MEIRegisterForm(forms.ModelForm):
    password = forms.CharField(
        label='Senha',
        min_length=6,
        widget=forms.PasswordInput(attrs={'placeholder': 'Mínimo 6 caracteres'}),
    )
    password_confirm = forms.CharField(
        label='Confirmar Senha',
        widget=forms.PasswordInput(attrs={'placeholder': 'Repita a senha'}),
    )
    cnpj = forms.CharField(label='CNPJ', max_length=18)
    razao_social = forms.CharField(label='Razão Social', max_length=255, required=False)
    nome_fantasia = forms.CharField(label='Nome Fantasia', max_length=255, required=False)
    cnpj_file = forms.FileField(label='Cartão CNPJ (PDF ou imagem)', required=False)

    class Meta:
        model = User
        fields = ('email', 'full_name', 'phone', 'cpf')

    def clean_phone(self):
        return _clean_phone(self.cleaned_data.get('phone'))

    def clean_cnpj(self):
        # ⚠ MODO DE TESTE: validação de CNPJ desativada direto no código.
        # Aceita qualquer CNPJ de 14 dígitos (sem checksum, sem ReceitaWS).
        # Para reativar, restaurar: digits = _clean_cnpj_digits(raw)
        raw = self.cleaned_data.get('cnpj', '')
        digits = re.sub(r'\D', '', raw or '')
        if len(digits) != 14:
            raise forms.ValidationError('CNPJ deve conter 14 dígitos.')
        if MEIProfile.objects.filter(cnpj=digits).exists():
            raise forms.ValidationError('Este CNPJ já está cadastrado na plataforma.')
        return digits

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get('password')
        password_confirm = cleaned.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', 'As senhas não coincidem.')

        skip_receita = True  # ⚠ MODO DE TESTE: não consulta a ReceitaWS.
        cnpj_digits = cleaned.get('cnpj')
        if cnpj_digits and not skip_receita:
            try:
                receita_data = _query_receita(cnpj_digits)
            except forms.ValidationError as e:
                self.add_error('cnpj', e)
            else:
                # Preenche razão social/nome fantasia a partir da Receita se ausentes
                if not cleaned.get('razao_social') and receita_data.get('nome'):
                    cleaned['razao_social'] = receita_data['nome']
                if not cleaned.get('nome_fantasia'):
                    cleaned['nome_fantasia'] = (
                        receita_data.get('fantasia')
                        or receita_data.get('nome')
                        or 'MEI'
                    )

        # Se Receita falhou silenciosamente e usuário não preencheu, usar nome
        if not cleaned.get('razao_social'):
            cleaned['razao_social'] = cleaned.get('full_name', 'MEI')
        if not cleaned.get('nome_fantasia'):
            cleaned['nome_fantasia'] = cleaned.get('full_name', 'MEI')

        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = User.UserType.MEI
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            # ⚠ MODO DE TESTE: já verifica o MEI para que possa dar lances
            # sem precisar de aprovação manual no painel admin.
            verification_status = MEIProfile.VerificationStatus.VERIFIED
            # Signal de accounts NÃO cria MEIProfile — fazemos manualmente:
            MEIProfile.objects.create(
                user=user,
                cnpj=self.cleaned_data['cnpj'],
                razao_social=self.cleaned_data['razao_social'],
                nome_fantasia=self.cleaned_data['nome_fantasia'],
                cnpj_file=self.cleaned_data.get('cnpj_file') or None,
                verification_status=verification_status,
            )
        return user


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('full_name', 'phone', 'avatar')

    def clean_phone(self):
        return _clean_phone(self.cleaned_data.get('phone'))


class CitizenProfileForm(forms.ModelForm):
    class Meta:
        model = CitizenProfile
        fields = ('default_address',)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['default_address'].queryset = Address.objects.filter(user=user)


class MEIProfileForm(forms.ModelForm):
    class Meta:
        model = MEIProfile
        fields = ('nome_fantasia', 'bio', 'service_radius_km', 'city', 'is_available', 'whatsapp_link')


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = (
            'label', 'cep', 'street', 'number', 'complement',
            'neighborhood', 'city', 'state', 'latitude', 'longitude', 'is_primary',
        )
        widgets = {
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
        }

    def clean_cep(self):
        cep = (self.cleaned_data.get('cep') or '').replace('-', '').replace(' ', '')
        if len(cep) != 8 or not cep.isdigit():
            raise forms.ValidationError('CEP inválido. Use o formato 00000-000.')
        return self.cleaned_data['cep']

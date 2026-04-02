from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import User, CitizenProfile, MEIProfile, Address


class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'placeholder': 'seu@email.com'}),
    )
    password = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={'placeholder': 'Sua senha'}),
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

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', 'As senhas não coincidem.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = User.UserType.CIDADAO
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
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
    razao_social = forms.CharField(label='Razão Social', max_length=255)
    nome_fantasia = forms.CharField(label='Nome Fantasia', max_length=255)
    cnpj_file = forms.FileField(label='Cartão CNPJ (PDF ou imagem)', required=False)

    class Meta:
        model = User
        fields = ('email', 'full_name', 'phone', 'cpf')

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', 'As senhas não coincidem.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = User.UserType.MEI
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            # O signal cria o MEIProfile, mas precisamos atualizar com os dados do form
            mei_profile = user.mei_profile
            mei_profile.cnpj = self.cleaned_data['cnpj']
            mei_profile.razao_social = self.cleaned_data['razao_social']
            mei_profile.nome_fantasia = self.cleaned_data['nome_fantasia']
            if self.cleaned_data.get('cnpj_file'):
                mei_profile.cnpj_file = self.cleaned_data['cnpj_file']
            mei_profile.save()
        return user


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('full_name', 'phone', 'avatar')


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
        fields = ('label', 'cep', 'street', 'number', 'complement', 'neighborhood', 'city', 'state', 'latitude', 'longitude', 'is_primary')
        widgets = {
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
        }

    def clean_cep(self):
        cep = self.cleaned_data['cep'].replace('-', '').replace(' ', '')
        if len(cep) != 8 or not cep.isdigit():
            raise forms.ValidationError('CEP inválido. Use o formato 00000-000.')
        return self.cleaned_data['cep']

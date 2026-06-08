import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from .managers import CustomUserManager


class User(AbstractBaseUser, PermissionsMixin):

    class UserType(models.TextChoices):
        CIDADAO = 'CIDADAO', 'Cidadão'
        MEI = 'MEI', 'MEI'
        ADMIN = 'ADMIN', 'Admin'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, unique=True, blank=True, null=True)
    cpf = models.CharField(max_length=14, unique=True, blank=True, null=True)
    full_name = models.CharField(max_length=255)
    user_type = models.CharField(max_length=20, choices=UserType.choices)
    is_phone_verified = models.BooleanField(default=False)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # Integração Gov.BR (Login Único) — preenchidos no callback OIDC.
    govbr_verified = models.BooleanField(default=False)
    govbr_level = models.CharField(max_length=10, blank=True, null=True)  # bronze/silver/gold

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name', 'user_type']

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'

    @property
    def first_name(self):
        if self.full_name:
            parts = self.full_name.split()
            if parts:
                return parts[0]
        return self.email.split('@')[0]

    def __str__(self):
        return f'{self.full_name} ({self.user_type})'


class CitizenProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='citizen_profile')
    default_address = models.ForeignKey('Address', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    rating_avg = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_services_requested = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Perfil Cidadão'
        verbose_name_plural = 'Perfis Cidadão'

    def __str__(self):
        return f'Cidadão: {self.user.full_name}'


class MEIProfile(models.Model):

    class VerificationStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pendente'
        VERIFIED = 'VERIFIED', 'Verificado'
        REJECTED = 'REJECTED', 'Rejeitado'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='mei_profile')
    cnpj = models.CharField(max_length=18, unique=True)
    razao_social = models.CharField(max_length=255)
    nome_fantasia = models.CharField(max_length=255)
    verification_status = models.CharField(max_length=20, choices=VerificationStatus.choices, default=VerificationStatus.PENDING)
    bio = models.TextField(blank=True)
    service_radius_km = models.DecimalField(max_digits=5, decimal_places=2, default=10)
    city = models.CharField(max_length=100, default='Florianópolis')
    rating_avg = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_services_completed = models.IntegerField(default=0)
    is_available = models.BooleanField(default=True)
    cnpj_file = models.FileField(upload_to='cnpj_files/', blank=True, null=True)
    whatsapp_link = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = 'Perfil MEI'
        verbose_name_plural = 'Perfis MEI'

    def __str__(self):
        return f'MEI: {self.user.full_name} — {self.nome_fantasia}'


class Address(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    label = models.CharField(max_length=100)
    cep = models.CharField(max_length=9)
    street = models.CharField(max_length=255)
    number = models.CharField(max_length=20)
    complement = models.CharField(max_length=100, blank=True, null=True)
    neighborhood = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Endereço'
        verbose_name_plural = 'Endereços'

    def __str__(self):
        return f'{self.label} — {self.street}, {self.number}, {self.city}'
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('O email é obrigatório')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    TIPO_CHOICES = [
        ('cliente', 'Cliente'),
        ('profissional', 'Profissional'),
    ]

    email = models.EmailField(unique=True)
    nome_completo = models.CharField(max_length=255)
    telefone = models.CharField(max_length=20, blank=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nome_completo']

    def __str__(self):
        return f"{self.nome_completo} ({self.tipo})"


class PerfilProfissional(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil_profissional')
    especialidade = models.CharField(max_length=100)
    bairro = models.CharField(max_length=100)
    cidade = models.CharField(max_length=100, default='Florianópolis')
    preco_base = models.DecimalField(max_digits=8, decimal_places=2)
    disponivel = models.BooleanField(default=True)
    verificado = models.BooleanField(default=False)
    bio = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.nome_completo} - {self.especialidade}"
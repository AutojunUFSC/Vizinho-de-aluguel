import uuid
from django.db import models


class ServiceCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Categoria de Serviço'
        verbose_name_plural = 'Categorias de Serviço'
        ordering = ['order']

    def __str__(self):
        return self.name


class ServiceRequest(models.Model):

    class Urgency(models.TextChoices):
        BAIXA = 'BAIXA', 'Baixa'
        MEDIA = 'MEDIA', 'Média'
        ALTA = 'ALTA', 'Alta'
        EMERGENCIA = 'EMERGENCIA', 'Emergência'

    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Aberto'
        IN_AUCTION = 'IN_AUCTION', 'Em Leilão'
        AWARDED = 'AWARDED', 'Adjudicado'
        IN_PROGRESS = 'IN_PROGRESS', 'Em Andamento'
        COMPLETED = 'COMPLETED', 'Concluído'
        CANCELLED = 'CANCELLED', 'Cancelado'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    citizen = models.ForeignKey('accounts.CitizenProfile', on_delete=models.CASCADE, related_name='service_requests')
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.ForeignKey(ServiceCategory, on_delete=models.SET_NULL, null=True, related_name='service_requests')
    address = models.ForeignKey('accounts.Address', on_delete=models.SET_NULL, null=True, related_name='service_requests')
    urgency = models.CharField(max_length=20, choices=Urgency.choices, default=Urgency.MEDIA)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    budget_max = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    auction_end_at = models.DateTimeField(blank=True, null=True)
    desired_deadline = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    awarded_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = 'Solicitação de Serviço'
        verbose_name_plural = 'Solicitações de Serviço'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} — {self.citizen.user.full_name}'


class ServiceRequestMedia(models.Model):

    class MediaType(models.TextChoices):
        IMAGE = 'IMAGE', 'Imagem'
        VIDEO = 'VIDEO', 'Vídeo'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name='media')
    file = models.FileField(upload_to='service_requests/')
    media_type = models.CharField(max_length=10, choices=MediaType.choices)
    order = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Mídia da Solicitação'
        verbose_name_plural = 'Mídias das Solicitações'
        ordering = ['order']

    def __str__(self):
        return f'{self.media_type} — {self.service_request.title}'
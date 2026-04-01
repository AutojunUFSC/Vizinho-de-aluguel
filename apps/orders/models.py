import uuid
from django.db import models

class ServiceOrder(models.Model):
    class Status(models.TextChoices):
        PENDING_START = 'PENDING_START', 'Aguardando Início'
        IN_PROGRESS = 'IN_PROGRESS', 'Em Andamento'
        COMPLETED = 'COMPLETED', 'Concluído'
        CANCELLED = 'CANCELLED', 'Cancelado'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_request = models.ForeignKey('services.ServiceRequest', on_delete=models.CASCADE, related_name='orders')
    winning_bid = models.ForeignKey('auctions.Bid', on_delete=models.CASCADE, related_name='won_orders')
    
    citizen = models.ForeignKey('accounts.CitizenProfile', on_delete=models.CASCADE, related_name='service_orders')
    mei_profile = models.ForeignKey('accounts.MEIProfile', on_delete=models.CASCADE, related_name='service_orders')
    
    agreed_amount = models.DecimalField(max_digits=10, decimal_places=2)
    agreed_deadline = models.DateField()
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_START)
    
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    citizen_confirmed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Ordem {self.id} - {self.status}"
import uuid
from django.db import models


class MEICategorySubscription(models.Model):
    mei_profile = models.ForeignKey('accounts.MEIProfile', on_delete=models.CASCADE, related_name='category_subscriptions')
    category = models.ForeignKey('services.ServiceCategory', on_delete=models.CASCADE, related_name='mei_subscriptions')
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['mei_profile', 'category']

    def __str__(self):
        return f"{self.mei_profile.user.full_name} inscrito em {self.category.name}"


class Bid(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Ativo'
        WITHDRAWN = 'WITHDRAWN', 'Retirado'
        WINNER = 'WINNER', 'Vencedor'
        REJECTED = 'REJECTED', 'Rejeitado'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_request = models.ForeignKey('services.ServiceRequest', on_delete=models.CASCADE, related_name='bids')
    mei_profile = models.ForeignKey('accounts.MEIProfile', on_delete=models.CASCADE, related_name='bids')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    estimated_hours = models.DecimalField(max_digits=5, decimal_places=2)
    proposed_deadline = models.DateField()
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Lance de R$ {self.amount} por {self.mei_profile.user.full_name}"
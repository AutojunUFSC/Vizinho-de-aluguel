import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Review(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_order = models.ForeignKey('orders.ServiceOrder', on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='reviews_given')
    reviewed_user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='reviews_received')
    
    # Valida para aceitar apenas notas de 1 a 5
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Garante que uma pessoa não avalie o mesmo contrato duas vezes
        unique_together = ['service_order', 'reviewer']

    def __str__(self):
        return f"Nota {self.rating} de {self.reviewer.full_name} para {self.reviewed_user.full_name}"
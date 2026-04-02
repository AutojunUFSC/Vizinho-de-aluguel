import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Review(models.Model):
    class ReviewType(models.TextChoices):
        CITIZEN_TO_MEI = 'CITIZEN_TO_MEI', 'Cidadão avalia MEI'
        MEI_TO_CITIZEN = 'MEI_TO_CITIZEN', 'MEI avalia Cidadão'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_order = models.ForeignKey(
        'orders.ServiceOrder',
        on_delete=models.CASCADE,
        related_name='reviews',
    )
    reviewer = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='reviews_given',
    )
    review_type = models.CharField(max_length=20, choices=ReviewType.choices)
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Avaliação'
        verbose_name_plural = 'Avaliações'
        unique_together = ('service_order', 'reviewer')

    def __str__(self):
        return f'Avaliação {self.rating}★ - Ordem {self.service_order_id}'

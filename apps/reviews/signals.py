from django.db.models import Avg
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Review


@receiver(post_save, sender=Review)
def update_rating_avg(sender, instance, **kwargs):
    order = instance.service_order

    if instance.review_type == Review.ReviewType.CITIZEN_TO_MEI:
        mei = order.mei_profile
        avg = Review.objects.filter(
            service_order__mei_profile=mei,
            review_type=Review.ReviewType.CITIZEN_TO_MEI,
        ).aggregate(avg=Avg('rating'))['avg'] or 0
        mei.rating_avg = round(avg, 2)
        mei.save(update_fields=['rating_avg'])

    elif instance.review_type == Review.ReviewType.MEI_TO_CITIZEN:
        citizen = order.citizen
        avg = Review.objects.filter(
            service_order__citizen=citizen,
            review_type=Review.ReviewType.MEI_TO_CITIZEN,
        ).aggregate(avg=Avg('rating'))['avg'] or 0
        citizen.rating_avg = round(avg, 2)
        citizen.save(update_fields=['rating_avg'])

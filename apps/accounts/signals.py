from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, CitizenProfile, MEIProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.user_type == User.UserType.CIDADAO:
            CitizenProfile.objects.create(user=instance)
        elif instance.user_type == User.UserType.MEI:
            MEIProfile.objects.create(user=instance)
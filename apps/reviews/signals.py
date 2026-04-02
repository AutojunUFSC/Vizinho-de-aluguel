from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Avg
from .models import Review

@receiver(post_save, sender=Review)
def update_user_rating(sender, instance, created, **kwargs):
    if created:
        reviewed_user = instance.reviewed_user
        
        # Calcula a média matemática de todas as notas desse usuário
        nova_media = Review.objects.filter(reviewed_user=reviewed_user).aggregate(Avg('rating'))['rating__avg']
        
        # Atualiza o perfil correto (Cidadão ou MEI)
        if hasattr(reviewed_user, 'mei_profile'):
            reviewed_user.mei_profile.rating_avg = round(nova_media, 2)
            reviewed_user.mei_profile.save()
        elif hasattr(reviewed_user, 'citizen_profile'):
            reviewed_user.citizen_profile.rating_avg = round(nova_media, 2)
            reviewed_user.citizen_profile.save()
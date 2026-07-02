from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import UserProfile

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    """
    Signal to automatically create a UserProfile when a User is created.
    Uses get_or_create to avoid duplicate errors.
    """
    if created:
        UserProfile.objects.get_or_create(
            user=instance,
            defaults={'role': 'EMPLOYEE'}
        )


@receiver(post_save, sender=User)
def ensure_profile_exists(sender, instance, **kwargs):
    """
    Signal to ensure UserProfile exists for every User (handles edge cases).
    """
    try:
        instance.userprofile
    except UserProfile.DoesNotExist:
        UserProfile.objects.get_or_create(
            user=instance,
            defaults={'role': 'EMPLOYEE'}
        )
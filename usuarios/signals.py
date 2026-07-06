from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from usuarios.models import Perfil


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def crear_perfil(sender, instance, created, **kwargs):
    if created and not instance.is_superuser:
        Perfil.objects.get_or_create(usuario=instance)
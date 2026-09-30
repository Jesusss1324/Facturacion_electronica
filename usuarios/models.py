from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    class Rol(models.TextChoices):
        EMISOR = 'emisor', 'Emisor'
        RECEPTOR = 'receptor', 'Receptor'
        ADMIN = 'admin', 'Administrador'

    rol = models.CharField(max_length=10, choices=Rol.choices, default=Rol.EMISOR)

    def __str__(self):
        return f"{self.username} ({self.get_rol_display()})"
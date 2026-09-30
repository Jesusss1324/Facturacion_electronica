from django.db import models
from django.conf import settings


class Emisor(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='emisor')
    rnc = models.CharField(max_length=11, unique=True)
    razon_social = models.CharField(max_length=200)
    direccion = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.razon_social} ({self.rnc})"


class Certificado(models.Model):
    emisor = models.ForeignKey(Emisor, on_delete=models.CASCADE, related_name='certificados')
    ruta_archivo = models.CharField(max_length=255)
    fecha_expiracion = models.DateField()
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"Certificado de {self.emisor.razon_social} (vence {self.fecha_expiracion})"
from django.db import models
from comprobantes.models import Comprobante


class ColaContingencia(models.Model):
    comprobante = models.OneToOneField(Comprobante, on_delete=models.CASCADE, related_name='cola')
    intentos = models.PositiveIntegerField(default=0)
    proximo_intento = models.DateTimeField()

    def __str__(self):
        return f"Reintento #{self.intentos} para {self.comprobante}"


class LogTransaccion(models.Model):
    comprobante = models.ForeignKey(Comprobante, on_delete=models.CASCADE, related_name='logs')
    evento = models.CharField(max_length=50)
    detalle = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.evento} - {self.comprobante} ({self.timestamp:%Y-%m-%d %H:%M})"
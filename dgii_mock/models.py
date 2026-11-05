from django.db import models
from comprobantes.models import Comprobante
from uuid import uuid4


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


class AdministradorEntidad(models.Model):
    clave = models.CharField(max_length=20, primary_key=True, default='principal')
    usuario = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=256)


class ContribuyenteLocal(models.Model):
    identificacion = models.CharField(max_length=11, unique=True)
    nombre = models.CharField(max_length=150)
    activo = models.BooleanField(default=True)
    emisor = models.BooleanField(default=False)
    receptor_credito = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.identificacion} · {self.nombre}'


class RangoLocal(models.Model):
    emisor = models.ForeignKey(ContribuyenteLocal, on_delete=models.PROTECT)
    tipo = models.CharField(max_length=2, choices=[('31', 'E31'), ('32', 'E32')])
    desde = models.PositiveBigIntegerField()
    hasta = models.PositiveBigIntegerField()
    vencimiento = models.DateField()
    activo = models.BooleanField(default=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(desde__gte=1) & models.Q(hasta__gte=models.F('desde')),
                                               name='rango_local_valido')]


class ConfiguracionEntidad(models.Model):
    clave = models.CharField(max_length=20, primary_key=True, default='principal')
    automatico = models.BooleanField(default=True)
    escenario = models.CharField(max_length=30, default='normal', choices=[
        ('normal', 'Normal'), ('indisponible', 'Servicio no disponible'),
        ('respuesta_perdida', 'Recepción guardada, respuesta perdida'), ('demora', 'Procesamiento demorado')])
    demora_segundos = models.PositiveIntegerField(default=10)
    rnc_autorizado = models.CharField(max_length=11)
    semilla_cargada = models.BooleanField(default=False)


class RecepcionLocal(models.Model):
    track_id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    emisor = models.CharField(max_length=11)
    encf = models.CharField(max_length=13)
    tipo = models.CharField(max_length=2)
    xml = models.TextField()
    sha256 = models.CharField(max_length=64)
    estado = models.CharField(max_length=30, default='recibido', db_index=True)
    recibida = models.DateTimeField(auto_now_add=True)
    procesar_desde = models.DateTimeField()
    procesada = models.DateTimeField(null=True)
    comprobaciones = models.JSONField(default=list)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['emisor', 'encf'], name='recepcion_local_unica')]
        ordering = ['-recibida']


class AuditoriaEntidad(models.Model):
    fecha = models.DateTimeField(auto_now_add=True)
    actor = models.CharField(max_length=150)
    accion = models.CharField(max_length=100)
    detalle = models.TextField(blank=True)
    recepcion = models.ForeignKey(RecepcionLocal, null=True, on_delete=models.PROTECT)

    class Meta:
        ordering = ['-fecha', '-id']


class IntentoAccesoEntidad(models.Model):
    ip = models.CharField(max_length=45, db_index=True)
    fecha = models.DateTimeField(auto_now_add=True)

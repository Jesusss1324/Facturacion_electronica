"""Persistencia de las entidades utilizadas por la interfaz actual.

Los conceptos y totales se guardan como instantáneas ordenadas JSON: sus
decimales se serializan como texto para no introducir errores de punto flotante.
Los modelos fiscales iniciales de comprobantes se conservan para la siguiente
etapa de integración; no se mezclan con los estados de demostración.
"""
from django.db import models
from uuid import uuid4


class ClienteRegistro(models.Model):
    nombre = models.CharField(max_length=200)
    identificacion = models.CharField(max_length=11, unique=True)
    tipo_identificacion = models.CharField(max_length=10)
    telefono = models.CharField(max_length=30, blank=True)
    direccion = models.CharField(max_length=500, blank=True)
    email = models.EmailField(blank=True)
    activo = models.BooleanField(default=True, db_index=True)
    fecha_registro = models.DateTimeField(null=True)
    fecha_modificacion = models.DateTimeField(null=True)


class BorradorRegistro(models.Model):
    id = models.UUIDField(primary_key=True)
    tipo_ecf = models.CharField(max_length=2)
    cliente = models.ForeignKey(ClienteRegistro, null=True, on_delete=models.PROTECT)
    fecha_creacion = models.DateTimeField(null=True)
    fecha_emision = models.DateField(null=True)
    tipo_ingreso = models.CharField(max_length=2, default='01')
    tipo_pago = models.CharField(max_length=10, default='contado')
    termino_pago = models.CharField(max_length=30, blank=True, default='30_dias')
    fecha_vencimiento = models.DateField(null=True)
    forma_pago = models.CharField(max_length=2, default='02')
    lineas = models.JSONField(default=list)
    revision_lineas = models.PositiveIntegerField(default=0)
    totales_guardados = models.JSONField(null=True)
    huella_totales = models.CharField(max_length=64, blank=True)
    fecha_guardado = models.DateTimeField(null=True)


class FacturaRegistro(models.Model):
    e_ncf = models.CharField(max_length=19, unique=True)
    tipo_ecf = models.CharField(max_length=2, db_index=True)
    cliente = models.ForeignKey(ClienteRegistro, on_delete=models.PROTECT)
    # NULL para el historial de ejemplo anterior a los borradores.
    borrador = models.OneToOneField(BorradorRegistro, null=True, on_delete=models.PROTECT)
    fecha_emision = models.DateTimeField(db_index=True)
    monto_total = models.DecimalField(max_digits=18, decimal_places=2)
    estado = models.CharField(max_length=15, db_index=True)
    track_id = models.CharField(max_length=100, blank=True)
    total_conceptos = models.PositiveIntegerField(default=1)
    huella_seguridad = models.CharField(max_length=200, blank=True)
    lineas = models.JSONField(default=list)
    tipo_ingreso = models.CharField(max_length=2, default='01')
    tipo_pago = models.CharField(max_length=10, default='contado')
    forma_pago = models.CharField(max_length=2, default='02')
    fecha_vencimiento = models.DateField(null=True)
    vencimiento_secuencia = models.CharField(max_length=20, default='31/12/2026')
    causal_anulacion = models.TextField(blank=True)
    acta_anulacion = models.CharField(max_length=100, blank=True)
    fecha_anulacion = models.CharField(max_length=50, blank=True)


class EventoRegistro(models.Model):
    timestamp = models.DateTimeField(db_index=True)
    usuario = models.CharField(max_length=150)
    tipo_usuario = models.CharField(max_length=100)
    modulo = models.CharField(max_length=30, db_index=True)
    modulo_display = models.CharField(max_length=100)
    titulo = models.CharField(max_length=250)
    descripcion = models.TextField()
    referencia_tipo = models.CharField(max_length=30)
    referencia_id = models.PositiveBigIntegerField(null=True)
    referencia_codigo = models.CharField(max_length=100)
    resultado = models.CharField(max_length=30, db_index=True)
    resultado_display = models.CharField(max_length=100)
    codigo_error = models.CharField(max_length=100, blank=True)
    ip = models.CharField(max_length=45)
    hash_seguridad = models.CharField(max_length=200, blank=True)
    detalles_tecnicos = models.JSONField(default=dict)


class CargaInicial(models.Model):
    clave = models.CharField(max_length=50, primary_key=True)
    fecha = models.DateTimeField(auto_now_add=True)


class ConfiguracionEmisor(models.Model):
    clave = models.CharField(max_length=30, primary_key=True)
    datos = models.JSONField(default=dict)


class SecuenciaLocal(models.Model):
    """Contador local; no representa un rango autorizado por la DGII."""
    tipo_ecf = models.CharField(max_length=2, primary_key=True)
    siguiente = models.PositiveBigIntegerField()
    limite = models.PositiveBigIntegerField(default=9999999999)
    activa = models.BooleanField(default=True)
    vencimiento = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(siguiente__gte=1), name='secuencia_positiva')]


class OperacionEmision(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente de preparación'
        PROCESANDO = 'procesando', 'Preparando documento'
        PREPARADA = 'preparada', 'Pendiente de integración'
        CONSULTAR = 'consultar', 'Resultado incierto: consultar recepción'

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    borrador = models.OneToOneField(BorradorRegistro, on_delete=models.PROTECT)
    factura = models.OneToOneField(FacturaRegistro, on_delete=models.PROTECT)
    secuencia = models.ForeignKey(SecuenciaLocal, on_delete=models.PROTECT)
    numero = models.PositiveBigIntegerField()
    e_ncf = models.CharField(max_length=19, unique=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True)
    creada = models.DateTimeField(auto_now_add=True)
    actualizada = models.DateTimeField(auto_now=True)
    instantanea = models.JSONField()
    xml = models.TextField(blank=True)
    xml_sha256 = models.CharField(max_length=64, blank=True)
    intentos = models.PositiveIntegerField(default=0)
    proximo_intento = models.DateTimeField(null=True, blank=True, db_index=True)
    bloqueo_token = models.UUIDField(null=True, editable=False)
    bloqueo_hasta = models.DateTimeField(null=True, blank=True)
    envio_iniciado = models.DateTimeField(null=True, blank=True)
    ultimo_error = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['secuencia', 'numero'], name='reserva_unica_por_tipo')]


class EventoOperacion(models.Model):
    operacion = models.ForeignKey(OperacionEmision, on_delete=models.PROTECT, related_name='eventos')
    fecha = models.DateTimeField(auto_now_add=True)
    evento = models.CharField(max_length=50)
    detalle = models.TextField(blank=True)

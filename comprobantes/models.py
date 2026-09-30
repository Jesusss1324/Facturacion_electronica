from decimal import Decimal
from django.db import models
from emisores.models import Emisor

TASA_ITBIS = Decimal('0.18')


class Receptor(models.Model):
    rnc_cedula = models.CharField(max_length=11)
    nombre = models.CharField(max_length=200)
    email = models.EmailField(blank=True)

    def __str__(self):
        return f"{self.nombre} ({self.rnc_cedula})"


class Comprobante(models.Model):
    class TipoECF(models.TextChoices):
        E31 = '31', 'Factura de Crédito Fiscal'
        E32 = '32', 'Factura de Consumo'
        E34 = '34', 'Nota de Crédito'
        E33 = '33', 'Nota de Débito'
        # agrega el resto de tipos (E41, E43, E44, E45, E46, E47) según los necesites

    class Estado(models.TextChoices):
        GENERADO = 'generado', 'Generado'
        FIRMADO = 'firmado', 'Firmado'
        ENVIADO = 'enviado', 'Enviado'
        ACEPTADO = 'aceptado', 'Aceptado'
        RECHAZADO = 'rechazado', 'Rechazado'
        EN_COLA = 'en_cola', 'En cola de contingencia'

    emisor = models.ForeignKey(Emisor, on_delete=models.PROTECT, related_name='comprobantes')
    receptor = models.ForeignKey(Receptor, on_delete=models.PROTECT, related_name='comprobantes')
    tipo_ecf = models.CharField(max_length=2, choices=TipoECF.choices)
    e_ncf = models.CharField(max_length=19, blank=True, null=True, unique=True)
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.GENERADO)
    fecha_emision = models.DateTimeField(auto_now_add=True)
    monto_gravado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    monto_exento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    itbis = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    monto_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    xml_content = models.TextField(blank=True)
    pdf_path = models.CharField(max_length=255, blank=True)
    motivo_rechazo = models.CharField(max_length=255, blank=True)

    def calcular_totales(self):
        """Recalcula montos a partir de los ítems asociados y guarda el resultado."""
        items = self.items.all()
        gravado = sum((item.monto_item for item in items), Decimal('0'))
        itbis = (gravado * TASA_ITBIS).quantize(Decimal('0.01'))
        total = gravado + itbis + self.monto_exento

        self.monto_gravado = gravado
        self.itbis = itbis
        self.monto_total = total
        self.save(update_fields=['monto_gravado', 'itbis', 'monto_total'])

    def __str__(self):
        return f"{self.get_tipo_ecf_display()} - {self.e_ncf or 'sin e-NCF'}"


class ItemComprobante(models.Model):
    comprobante = models.ForeignKey(Comprobante, on_delete=models.CASCADE, related_name='items')
    numero_linea = models.PositiveIntegerField()
    nombre_item = models.CharField(max_length=200)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    monto_item = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.nombre_item} x{self.cantidad}"
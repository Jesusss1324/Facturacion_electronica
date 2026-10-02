from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Tuple
from uuid import UUID


@dataclass(frozen=True)
class Cliente:
    id: int
    nombre: str
    identificacion: str
    tipo_identificacion: str
    telefono: str
    direccion: str
    email: str
    activo: bool = True
    fecha_registro: datetime | None = None
    fecha_modificacion: datetime | None = None

    @property
    def identificacion_display(self):
        value = self.identificacion
        if self.tipo_identificacion == 'RNC':
            return f'{value[:1]}-{value[1:3]}-{value[3:8]}-{value[8:]}'
        return f'{value[:3]}-{value[3:10]}-{value[10:]}'

    @property
    def categoria_display(self):
        if not self.activo:
            return 'SUSPENDIDO DGII'
        if self.tipo_identificacion in {'CEDULA', 'Cédula'}:
            return 'Persona Física con Actividad Lucrativa'
        categorias = [
            'Grandes Contribuyentes Nacionales',
            'Comercio al por mayor de insumos',
            'Servicios Corporativos y Consultoría',
            'Distribuidora y Logística Industrial',
            'Venta al por menor de medicamentos',
            'Servicios Profesionales Especializados',
        ]
        return categorias[(self.id - 1) % len(categorias)]


@dataclass(frozen=True)
class Factura:
    id: int
    e_ncf: str
    tipo_ecf: str
    cliente_id: int
    fecha_emision: datetime
    monto_total: Decimal
    estado: str
    track_id: str = ''
    total_conceptos: int = 1
    huella_seguridad: str = ''
    lineas: tuple = ()
    tipo_ingreso: str = '01'
    tipo_pago: str = 'contado'
    forma_pago: str = '02'
    fecha_vencimiento: date | str | None = None
    vencimiento_secuencia: str = '31/12/2026'
    causal_anulacion: str = ''
    acta_anulacion: str = ''
    fecha_anulacion: str = ''

    @property
    def tipo_display(self):
        return 'Crédito fiscal' if self.tipo_ecf == '31' else 'Consumo'

    @property
    def estado_display(self):
        return {'aprobado': 'Aprobado', 'rechazado': 'Rechazado', 'anulado': 'Anulado'}.get(self.estado, 'En proceso')

    @property
    def track_id_display(self):
        if self.track_id:
            return self.track_id
        return f'DGII-REC-{89240000 + self.id}'

    @property
    def condicion_pago_display(self):
        forma = {
            '01': 'Efectivo',
            '02': 'Transferencia',
            '03': 'Tarjeta',
            '04': 'Crédito',
            '07': 'Mixto',
            '08': 'Permuta',
        }.get(self.forma_pago, 'Transferencia')
        tipo = {'contado': 'Contado', 'credito': 'Crédito', 'gratuito': 'Gratuito'}.get(self.tipo_pago, 'Contado')
        return f'{tipo} ({forma})'


@dataclass(frozen=True)
class ResumenFactura:
    factura: Factura
    cliente: Cliente


@dataclass(frozen=True)
class ResumenInicio:
    emitidas: int
    aprobadas: int
    rechazadas: int
    clientes_activos: int


def importe(value):
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class LineaFactura:
    id: UUID
    tipo: str
    concepto: str
    descripcion: str
    unidad: str
    cantidad: Decimal
    precio: Decimal
    descuento: Decimal

    @property
    def bruto(self):
        return importe(self.cantidad * self.precio)

    @property
    def base(self):
        return self.bruto - self.descuento

    @property
    def itbis(self):
        return importe(self.base * Decimal('0.18'))

    @property
    def total(self):
        return self.base + self.itbis

    @property
    def tipo_display(self):
        return 'Servicio' if self.tipo == 'servicio' else 'Bien'


@dataclass(frozen=True)
class BorradorFactura:
    id: UUID
    tipo_ecf: str  # '31' (Crédito Fiscal) o '32' (Consumo)
    cliente_id: int | None = None
    fecha_creacion: datetime | None = None
    fecha_emision: date | str | None = None
    tipo_ingreso: str = '01'
    tipo_pago: str = 'contado'  # 'contado', 'credito', 'gratuito'
    termino_pago: str = '30_dias'
    fecha_vencimiento: date | str | None = None
    forma_pago: str = '02'  # '01', '02', '03', '04', '07', '08'
    lineas: tuple[LineaFactura, ...] = ()
    revision_lineas: int = 0
    totales_guardados: tuple | None = None
    huella_totales: str = ''
    fecha_guardado: datetime | None = None

    @property
    def tipo_display(self):
        return 'Crédito fiscal' if self.tipo_ecf == '31' else 'Consumo'

    @property
    def codigo_tipo(self):
        return f'E{self.tipo_ecf}'

    @property
    def secuencia_encf_display(self):
        return f'E{self.tipo_ecf}0000000001 (Automático)'

    @property
    def tipo_ingreso_display(self):
        mapa = {
            '01': '01 — Ingresos por operaciones (No financieros)',
            '02': '02 — Ingresos financieros',
            '03': '03 — Ingresos extraordinarios',
            '04': '04 — Ingresos por arrendamientos',
            '05': '05 — Ingresos por venta de activos depreciables',
            '06': '06 — Otros ingresos',
        }
        return mapa.get(self.tipo_ingreso, f'{self.tipo_ingreso} — Otro ingreso')

    @property
    def tipo_pago_display(self):
        mapa = {'contado': 'Contado', 'credito': 'Crédito', 'gratuito': 'Gratuito'}
        return mapa.get(self.tipo_pago, 'Contado')

    @property
    def forma_pago_display(self):
        mapa = {
            '01': '01 — Efectivo',
            '02': '02 — Cheque / Transferencia / Depósito',
            '03': '03 — Tarjeta de Crédito / Débito',
            '04': '04 — Compra a Crédito',
            '07': '07 — Mixto',
            '08': '08 — Permuta / Otros',
        }
        return mapa.get(self.forma_pago, f'{self.forma_pago} — Otra forma')


@dataclass(frozen=True)
class EventoLog:
    id: int
    timestamp: datetime
    usuario: str
    tipo_usuario: str
    modulo: str  # 'dgii', 'firma', 'xml', 'facturacion', 'clientes', 'auth', 'pdf'
    modulo_display: str
    titulo: str
    descripcion: str
    referencia_tipo: str  # 'factura', 'cliente', 'sesion', 'sistema'
    referencia_id: int | None
    referencia_codigo: str
    resultado: str  # 'correcto', 'informativo', 'advertencia', 'error'
    resultado_display: str
    codigo_error: str = ''
    ip: str = '192.168.1.45'
    hash_seguridad: str = ''
    detalles_tecnicos: dict = field(default_factory=dict)

    @property
    def timestamp_display(self):
        return self.timestamp.strftime('%d/%m/%Y %H:%M:%S.%f')[:-3]

    @property
    def fecha_display(self):
        return self.timestamp.strftime('%d/%m/%Y')

    @property
    def hora_display(self):
        return self.timestamp.strftime('%H:%M:%S.%f')[:-3]

    @property
    def es_correcto(self):
        return self.resultado == 'correcto'

    @property
    def es_informativo(self):
        return self.resultado == 'informativo'

    @property
    def es_advertencia(self):
        return self.resultado == 'advertencia'

    @property
    def es_error(self):
        return self.resultado == 'error'

    @property
    def badge_css(self):
        return {
            'correcto': 'badge-success',
            'informativo': 'badge-info',
            'advertencia': 'badge-warning',
            'error': 'badge-danger',
        }.get(self.resultado, 'badge-neutral')

    @property
    def es_sistema(self):
        return self.usuario.lower() == 'sistema'


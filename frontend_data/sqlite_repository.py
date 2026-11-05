"""Repositorio ORM sin cachés de registros entre solicitudes.

La transacción IMMEDIATE de SQLite serializa las escrituras antes de leer el
estado vigente. Las reglas de borrador se comparten con el repositorio unitario;
únicamente el agregado modificado se vuelve a guardar.
"""
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.utils import timezone

from .entities import BorradorFactura, Cliente, EventoLog, Factura, ResumenFactura, ResumenInicio
from .models import BorradorRegistro, ClienteRegistro, EventoRegistro, FacturaRegistro
from .repository import FrontendRepository
from .serialization import entidad, registro


class SQLiteRepository(FrontendRepository):
    def __init__(self):
        # Ningún registro queda almacenado en memoria entre llamadas.
        pass

    @staticmethod
    def _get(model, cls, pk):
        try:
            return entidad(model.objects.get(pk=pk), cls)
        except (model.DoesNotExist, ValueError) as error:
            raise KeyError(pk) from error

    def get_cliente(self, cliente_id):
        return self._get(ClienteRegistro, Cliente, cliente_id)

    def list_clientes(self):
        return tuple(entidad(row, Cliente) for row in ClienteRegistro.objects.order_by('id'))

    def find_cliente_by_identificacion(self, identificacion):
        row = ClienteRegistro.objects.filter(identificacion=identificacion).first()
        return entidad(row, Cliente) if row else None

    def create_cliente(self, **datos):
        try:
            with transaction.atomic():
                datos.setdefault('fecha_registro', timezone.now())
                return entidad(ClienteRegistro.objects.create(**datos), Cliente)
        except IntegrityError as error:
            raise ValueError('La identificación ya está registrada.') from error

    def update_cliente(self, cliente_id, **datos):
        from dataclasses import replace
        try:
            with transaction.atomic():
                actual = self.get_cliente(cliente_id)
                datos.setdefault('fecha_modificacion', timezone.now())
                updated = replace(actual, **datos)
                ClienteRegistro.objects.filter(pk=cliente_id).update(**registro(updated))
                return self.get_cliente(cliente_id)
        except IntegrityError as error:
            raise ValueError('La identificación ya está registrada.') from error

    def set_cliente_activo(self, cliente_id, activo):
        return self.update_cliente(cliente_id, activo=activo)

    def get_factura(self, factura_id):
        return self._get(FacturaRegistro, Factura, factura_id)

    def list_facturas(self):
        return tuple(entidad(row, Factura) for row in FacturaRegistro.objects.order_by('-fecha_emision', '-id'))

    def facturas_cliente(self, cliente_id):
        return tuple(entidad(row, Factura) for row in FacturaRegistro.objects.filter(
            cliente_id=cliente_id).order_by('-fecha_emision', '-id'))

    def recent_facturas_cliente(self, cliente_id, limit=3):
        if limit < 0:
            raise ValueError('El límite no puede ser negativo.')
        return tuple(entidad(row, Factura) for row in FacturaRegistro.objects.filter(
            cliente_id=cliente_id).order_by('-fecha_emision', '-id')[:limit])

    def tipos_ecf_cliente(self, cliente_id):
        return [f'E{tipo}' for tipo in FacturaRegistro.objects.filter(
            cliente_id=cliente_id).order_by('tipo_ecf').values_list('tipo_ecf', flat=True).distinct()]

    def recent_facturas(self, limit=5):
        if limit < 0:
            raise ValueError('El límite no puede ser negativo.')
        return tuple(ResumenFactura(entidad(row, Factura), entidad(row.cliente, Cliente))
                     for row in FacturaRegistro.objects.select_related('cliente').order_by(
                         '-fecha_emision', '-id')[:limit])

    def resumen_inicio(self):
        counts = FacturaRegistro.objects.aggregate(emitidas=Count('id'),
            aprobadas=Count('id', filter=Q(estado='aprobado')),
            rechazadas=Count('id', filter=Q(estado='rechazado')))
        return ResumenInicio(**counts, clientes_activos=ClienteRegistro.objects.filter(activo=True).count())

    def get_borrador(self, borrador_id):
        return self._get(BorradorRegistro, BorradorFactura, borrador_id)

    def create_borrador(self, tipo_ecf, cliente_id=None, borrador_id=None):
        from uuid import uuid4
        with transaction.atomic():
            if cliente_id is not None:
                self.get_cliente(cliente_id)
            row = BorradorRegistro.objects.create(id=borrador_id or uuid4(), tipo_ecf=tipo_ecf,
                cliente_id=cliente_id, fecha_creacion=timezone.now())
            return entidad(row, BorradorFactura)

    def factura_emitida_borrador(self, borrador_id):
        row = FacturaRegistro.objects.filter(borrador_id=borrador_id).first()
        return entidad(row, Factura) if row else None

    def _draft_action(self, action, borrador_id, *args, **kwargs):
        with transaction.atomic():
            borrador = self.get_borrador(borrador_id)
            emitida = self.factura_emitida_borrador(borrador_id)
            if emitida:
                raise ValueError('El borrador ya fue emitido y no se puede modificar.')
            cliente = self.get_cliente(borrador.cliente_id) if borrador.cliente_id else None
            # Las reglas monetarias y las huellas operan sobre las mismas entidades
            # que las pantallas; toda lectura/escritura queda en esta transacción.
            memory = FrontendRepository(clientes=(cliente,) if cliente else (),
                facturas=())
            memory._borradores[borrador.id] = borrador
            result = getattr(memory, action)(borrador.id, *args, **kwargs)
            BorradorRegistro.objects.filter(pk=borrador.id).update(**registro(result))
            return result

    def update_borrador(self, borrador_id, **datos):
        return self._draft_action('update_borrador', borrador_id, **datos)

    def guardar_linea(self, borrador_id, linea, revision, editar=False):
        return self._draft_action('guardar_linea', borrador_id, linea, revision, editar=editar)

    def quitar_linea(self, borrador_id, linea_id, revision):
        return self._draft_action('quitar_linea', borrador_id, linea_id, revision)

    def guardar_totales(self, borrador_id, huella, recalcular=False):
        return self._draft_action('guardar_totales', borrador_id, huella, recalcular=recalcular)

    def emitir_factura(self, borrador_id, huella=None):
        from .emission import reservar_emision
        return reservar_emision(self, borrador_id, huella)

    def get_operacion_factura(self, factura_id):
        from .models import OperacionEmision
        return OperacionEmision.objects.filter(factura_id=factura_id).first()

    def list_logs(self):
        return tuple(entidad(row, EventoLog) for row in EventoRegistro.objects.order_by('-timestamp', '-id'))

    def get_log(self, log_id):
        return self._get(EventoRegistro, EventoLog, log_id)

    def total_logs(self):
        return EventoRegistro.objects.count()

from datetime import datetime
from functools import lru_cache
from dataclasses import replace
from threading import RLock
from uuid import uuid4
from zoneinfo import ZoneInfo

from .entities import BorradorFactura, Cliente, EventoLog, ResumenFactura, ResumenInicio
from .fixtures import build_clientes, build_facturas, build_logs


class FrontendRepository:
    def __init__(self, clientes=(), facturas=(), logs=()):
        clientes = tuple(clientes)
        self._clientes = {cliente.id: cliente for cliente in clientes}
        self._facturas = {factura.id: factura for factura in facturas}
        self._logs = {log.id: log for log in logs}
        self._identificaciones = {cliente.identificacion: cliente.id for cliente in clientes}
        self._borradores = {}
        self._write_lock = RLock()
        self._facturas_por_cliente = {}
        for factura in self.list_facturas():
            self._facturas_por_cliente.setdefault(factura.cliente_id, []).append(factura)

    def recent_facturas_cliente(self, cliente_id, limit=3):
        if limit < 0:
            raise ValueError('El límite no puede ser negativo.')
        return tuple(self._facturas_por_cliente.get(cliente_id, ())[:limit])

    def tipos_ecf_cliente(self, cliente_id):
        facturas = self._facturas_por_cliente.get(cliente_id, ())
        return sorted({f'E{factura.tipo_ecf}' for factura in facturas})

    def facturas_cliente(self, cliente_id):
        return tuple(self._facturas_por_cliente.get(cliente_id, ()))

    def find_cliente_by_identificacion(self, identificacion):
        cliente_id = self._identificaciones.get(identificacion)
        return self._clientes.get(cliente_id)

    def update_cliente(self, cliente_id, **datos):
        with self._write_lock:
            actual = self.get_cliente(cliente_id)
            nueva_identificacion = datos.get('identificacion', actual.identificacion)
            existente = self.find_cliente_by_identificacion(nueva_identificacion)
            if existente and existente.id != cliente_id:
                raise ValueError('La identificación ya está registrada.')
            if actual.identificacion in self._identificaciones:
                del self._identificaciones[actual.identificacion]
            cliente = replace(actual, **datos)
            self._clientes[cliente_id] = cliente
            self._identificaciones[cliente.identificacion] = cliente_id
            return cliente

    def create_cliente(self, **datos):
        with self._write_lock:
            if self.find_cliente_by_identificacion(datos['identificacion']):
                raise ValueError('La identificación ya está registrada.')
            cliente = Cliente(id=max(self._clientes, default=0) + 1, **datos)
            self._clientes[cliente.id] = cliente
            self._identificaciones[cliente.identificacion] = cliente.id
            return cliente

    def list_clientes(self):
        return tuple(self._clientes.values())

    def get_cliente(self, cliente_id):
        return self._clientes[cliente_id]

    def set_cliente_activo(self, cliente_id, activo):
        """Actualiza sólo el registro en memoria; se reinicia al recargar el servidor."""
        cliente = replace(self.get_cliente(cliente_id), activo=activo)
        self._clientes[cliente_id] = cliente
        return cliente

    def create_borrador(self, tipo_ecf, cliente_id=None, borrador_id=None):
        with self._write_lock:
            bid = borrador_id or uuid4()
            borrador = BorradorFactura(
                id=bid,
                tipo_ecf=tipo_ecf,
                cliente_id=cliente_id,
                fecha_creacion=datetime.now(tz=ZoneInfo('America/Santo_Domingo')),
            )
            self._borradores[bid] = borrador
            return borrador

    def get_borrador(self, borrador_id):
        return self._borradores[borrador_id]

    def update_borrador(self, borrador_id, **datos):
        with self._write_lock:
            actual = self.get_borrador(borrador_id)
            actualizado = replace(actual, **datos)
            self._borradores[borrador_id] = actualizado
            return actualizado

    def guardar_linea(self, borrador_id, linea, revision, editar=False):
        with self._write_lock:
            actual = self.get_borrador(borrador_id)
            if revision != actual.revision_lineas:
                raise ValueError('El borrador cambió en otra pestaña. Recarga la página antes de guardar.')
            if editar:
                if not any(item.id == linea.id for item in actual.lineas):
                    raise KeyError(linea.id)
                lineas = tuple(linea if item.id == linea.id else item for item in actual.lineas)
            else:
                if len(actual.lineas) >= 100:
                    raise ValueError('Puedes registrar hasta 100 conceptos por factura.')
                lineas = (*actual.lineas, linea)
            return self.update_borrador(borrador_id, lineas=lineas, revision_lineas=revision + 1)

    def quitar_linea(self, borrador_id, linea_id, revision):
        with self._write_lock:
            actual = self.get_borrador(borrador_id)
            if revision != actual.revision_lineas:
                raise ValueError('El borrador cambió en otra pestaña. Recarga la página antes de continuar.')
            if not any(item.id == linea_id for item in actual.lineas):
                raise KeyError(linea_id)
            return self.update_borrador(borrador_id, lineas=tuple(item for item in actual.lineas if item.id != linea_id), revision_lineas=revision + 1)

    def guardar_totales(self, borrador_id, huella, recalcular=False):
        from comprobantes.totales import huella_borrador, revisar_borrador
        with self._write_lock:
            actual = self.get_borrador(borrador_id)
            cliente = self.get_cliente(actual.cliente_id)
            if not cliente.activo:
                raise ValueError('El cliente está inactivo. Selecciona un cliente activo antes de continuar.')
            if huella != huella_borrador(actual):
                raise ValueError('El borrador cambió en otra pestaña. Revisa los datos actualizados antes de continuar.')
            resumen, errores = revisar_borrador(actual)
            if errores:
                raise ValueError(' '.join(errores))
            if not recalcular and actual.totales_guardados is not None and (
                dict(actual.totales_guardados) != resumen or actual.huella_totales != huella
            ):
                raise ValueError('Recalcula y confirma los importes actualizados antes de continuar.')
            return self.update_borrador(borrador_id, totales_guardados=tuple(resumen.items()),
                                       huella_totales=huella, fecha_guardado=datetime.now(tz=ZoneInfo('America/Santo_Domingo')))

    def emitir_factura(self, borrador_id, huella=None):
        from .entities import Factura
        with self._write_lock:
            borrador = self.get_borrador(borrador_id)
            if huella and borrador.huella_totales != huella:
                raise ValueError('El borrador fue modificado antes de emitir.')
            if borrador.totales_guardados is None:
                raise ValueError('Debes calcular y confirmar los totales antes de emitir.')
            cliente = self.get_cliente(borrador.cliente_id)
            if not cliente.activo:
                raise ValueError('El cliente receptor está inactivo.')

            nuevo_id = max(self._facturas.keys(), default=0) + 1
            cuenta_tipo = sum(1 for f in self._facturas.values() if f.tipo_ecf == borrador.tipo_ecf) + 1
            e_ncf = f'E{borrador.tipo_ecf}{cuenta_tipo:010d}'
            resumen = dict(borrador.totales_guardados)

            factura = Factura(
                id=nuevo_id,
                e_ncf=e_ncf,
                tipo_ecf=borrador.tipo_ecf,
                cliente_id=cliente.id,
                fecha_emision=datetime.now(tz=ZoneInfo('America/Santo_Domingo')),
                monto_total=resumen['total'],
                estado='aprobado',
                track_id=f'DGII-REC-{89240000 + nuevo_id}',
                total_conceptos=max(1, len(borrador.lineas)),
                huella_seguridad=borrador.huella_totales or 'sec-sha256-verified',
                lineas=borrador.lineas,
                tipo_ingreso=borrador.tipo_ingreso,
                tipo_pago=borrador.tipo_pago,
                forma_pago=borrador.forma_pago,
                fecha_vencimiento=borrador.fecha_vencimiento,
            )
            self._facturas[nuevo_id] = factura
            self._facturas_por_cliente.setdefault(cliente.id, []).insert(0, factura)
            return factura

    def list_facturas(self):
        return tuple(sorted(self._facturas.values(), key=lambda item: (item.fecha_emision, item.id), reverse=True))

    def get_factura(self, factura_id):
        return self._facturas[factura_id]

    def recent_facturas(self, limit=5):
        if limit < 0:
            raise ValueError('El límite no puede ser negativo.')
        return tuple(
            ResumenFactura(factura=factura, cliente=self.get_cliente(factura.cliente_id))
            for factura in self.list_facturas()[:limit]
        )

    def resumen_inicio(self):
        facturas = tuple(self._facturas.values())
        return ResumenInicio(
            emitidas=len(facturas),
            aprobadas=sum(factura.estado == 'aprobado' for factura in facturas),
            rechazadas=sum(factura.estado == 'rechazado' for factura in facturas),
            clientes_activos=sum(cliente.activo for cliente in self._clientes.values()),
        )

    def list_logs(self):
        return tuple(sorted(self._logs.values(), key=lambda l: (l.timestamp, l.id), reverse=True))

    def get_log(self, log_id):
        return self._logs[log_id]

    def total_logs(self):
        return len(self._logs)

    def filter_logs(self, query='', modulo='', usuario='', resultado='', fecha_desde='', fecha_hasta=''):
        logs = self.list_logs()
        if query:
            q = query.lower().strip()
            logs = tuple(l for l in logs if (
                q in l.referencia_codigo.lower() or
                q in l.titulo.lower() or
                q in l.descripcion.lower() or
                q in l.usuario.lower() or
                q in l.codigo_error.lower() or
                q in l.hash_seguridad.lower() or
                (l.detalles_tecnicos.get('track_id') and q in l.detalles_tecnicos['track_id'].lower())
            ))
        if modulo and modulo.lower() != 'todos':
            m = modulo.lower().strip()
            logs = tuple(l for l in logs if l.modulo == m or m in l.modulo_display.lower())
        if usuario and usuario.lower() != 'todos':
            u = usuario.lower().strip()
            logs = tuple(l for l in logs if u in l.usuario.lower() or u in l.tipo_usuario.lower())
        if resultado and resultado.lower() != 'todos':
            r = resultado.lower().strip()
            logs = tuple(l for l in logs if l.resultado == r)
        if fecha_desde:
            try:
                if '/' in fecha_desde:
                    d, m, y = map(int, fecha_desde.split('/'))
                    dt_desde = datetime(y, m, d, 0, 0, 0, tzinfo=ZoneInfo('America/Santo_Domingo'))
                else:
                    parts = list(map(int, fecha_desde.split('-')))
                    dt_desde = datetime(parts[0], parts[1], parts[2], 0, 0, 0, tzinfo=ZoneInfo('America/Santo_Domingo'))
                logs = tuple(l for l in logs if l.timestamp >= dt_desde)
            except Exception:
                pass
        if fecha_hasta:
            try:
                if '/' in fecha_hasta:
                    d, m, y = map(int, fecha_hasta.split('/'))
                    dt_hasta = datetime(y, m, d, 23, 59, 59, 999999, tzinfo=ZoneInfo('America/Santo_Domingo'))
                else:
                    parts = list(map(int, fecha_hasta.split('-')))
                    dt_hasta = datetime(parts[0], parts[1], parts[2], 23, 59, 59, 999999, tzinfo=ZoneInfo('America/Santo_Domingo'))
                logs = tuple(l for l in logs if l.timestamp <= dt_hasta)
            except Exception:
                pass
        return logs


@lru_cache(maxsize=1)
def get_repository():
    clientes = build_clientes()
    facturas = build_facturas(clientes)
    logs = build_logs(clientes, facturas)
    return FrontendRepository(clientes=clientes, facturas=facturas, logs=logs)

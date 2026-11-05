"""Operaciones locales persistentes. No firma ni envía documentos todavía."""
import json
from datetime import datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4
from zoneinfo import ZoneInfo

from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .configuration import get_emisor_info
from .entities import Cliente, Factura
from .models import (EventoOperacion, EventoRegistro, FacturaRegistro,
                     OperacionEmision, SecuenciaLocal)
from .serialization import entidad, registro


def evento(op, nombre, detalle=''):
    EventoOperacion.objects.create(operacion=op, evento=nombre, detalle=detalle)
    EventoRegistro.objects.create(timestamp=timezone.now(), usuario='sistema', tipo_usuario='Sistema',
        modulo='facturacion', modulo_display='Facturación', titulo=nombre, descripcion=detalle,
        referencia_tipo='factura', referencia_id=op.factura_id, referencia_codigo=op.e_ncf,
        resultado='informativo', resultado_display='Informativo', ip='127.0.0.1',
        detalles_tecnicos={'operacion_id': str(op.id), 'estado': op.estado})


@transaction.atomic
def reservar_emision(repo, borrador_id, huella):
    from comprobantes.totales import huella_borrador, revisar_borrador
    if not borrador_id:
        raise ValueError('Selecciona un borrador válido.')
    existente = repo.factura_emitida_borrador(borrador_id)
    if existente is not None:
        return existente
    borrador = repo.get_borrador(borrador_id)
    if not huella or huella != borrador.huella_totales or huella != huella_borrador(borrador):
        raise ValueError('El borrador cambió. Confirma sus totales antes de emitir.')
    cliente = repo.get_cliente(borrador.cliente_id)
    if not cliente.activo:
        raise ValueError('El cliente receptor está inactivo.')
    resumen, errores = revisar_borrador(borrador)
    if errores or borrador.totales_guardados is None or dict(borrador.totales_guardados) != resumen:
        raise ValueError('Revisa y confirma los totales actualizados antes de emitir.')
    try:
        secuencia = SecuenciaLocal.objects.get(pk=borrador.tipo_ecf)
    except SecuenciaLocal.DoesNotExist as error:
        raise ValueError('No hay secuencia local configurada para este tipo.') from error
    hoy = timezone.localdate(timezone.now(), timezone=ZoneInfo('America/Santo_Domingo'))
    if not secuencia.activa or (secuencia.vencimiento and secuencia.vencimiento < hoy):
        raise ValueError('La secuencia está desactivada o vencida.')
    if secuencia.siguiente > secuencia.limite or secuencia.siguiente > 9999999999:
        raise ValueError('La secuencia está agotada.')
    numero = secuencia.siguiente
    encf = f'E{borrador.tipo_ecf}{numero:010d}'
    if FacturaRegistro.objects.filter(e_ncf=encf).exists():
        raise ValueError('La secuencia configurada colisiona con una factura existente; revisa su contador.')
    emisor = get_emisor_info()
    secuencia.siguiente += 1
    secuencia.save(update_fields=['siguiente'])
    factura = FacturaRegistro.objects.create(borrador_id=borrador.id, e_ncf=encf,
        tipo_ecf=borrador.tipo_ecf, cliente_id=cliente.id, fecha_emision=timezone.now(),
        monto_total=resumen['total'], estado='generado', track_id='', total_conceptos=len(borrador.lineas),
        huella_seguridad=huella, lineas=registro(borrador)['lineas'], tipo_ingreso=borrador.tipo_ingreso,
        tipo_pago=borrador.tipo_pago, forma_pago=borrador.forma_pago,
        fecha_vencimiento=borrador.fecha_vencimiento,
        vencimiento_secuencia=secuencia.vencimiento.strftime('%d/%m/%Y') if secuencia.vencimiento else '')
    snapshot = json.loads(json.dumps({'factura': registro(entidad(factura, Factura)),
        'cliente': registro(cliente), 'emisor': emisor, 'totales': resumen}, cls=DjangoJSONEncoder))
    op = OperacionEmision.objects.create(borrador_id=borrador.id, factura=factura,
        secuencia=secuencia, numero=numero, e_ncf=encf, instantanea=snapshot)
    evento(op, 'secuencia_reservada', 'Operación local creada; secuencia reservada de forma definitiva.')
    return entidad(factura, Factura)


@transaction.atomic
def recuperar_interrumpidas():
    """Sólo recupera bloqueos vencidos; nunca roba trabajo a un proceso vivo."""
    ahora = timezone.now()
    expiradas = Q(bloqueo_hasta__lte=ahora) | Q(bloqueo_hasta__isnull=True)
    ops = OperacionEmision.objects.filter(estado='procesando').filter(expiradas)
    recuperadas = 0
    for op in ops:
        op.estado = 'consultar' if op.envio_iniciado else 'pendiente'
        op.bloqueo_token = None
        op.bloqueo_hasta = None
        op.proximo_intento = ahora
        op.save()
        evento(op, 'operacion_recuperada', 'Consultar recepción antes de enviar.' if op.envio_iniciado
               else 'Preparación local reanudable; se conserva la misma secuencia.')
        recuperadas += 1
    return recuperadas


@transaction.atomic
def reclamar(operacion_id, segundos=60):
    op = OperacionEmision.objects.get(pk=operacion_id)
    ahora = timezone.now()
    if op.estado != 'pendiente' or (op.proximo_intento and op.proximo_intento > ahora):
        return None
    if op.envio_iniciado:
        op.estado = 'consultar'
        op.save()
        evento(op, 'consulta_requerida', 'No se retransmite un envío con resultado desconocido.')
        return None
    op.estado = 'procesando'
    op.bloqueo_token = uuid4()
    op.bloqueo_hasta = ahora + timedelta(seconds=segundos)
    op.intentos += 1
    op.save()
    evento(op, 'preparacion_iniciada')
    return op


def _snapshot_entity(data, cls):
    data = dict(data)
    for name in ('fecha_emision', 'fecha_registro', 'fecha_modificacion'):
        if data.get(name):
            data[name] = datetime.fromisoformat(data[name])
    if data.get('fecha_vencimiento'):
        from datetime import date
        data['fecha_vencimiento'] = date.fromisoformat(data['fecha_vencimiento'])
    if 'monto_total' in data:
        data['monto_total'] = Decimal(data['monto_total'])
    return entidad(SimpleNamespace(**data), cls)


@transaction.atomic
def terminar_preparacion(operacion_id, token, xml='', error=''):
    op = OperacionEmision.objects.filter(pk=operacion_id, estado='procesando',
        bloqueo_token=token, bloqueo_hasta__gt=timezone.now()).first()
    if op is None:
        return False  # El resultado de un trabajador vencido no puede sobrescribir otro.
    op.bloqueo_token = None
    op.bloqueo_hasta = None
    op.ultimo_error = error[:2000]
    if error:
        op.estado = 'pendiente'
        op.proximo_intento = timezone.now() + timedelta(seconds=min(30 * 2 ** min(op.intentos, 6), 1800))
        evento(op, 'preparacion_fallida', op.ultimo_error)
    else:
        op.xml = xml
        op.xml_sha256 = sha256(xml.encode('utf-8')).hexdigest()
        op.estado = 'preparada'
        op.proximo_intento = None
        evento(op, 'documento_preparado', 'XML representativo guardado; pendientes XSD, firma y entidad local.')
    op.save()
    return True


def xml_operacion(op):
    from comprobantes.xml_document import construir_documento
    data = op.instantanea
    factura = _snapshot_entity(data['factura'], Factura)
    cliente = _snapshot_entity(data['cliente'], Cliente)
    resumen = {key: Decimal(value) for key, value in data['totales'].items()}
    return construir_documento(factura, cliente, data['emisor'], factura.lineas, resumen, op.e_ncf)


def procesar_pendientes(limite=100, operacion_id=None):
    """Reanuda únicamente preparación local. No hace llamadas de red."""
    recuperar_interrumpidas()
    ahora = timezone.now()
    pendientes = OperacionEmision.objects.filter(estado='pendiente').filter(
        Q(proximo_intento__isnull=True) | Q(proximo_intento__lte=ahora))
    if operacion_id is not None:
        pendientes = pendientes.filter(pk=operacion_id)
    ids = list(pendientes.order_by('creada').values_list('id', flat=True)[:limite])
    preparadas = 0
    for op_id in ids:
        op = reclamar(op_id)
        if op is None:
            continue
        try:
            xml = xml_operacion(op)
        except Exception as error:
            terminar_preparacion(op.id, op.bloqueo_token, error=f'{type(error).__name__}: {error}')
        else:
            preparadas += terminar_preparacion(op.id, op.bloqueo_token, xml=xml)
    return preparadas

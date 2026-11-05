"""Entrega/consulta duradera por HTTP. No mantiene transacciones durante la red."""
from datetime import timedelta
from uuid import UUID, uuid4
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from .emission import evento
from .models import OperacionEmision


@transaction.atomic
def reclamar_entrega(op_id):
    op = OperacionEmision.objects.get(pk=op_id)
    if op.estado not in ('preparada', 'consultar', 'recibido') or (op.proximo_intento and op.proximo_intento > timezone.now()):
        return None
    enviar = op.estado == 'preparada' and not op.envio_iniciado
    op.estado = 'enviando' if enviar else 'consultando'
    if enviar:
        op.envio_iniciado = timezone.now()  # Se confirma ANTES de abrir la conexión.
    op.bloqueo_token = uuid4()
    op.bloqueo_hasta = timezone.now() + timedelta(seconds=30)
    op.save()
    evento(op, 'envio_iniciado' if enviar else 'consulta_iniciada')
    return op, enviar


@transaction.atomic
def finalizar(op_id, token, enviando, status=None, data=None, error=''):
    op = OperacionEmision.objects.filter(pk=op_id, bloqueo_token=token,
        estado__in=['enviando', 'consultando'], bloqueo_hasta__gt=timezone.now()).first()
    if op is None:
        return False
    op.bloqueo_token = None
    op.bloqueo_hasta = None
    op.proximo_intento = timezone.now() + timedelta(seconds=3)
    op.estado = 'consultar'
    op.ultimo_error = error[:2000]
    if not error and not enviando and status == 404 and data == {'error': 'No recibido.'}:
        op.estado = 'preparada'
        op.envio_iniciado = None
        evento(op, 'no_recibido_confirmado', 'Se permite reenviar exactamente el mismo documento y reserva.')
    elif not error and status in (200, 202):
        try:
            UUID(data['trackId'])
            if (data['eNCF'] != op.e_ncf or data['rnc'] != op.instantanea['emisor']['rnc_raw'] or data['sha256'] != op.xml_sha256
                or data['estado'] not in ('recibido', 'rechazado', 'validado_sin_firma')):
                raise ValueError('Respuesta de la entidad no corresponde al documento reservado.')
            op.resultado_entidad = data
            op.estado = data['estado']
            op.ultimo_error = ''
            op.factura.track_id = data['trackId']
            op.factura.estado = {'recibido': 'enviado', 'rechazado': 'rechazado', 'validado_sin_firma': 'validado'}[op.estado]
            op.factura.save(update_fields=['track_id', 'estado'])
            if op.estado != 'recibido':
                op.proximo_intento = None
            evento(op, 'resultado_entidad', op.estado)
        except (KeyError, ValueError, TypeError) as failure:
            op.estado = 'conflicto'
            op.ultimo_error = str(failure)
            op.proximo_intento = None
            evento(op, 'respuesta_incompatible', op.ultimo_error)
    elif not error and status in (400, 409, 415):
        op.estado = 'conflicto' if status == 409 else 'rechazado'
        op.resultado_entidad = data
        op.ultimo_error = data.get('error', 'La entidad no recibió el documento.')[:2000]
        op.proximo_intento = None
        if op.estado == 'rechazado':
            op.factura.estado = 'rechazado'
            op.factura.save(update_fields=['estado'])
        evento(op, 'entrega_detenida', op.ultimo_error)
    else:
        op.ultimo_error = error[:2000] if error else f'Entidad HTTP {status}. Se consultará antes de cualquier reenvío.'
        evento(op, 'resultado_incierto', op.ultimo_error)
    op.save()
    return True


def integrar_pendientes(limite=100, operacion_id=None):
    if not settings.LOCAL_ENTITY_ENABLED:
        return 0
    from dgii_mock.transport import enviar, consultar
    qs = OperacionEmision.objects.filter(estado__in=['preparada', 'consultar', 'recibido']).filter(
        Q(proximo_intento__isnull=True) | Q(proximo_intento__lte=timezone.now()))
    if operacion_id:
        qs = qs.filter(pk=operacion_id)
    ids = list(qs.order_by('creada').values_list('id', flat=True)[:limite])
    count = 0
    for op_id in ids:
        claim = reclamar_entrega(op_id)
        if claim is None:
            continue
        op, is_send = claim
        try:
            status, data = enviar(op.xml) if is_send else consultar(op.e_ncf)
        except Exception as error:
            count += finalizar(op.id, op.bloqueo_token, is_send, error=f'{type(error).__name__}: {error}')
        else:
            count += finalizar(op.id, op.bloqueo_token, is_send, status=status, data=data)
    return count

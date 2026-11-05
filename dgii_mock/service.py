from datetime import timedelta
from hashlib import sha256
import re

from django.db import transaction
from django.utils import timezone

from .models import AuditoriaEntidad, ConfiguracionEntidad, RecepcionLocal
from .validation import analizar, validar


def audit(actor, accion, detalle='', recepcion=None):
    AuditoriaEntidad.objects.create(actor=actor, accion=accion, detalle=detalle, recepcion=recepcion)


@transaction.atomic(using='entidad')
def recibir(raw):
    config = ConfiguracionEntidad.objects.get(pk='principal')
    if config.escenario == 'indisponible':
        audit('api', 'servicio_indisponible')
        return {'error': 'Servicio local temporalmente no disponible.'}, 503
    digest = sha256(raw).hexdigest()
    try:
        root = analizar(raw)
        rnc = root.findtext('Encabezado/Emisor/RNCEmisor', '').strip()
        encf = root.findtext('Encabezado/IdDoc/eNCF', '').strip()
        tipo = root.findtext('Encabezado/IdDoc/TipoeCF', '').strip()
        if not re.fullmatch(r'E(31|32)[0-9]{10}', encf) or tipo != encf[1:3]:
            raise ValueError('Tipo o e-NCF no soportado/coherente.')
        xml = raw.decode('utf-8-sig')
    except (ValueError, UnicodeError) as error:
        audit('api', 'documento_no_recibido', f'{error} SHA256={digest}')
        return {'error': str(error)}, 400
    if rnc != config.rnc_autorizado:
        audit('api', 'emisor_no_autorizado', f'{rnc} {encf} SHA256={digest}')
        return {'error': 'La credencial de esta instalación no autoriza ese emisor.'}, 403
    previous = RecepcionLocal.objects.filter(emisor=rnc, encf=encf).first()
    if previous is not None:
        if previous.sha256 != digest:
            audit('api', 'conflicto_contenido', f'Nuevo SHA256={digest}', previous)
            return {'error': 'e-NCF ya recibido con contenido diferente.', 'trackId': str(previous.track_id)}, 409
        audit('api', 'recepcion_repetida', recepcion=previous)
        return respuesta(previous), 200
    receipt = RecepcionLocal.objects.create(emisor=rnc, encf=encf, tipo=tipo, xml=xml, sha256=digest,
        procesar_desde=timezone.now()+timedelta(seconds=config.demora_segundos if config.escenario == 'demora' else 0))
    audit('api', 'documento_recibido', f'SHA256={digest}', receipt)
    if config.escenario == 'respuesta_perdida':
        return {'error': 'Se simuló la pérdida de respuesta después de guardar la recepción.'}, 504
    return respuesta(receipt), 202


def respuesta(receipt):
    return {'trackId': str(receipt.track_id), 'rnc': receipt.emisor, 'eNCF': receipt.encf,
            'estado': receipt.estado, 'fechaRecepcion': receipt.recibida.isoformat(),
            'sha256': receipt.sha256, 'comprobaciones': receipt.comprobaciones,
            'validezFiscal': False}


@transaction.atomic(using='entidad')
def procesar_recepciones(manual=False, track_id=None):
    config = ConfiguracionEntidad.objects.get(pk='principal')
    if not manual and (not config.automatico or config.escenario == 'indisponible'):
        return 0
    qs = RecepcionLocal.objects.filter(estado='recibido').order_by('recibida')
    if not manual:
        qs = qs.filter(procesar_desde__lte=timezone.now())
    if track_id is not None:
        qs = qs.filter(pk=track_id)
    count = 0
    for receipt in qs[:100]:
        checks = validar(analizar(receipt.xml.encode('utf-8')))
        receipt.comprobaciones = checks
        receipt.estado = 'rechazado' if any(c['estado'] == 'error' for c in checks) else 'validado_sin_firma'
        receipt.procesada = timezone.now()
        receipt.save()
        audit('administrador' if manual else 'trabajador', 'documento_procesado', receipt.estado, receipt)
        count += 1
    return count

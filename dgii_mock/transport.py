"""Cliente HTTP exclusivamente loopback; nunca reenvía credenciales por redirecciones."""
import json
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from django.conf import settings
from .security import token


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def solicitud(path, raw=None):
    base = settings.LOCAL_ENTITY_URL.rstrip('/')
    parsed = urlsplit(base)
    if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1') or parsed.username or parsed.password:
        raise ValueError('La URL de la entidad debe ser HTTP local sin credenciales en la URL.')
    headers = {'Authorization': f'Bearer {token()}', 'Accept': 'application/json'}
    if raw is not None:
        headers['Content-Type'] = 'application/xml'
    request = Request(base + path, data=raw, headers=headers, method='POST' if raw is not None else 'GET')
    try:
        response = build_opener(NoRedirect()).open(request, timeout=3)
    except HTTPError as error:
        response = error
    with response:
        body = response.read(1024 * 1024)
        try:
            data = json.loads(body)
            if not isinstance(data, dict):
                raise ValueError('Se esperaba un objeto JSON.')
        except (ValueError, UnicodeError) as error:
            raise ValueError('La entidad devolvió una respuesta no reconocida.') from error
        return response.status, data


def enviar(xml):
    return solicitud('/api/recepciones/', xml.encode('utf-8'))


def consultar(encf):
    return solicitud('/api/consulta/?' + urlencode({'encf': encf}))

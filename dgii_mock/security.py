from functools import wraps
import hmac
from ipaddress import ip_address
from pathlib import Path
import secrets

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils.crypto import salted_hmac
from .models import AdministradorEntidad

SESSION_KEY = 'administrador_entidad'


def token(create=False):
    path = Path(settings.LOCAL_ENTITY_TOKEN_FILE)
    if create:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open('x', encoding='ascii') as f:
                f.write(secrets.token_urlsafe(48))
            path.chmod(0o600)
        except FileExistsError:
            pass
    return path.read_text(encoding='ascii').strip()


def local_only(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        try:
            local = ip_address(request.META.get('REMOTE_ADDR', '')).is_loopback
        except ValueError:
            local = False
        if not local:
            raise PermissionDenied('La entidad sólo admite conexiones locales.')
        return view(request, *args, **kwargs)
    return wrapped


def session_value(admin):
    return salted_hmac('entidad-admin', f'{admin.pk}:{admin.password}').hexdigest()


def admin_required(view):
    @local_only
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        admin = AdministradorEntidad.objects.filter(pk='principal').first()
        if admin is None:
            return redirect('entidad:configurar')
        if not hmac.compare_digest(request.session.get(SESSION_KEY, ''), session_value(admin)):
            return redirect('entidad:login')
        request.entidad_admin = admin
        return view(request, *args, **kwargs)
    return wrapped


def api_required(view):
    @local_only
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        try:
            expected = token()
        except FileNotFoundError:
            return JsonResponse({'error': 'Entidad no inicializada.'}, status=503)
        if len(expected) < 32:
            return JsonResponse({'error': 'Credencial de instalación no inicializada correctamente.'}, status=503)
        if not hmac.compare_digest(request.headers.get('Authorization', ''), f'Bearer {expected}'):
            return JsonResponse({'error': 'Credencial de integración inválida.'}, status=401)
        return view(request, *args, **kwargs)
    return wrapped

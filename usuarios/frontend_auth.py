"""Identidad temporal de frontend. Nunca guarda usuarios ni consulta modelos."""

from django.conf import settings
from django.utils.crypto import constant_time_compare, salted_hmac

from .models import Usuario

USERNAME = 'user'
PASSWORD = '1234'
SESSION_KEY = 'frontend_identity'


def enabled():
    return settings.DEBUG and getattr(settings, 'FRONTEND_AUTH_ENABLED', False)


def session_identity(username=USERNAME):
    return salted_hmac('usuarios.frontend_auth', f'{username}:{PASSWORD}').hexdigest()


def get_user(username=USERNAME, first_name='', last_name='', rol=Usuario.Rol.ADMIN):
    # Instancia en memoria construida dinámicamente según la sesión activa; sin hardcodeo de nombres.
    return Usuario(
        pk=-1,
        username=username,
        first_name=first_name,
        last_name=last_name,
        rol=rol,
        is_active=True,
        is_staff=False,
        is_superuser=False,
    )


def authenticate(username, password):
    if enabled() and constant_time_compare(username, USERNAME) and constant_time_compare(password, PASSWORD):
        return get_user(username=username)
    return None


class FrontendAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Si request.user ya fue autenticado por Django (vía base de datos o force_login), respetarlo.
        if hasattr(request, 'user') and request.user.is_authenticated and getattr(request.user, 'pk', None) != -1:
            return self.get_response(request)

        if enabled():
            identity = request.session.get(SESSION_KEY, '')
            username = request.session.get('frontend_username', USERNAME)
            if identity and (constant_time_compare(identity, session_identity(username)) or constant_time_compare(identity, session_identity(USERNAME))):
                first_name = request.session.get('frontend_first_name', '')
                last_name = request.session.get('frontend_last_name', '')
                rol = request.session.get('frontend_rol', Usuario.Rol.ADMIN)
                user = get_user(username=username, first_name=first_name, last_name=last_name, rol=rol)
                request.user = user

                async def auser():
                    return user

                request.auser = auser
        return self.get_response(request)

"""Segundo servidor local: API y panel; sin acceso mediante el login de facturación."""
from .settings import *

ENTITY_MODE = True
ROOT_URLCONF = 'dgii_mock.urls'
SESSION_COOKIE_NAME = 'entidad_sessionid'
CSRF_COOKIE_NAME = 'entidad_csrftoken'
FRONTEND_AUTH_ENABLED = False
MIDDLEWARE = [m for m in MIDDLEWARE if m != 'usuarios.frontend_auth.FrontendAuthenticationMiddleware']
DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024

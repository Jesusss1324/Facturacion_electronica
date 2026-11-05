"""Arranque del segundo servidor y su trabajador, sin ventanas de consola adicionales."""
import atexit
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import urlopen

from django.conf import settings
from django.core.management import call_command
from django.db import connections
from .security import token


def inicializar():
    call_command('migrate', database='entidad', verbosity=0, interactive=False)
    token(create=True)


def ejecutar():
    from .service import procesar_recepciones
    while True:
        try:
            procesar_recepciones()
        except Exception:
            logging.getLogger(__name__).exception('No se pudo procesar la cola de la entidad')
        finally:
            connections.close_all()
        time.sleep(1)


def iniciar_servidor():
    inicializar()
    try:
        with urlopen(settings.LOCAL_ENTITY_URL + '/health/', timeout=1) as response:
            if json.load(response).get('servicio') == 'entidad-local-ecf':
                return
            raise RuntimeError('El puerto de la entidad está ocupado por otro servicio.')
    except OSError:
        pass
    from urllib.parse import urlsplit
    url = urlsplit(settings.LOCAL_ENTITY_URL)
    if url.hostname != '127.0.0.1':
        raise ValueError('El arranque automático requiere 127.0.0.1.')
    local = Path(settings.LOCAL_ENTITY_TOKEN_FILE).parent
    local.mkdir(parents=True, exist_ok=True)
    with (local / 'entidad.log').open('a', encoding='utf-8') as log:
        env = dict(os.environ, DJANGO_SETTINGS_MODULE='facturacion_ecf.entity_settings')
        env.pop('RUN_MAIN', None)
        process = subprocess.Popen([sys.executable, str(Path(settings.BASE_DIR) / 'manage.py'),
            'runserver', f'127.0.0.1:{url.port or 8001}', '--noreload', '--settings=facturacion_ecf.entity_settings'],
            cwd=settings.BASE_DIR, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    def cerrar():
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
    atexit.register(cerrar)

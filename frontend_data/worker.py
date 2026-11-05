"""Preparación periódica local; el proceso termina junto con el servidor."""
import logging
import time

from django.db import connections

from .emission import procesar_pendientes


def ejecutar():
    while True:
        try:
            procesar_pendientes()
            from .entity_client import integrar_pendientes
            integrar_pendientes()
        except Exception:
            logging.getLogger(__name__).exception('No se pudo recuperar la cola de emisiones')
        finally:
            connections.close_all()
        time.sleep(2)

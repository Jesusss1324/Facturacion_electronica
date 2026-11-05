"""Configuración de la única empresa de esta instalación."""
from django.conf import settings


def get_emisor_info():
    if settings.FRONTEND_DATA_BACKEND == 'memory':
        # Sólo las pruebas aisladas leen la instantánea de la migración.
        import json
        from pathlib import Path
        return json.loads((Path(__file__).parent / 'migrations' / 'emisor_v1.json').read_text(encoding='utf-8'))
    from .models import ConfiguracionEmisor
    return ConfiguracionEmisor.objects.get(pk='principal').datos

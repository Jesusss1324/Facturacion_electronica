"""Configuración de la única empresa de esta instalación."""
from django.conf import settings


def get_emisor_info():
    if settings.FRONTEND_DATA_BACKEND == 'memory':
        # Sólo las pruebas aisladas leen la instantánea de la migración.
        import json
        from pathlib import Path
        root = Path(__file__).parent / 'migrations'
        data = json.loads((root / 'emisor_v1.json').read_text(encoding='utf-8'))
        nuevo = json.loads((root / 'demo_v2_correcciones.json').read_text(encoding='utf-8'))['emisor']['nuevo']
        data.update(rnc_raw=nuevo, rnc=f'{nuevo[:1]}-{nuevo[1:3]}-{nuevo[3:8]}-{nuevo[8:]}')
        return data
    from .models import ConfiguracionEmisor
    return ConfiguracionEmisor.objects.get(pk='principal').datos

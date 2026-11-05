"""Carga transaccional y única del conjunto de demostración versionado."""
import json
from pathlib import Path

from django.db import transaction


def cargar_demo(apps, schema_editor=None, using='default'):
    if schema_editor is not None:
        using = schema_editor.connection.alias
    marker = apps.get_model('frontend_data', 'CargaInicial')
    with transaction.atomic(using=using):
        if marker.objects.using(using).filter(pk='demo-v1').exists():
            return False
        data = json.loads((Path(__file__).parent / 'migrations' / 'demo_v1.json').read_text(encoding='utf-8'))
        models = {name: apps.get_model('frontend_data', name) for name in data}
        if any(model.objects.using(using).exists() for model in models.values()):
            raise RuntimeError('Hay datos existentes: no se cargaron ni sobrescribieron datos de demostración.')
        for name, rows in data.items():
            models[name].objects.using(using).bulk_create(models[name](**row) for row in rows)
        marker.objects.using(using).create(clave='demo-v1')
        return True

import json
from importlib import import_module
from pathlib import Path
from django.db import migrations


def completar(apps, schema_editor):
    if schema_editor.connection.alias != 'entidad':
        return
    if apps.get_model('dgii_mock', 'AdministradorEntidad').objects.using('entidad').exists():
        return
    if apps.get_model('dgii_mock', 'RecepcionLocal').objects.using('entidad').exists():
        return
    import_module('dgii_mock.migrations.0003_padron_inicial').cargar(apps, schema_editor)
    root = Path(__file__).resolve().parents[2] / 'frontend_data' / 'migrations'
    original = json.loads((root / 'demo_v1.json').read_text(encoding='utf-8'))['ClienteRegistro']
    cambios = json.loads((root / 'demo_v2_correcciones.json').read_text(encoding='utf-8'))
    mapa = {c['id']: c['nuevo'] for c in cambios['clientes']}
    padron = apps.get_model('dgii_mock', 'ContribuyenteLocal')
    nombres = [c['nombre'] for c in original]
    for c in original:
        padron.objects.using('entidad').filter(identificacion=mapa[c['id']], nombre__in=nombres).update(
            nombre=c['nombre'], activo=c['activo'])


class Migration(migrations.Migration):
    dependencies = [('dgii_mock', '0003_padron_inicial')]
    operations = [migrations.RunPython(completar, migrations.RunPython.noop, hints={'model_name': 'configuracionentidad'})]

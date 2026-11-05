import json
from datetime import date
from pathlib import Path
from django.db import migrations


def cargar(apps, schema_editor):
    alias = schema_editor.connection.alias
    if alias != 'entidad':
        return
    root = Path(__file__).resolve().parents[2] / 'frontend_data' / 'migrations'
    datos = json.loads((root / 'demo_v1.json').read_text(encoding='utf-8'))
    cambios = json.loads((root / 'demo_v2_correcciones.json').read_text(encoding='utf-8'))
    emisor = json.loads((root / 'emisor_v1.json').read_text(encoding='utf-8'))
    correcciones = {c['id']: c['nuevo'] for c in cambios['clientes']}
    padron = apps.get_model('dgii_mock', 'ContribuyenteLocal')
    for c in datos['ClienteRegistro']:
        padron.objects.using(alias).get_or_create(identificacion=correcciones[c['id']], defaults={
            'nombre': c['nombre'], 'activo': c['activo'], 'receptor_credito': True})
    empresa, _ = padron.objects.using(alias).get_or_create(identificacion=cambios['emisor']['nuevo'],
        defaults={'nombre': emisor['razon_social'], 'emisor': True})
    apps.get_model('dgii_mock', 'ConfiguracionEntidad').objects.using(alias).get_or_create(
        clave='principal', defaults={'rnc_autorizado': empresa.identificacion, 'semilla_cargada': True})
    rango = apps.get_model('dgii_mock', 'RangoLocal')
    for tipo in ('31', '32'):
        rango.objects.using(alias).get_or_create(emisor=empresa, tipo=tipo, desde=1,
            defaults={'hasta': 9999999999, 'vencimiento': date(2028, 12, 31)})


class Migration(migrations.Migration):
    dependencies = [('dgii_mock', '0002_administradorentidad_configuracionentidad_and_more')]
    operations = [migrations.RunPython(cargar, migrations.RunPython.noop, hints={'model_name': 'configuracionentidad'})]

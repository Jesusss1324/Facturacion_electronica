import json
from pathlib import Path

from django.db import migrations


def cargar(apps, schema_editor):
    config = apps.get_model('frontend_data', 'ConfiguracionEmisor')
    datos = json.loads((Path(__file__).parent / 'emisor_v1.json').read_text(encoding='utf-8'))
    config.objects.using(schema_editor.connection.alias).get_or_create(
        clave='principal', defaults={'datos': datos})


class Migration(migrations.Migration):
    dependencies = [('frontend_data', '0003_configuracionemisor')]
    operations = [migrations.RunPython(cargar, migrations.RunPython.noop)]

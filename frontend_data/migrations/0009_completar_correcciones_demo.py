from importlib import import_module
from django.db import migrations


def corregir(apps, schema_editor):
    import_module('frontend_data.migrations.0007_corregir_demo').corregir(apps, schema_editor)


class Migration(migrations.Migration):
    dependencies = [('frontend_data', '0008_operacionemision_resultado_entidad_and_more')]
    operations = [migrations.RunPython(corregir, migrations.RunPython.noop)]

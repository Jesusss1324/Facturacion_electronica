from django.db import migrations


def cargar(apps, schema_editor):
    from frontend_data.seed import cargar_demo
    cargar_demo(apps, schema_editor)


class Migration(migrations.Migration):
    dependencies = [('frontend_data', '0001_initial')]
    operations = [migrations.RunPython(cargar, migrations.RunPython.noop)]

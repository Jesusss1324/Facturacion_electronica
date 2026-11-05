from django.db import migrations


def cargar(apps, schema_editor):
    factura = apps.get_model('frontend_data', 'FacturaRegistro')
    secuencia = apps.get_model('frontend_data', 'SecuenciaLocal')
    alias = schema_editor.connection.alias
    for tipo in ('31', '32'):
        valores = factura.objects.using(alias).filter(tipo_ecf=tipo).values_list('e_ncf', flat=True)
        maximo = max((int(v[3:]) for v in valores if v.startswith(f'E{tipo}') and v[3:].isdigit()), default=0)
        secuencia.objects.using(alias).get_or_create(tipo_ecf=tipo, defaults={'siguiente': maximo + 1})


class Migration(migrations.Migration):
    dependencies = [('frontend_data', '0005_operacionemision_eventooperacion_secuencialocal_and_more')]
    operations = [migrations.RunPython(cargar, migrations.RunPython.noop)]

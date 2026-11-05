import json
from datetime import date
from pathlib import Path
from django.db import migrations


def corregir(apps, schema_editor):
    alias = schema_editor.connection.alias
    if alias != 'default':
        return
    cambios = json.loads((Path(__file__).parent / 'demo_v2_correcciones.json').read_text(encoding='utf-8'))
    cliente = apps.get_model('frontend_data', 'ClienteRegistro')
    pendientes = [c for c in cambios['clientes'] if c['nuevo'] != c['anterior'] and
        cliente.objects.using(alias).filter(pk=c['id'], identificacion__in=[c['anterior'], c.get('previo', c['anterior'])]).exists()]
    movibles = {c['id'] for c in pendientes}
    pendientes = [c for c in pendientes if not cliente.objects.using(alias).filter(
        identificacion=c['nuevo']).exclude(pk__in=movibles).exists()]
    # Dos fases para evitar que un identificador corregido choque con otro
    # identificador demo que también va a cambiar en esta misma transacción.
    for c in pendientes:
        cliente.objects.using(alias).filter(pk=c['id']).update(identificacion=f"X{c['id']:010d}")
    for c in pendientes:
        cliente.objects.using(alias).filter(pk=c['id']).update(identificacion=c['nuevo'])
    config = apps.get_model('frontend_data', 'ConfiguracionEmisor').objects.using(alias).get(pk='principal')
    anterior, nuevo = cambios['emisor']['anterior'], cambios['emisor']['nuevo']
    if config.datos.get('rnc_raw') == anterior:
        config.datos.update(rnc_raw=nuevo, rnc=f'{nuevo[:1]}-{nuevo[1:3]}-{nuevo[3:8]}-{nuevo[8:]}')
        config.save(using=alias)
    apps.get_model('frontend_data', 'SecuenciaLocal').objects.using(alias).filter(vencimiento=None).update(vencimiento=date(2028, 12, 31))


class Migration(migrations.Migration):
    dependencies = [('frontend_data', '0006_inicializar_secuencias')]
    operations = [migrations.RunPython(corregir, migrations.RunPython.noop)]

from dataclasses import replace
from datetime import date
from decimal import Decimal
from io import StringIO
from uuid import uuid4

from django.apps import apps
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from comprobantes.totales import huella_borrador
from .entities import LineaFactura
from .fixtures import build_clientes, build_facturas, build_logs
from .models import ClienteRegistro, FacturaRegistro
from .repository import get_repository
from .seed import cargar_demo
from .sqlite_repository import SQLiteRepository


@override_settings(LOCAL_ENTITY_ENABLED=False, FRONTEND_DATA_BACKEND='sqlite', DEBUG=True, FRONTEND_AUTH_ENABLED=True,
                   SESSION_ENGINE='django.contrib.sessions.backends.signed_cookies')
class SQLiteRepositoryTests(TestCase):
    def test_runtime_reads_only_sqlite_and_emitter_changes_reach_views_and_xml(self):
        from unittest.mock import patch
        from .configuration import get_emisor_info
        from .models import ConfiguracionEmisor
        from comprobantes.views_xml import construir_xml_factura
        config = ConfiguracionEmisor.objects.get(pk='principal')
        config.datos = {**config.datos, 'razon_social': 'Emisor actualizado & verificado'}
        config.save()
        with patch('frontend_data.repository.get_demo_repository', side_effect=AssertionError('No usar fixtures')):
            self.assertEqual(get_emisor_info()['razon_social'], config.datos['razon_social'])
            factura = get_repository().get_factura(1)
            xml = construir_xml_factura(factura, self.repo.get_cliente(factura.cliente_id))
            self.assertIn('Emisor actualizado &amp; verificado', xml)
            self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})
            self.assertContains(self.client.get('/facturas/1/pdf/'), 'Emisor actualizado &amp; verificado')

    def setUp(self):
        self.repo = get_repository()

    def draft(self):
        borrador = self.repo.create_borrador('31', 1)
        linea = LineaFactura(uuid4(), 'servicio', 'Soporte & <gestión>', '', 'Servicio',
                             Decimal('2.50'), Decimal('123.45'), Decimal('1.01'))
        self.repo.update_borrador(borrador.id, fecha_emision=date(2026, 11, 4))
        self.repo.guardar_linea(borrador.id, linea, 0)
        actual = self.repo.get_borrador(borrador.id)
        huella = huella_borrador(actual)
        self.repo.guardar_totales(borrador.id, huella, recalcular=True)
        return self.repo.get_borrador(borrador.id), huella

    def test_seed_preserves_all_demo_entities_and_dashboard_counts(self):
        clientes = build_clientes()
        facturas = build_facturas(clientes)
        self.assertEqual(self.repo.list_clientes(), clientes)
        self.assertEqual(self.repo.list_facturas(), tuple(sorted(facturas,
            key=lambda f: (f.fecha_emision, f.id), reverse=True)))
        self.assertEqual(self.repo.list_logs(), tuple(sorted(build_logs(clientes, facturas),
            key=lambda l: (l.timestamp, l.id), reverse=True)))
        resumen = self.repo.resumen_inicio()
        self.assertEqual((resumen.emitidas, resumen.aprobadas, resumen.rechazadas,
                          resumen.clientes_activos), (128, 119, 9, 42))

    def test_seed_is_idempotent_and_does_not_restore_deleted_or_edited_data(self):
        self.repo.update_cliente(1, nombre='Nombre actualizado')
        FacturaRegistro.objects.filter(pk=1).delete()
        self.assertFalse(cargar_demo(apps))
        call_command('cargar_demo', stdout=StringIO())
        self.assertEqual(self.repo.get_cliente(1).nombre, 'Nombre actualizado')
        self.assertEqual(FacturaRegistro.objects.count(), 127)

    def test_clients_persist_between_repository_instances_and_uniqueness_is_enforced(self):
        source = self.repo.get_cliente(1)
        from dataclasses import asdict
        datos = asdict(replace(source, identificacion='999888777', nombre='Cliente persistente'))
        datos.pop('id')
        cliente = self.repo.create_cliente(**datos)
        fresh = SQLiteRepository()
        self.assertEqual(fresh.get_cliente(cliente.id), cliente)
        fresh.set_cliente_activo(cliente.id, False)
        self.assertFalse(self.repo.get_cliente(cliente.id).activo)
        with self.assertRaises(ValueError):
            fresh.create_cliente(**datos)
        with self.assertRaises(ValueError):
            fresh.update_cliente(2, identificacion=cliente.identificacion)
        self.assertEqual(fresh.get_cliente(2), self.repo.get_cliente(2))

    def test_draft_roundtrip_preserves_uuid_decimal_and_saved_fingerprint(self):
        borrador, huella = self.draft()
        actual = SQLiteRepository().get_borrador(str(borrador.id))
        self.assertEqual(actual, borrador)
        self.assertEqual(huella_borrador(actual), huella)
        self.assertIsInstance(actual.lineas[0].precio, Decimal)
        self.assertIsInstance(actual.fecha_emision, date)

    def test_stale_line_revision_cannot_overwrite_a_saved_change(self):
        borrador, _ = self.draft()
        edited = replace(borrador.lineas[0], concepto='Cambio confirmado')
        self.repo.guardar_linea(borrador.id, edited, 1, editar=True)
        with self.assertRaises(ValueError):
            SQLiteRepository().guardar_linea(borrador.id, borrador.lineas[0], 1, editar=True)
        self.assertEqual(self.repo.get_borrador(borrador.id).lineas[0].concepto, 'Cambio confirmado')

    def test_emission_link_persists_and_database_prevents_duplicate_draft_or_encf(self):
        borrador, huella = self.draft()
        factura = self.repo.emitir_factura(borrador.id, huella)
        fresh = SQLiteRepository()
        self.assertEqual(fresh.emitir_factura(borrador.id, huella), factura)
        self.assertEqual(fresh.factura_emitida_borrador(borrador.id), factura)
        self.assertEqual(FacturaRegistro.objects.count(), 129)
        with self.assertRaises(ValueError):
            fresh.update_borrador(borrador.id, forma_pago='01')
        from .serialization import registro
        for datos in (dict(registro(factura), id=9999, e_ncf='E310099999999'),
                      dict(registro(factura), id=9999)):
            with self.assertRaises(IntegrityError), transaction.atomic():
                FacturaRegistro.objects.create(**datos, borrador_id=borrador.id)

    def test_invalid_emission_rolls_back_without_consuming_invoice(self):
        borrador, huella = self.draft()
        with self.assertRaises(ValueError):
            self.repo.emitir_factura(borrador.id, 'desactualizada')
        self.assertEqual(FacturaRegistro.objects.count(), 128)
        self.repo.set_cliente_activo(1, False)
        with self.assertRaises(ValueError):
            self.repo.emitir_factura(borrador.id, huella)
        self.assertIsNone(self.repo.factura_emitida_borrador(borrador.id))

    def test_http_pages_and_downloads_use_sqlite_without_mocking_repository(self):
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})
        for url in ('/inicio/', '/clientes/', '/clientes/1/', '/facturas/',
                    '/facturas/1/', '/facturas/1/xml/', '/facturas/1/pdf/', '/bitacora/'):
            if url == '/bitacora/':
                url = reverse('bitacora:listado')
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        self.repo.update_cliente(1, nombre='Cambio visible desde SQLite')
        self.assertContains(self.client.get('/clientes/1/'), 'Cambio visible desde SQLite')
        borrador, huella = self.draft()
        url = reverse('comprobantes:emitir', kwargs={'borrador_id': borrador.id})
        first = self.client.post(url, {'huella': huella})
        second = self.client.post(url, {'huella': huella})
        self.assertEqual(first.status_code, 302)
        self.assertEqual(first['Location'], second['Location'])
        factura = self.repo.factura_emitida_borrador(borrador.id)
        for name in ('xml', 'pdf', 'descargar_xml', 'descargar_pdf'):
            self.assertEqual(self.client.get(reverse(f'comprobantes:{name}',
                kwargs={'pk': factura.id})).status_code, 200)

    def test_missing_records_keep_keyerror_contract(self):
        for getter in (self.repo.get_cliente, self.repo.get_factura, self.repo.get_log):
            with self.assertRaises(KeyError):
                getter(999999)
        with self.assertRaises(KeyError):
            self.repo.get_borrador(uuid4())


class SQLiteProcessTests(SimpleTestCase):
    def test_restart_and_simultaneous_processes_keep_data_and_one_emission(self):
        """Base temporal en disco: cada subprocess abre su propia conexión SQLite."""
        import os
        from concurrent.futures import ThreadPoolExecutor
        from pathlib import Path
        import subprocess
        import sys
        import tempfile
        prelude = '''
import os, json
os.environ['DJANGO_SETTINGS_MODULE'] = 'facturacion_ecf.settings'
from django.conf import settings
settings.DATABASES['default']['NAME'] = os.environ['PERSISTENCE_TEST_DB']
import django
django.setup()
from frontend_data.repository import get_repository
repo = get_repository()
'''
        prepare = '''
from django.core.management import call_command
call_command('migrate', verbosity=0)
from datetime import date
from decimal import Decimal
from uuid import uuid4
from frontend_data.entities import LineaFactura
from comprobantes.totales import huella_borrador
repo.update_cliente(1, nombre='Conservado después del cierre')
repo.set_cliente_activo(2, False)
b = repo.create_borrador('31', 1)
repo.update_borrador(b.id, fecha_emision=date(2026, 11, 4))
repo.guardar_linea(b.id, LineaFactura(uuid4(), 'servicio', 'Soporte', '', 'Servicio',
    Decimal('2.50'), Decimal('123.45'), Decimal('1.01')), 0)
huella = huella_borrador(repo.get_borrador(b.id))
repo.guardar_totales(b.id, huella, recalcular=True)
print(json.dumps({'id': str(b.id), 'huella': huella}))
'''
        send = '''
from uuid import UUID
f = repo.emitir_factura(UUID(os.environ['DRAFT_ID']), os.environ['DRAFT_HASH'])
print(json.dumps({'id': f.id, 'encf': f.e_ncf}))
'''
        verify = '''
from uuid import UUID
from frontend_data.seed import cargar_demo
from django.apps import apps
assert not cargar_demo(apps)
assert repo.get_cliente(1).nombre == 'Conservado después del cierre'
assert not repo.get_cliente(2).activo
assert len(repo.list_facturas()) == 129
b = repo.get_borrador(UUID(os.environ['DRAFT_ID']))
assert str(b.lineas[0].precio) == '123.45'
f = repo.factura_emitida_borrador(b.id)
assert f is not None and f.lineas == b.lineas
from frontend_data.emission import procesar_pendientes
from frontend_data.models import OperacionEmision, SecuenciaLocal
assert procesar_pendientes() == 1
op = OperacionEmision.objects.get(factura_id=f.id)
assert op.estado == 'preparada' and op.xml and op.intentos == 2
assert OperacionEmision.objects.count() == 1
assert SecuenciaLocal.objects.get(pk='31').siguiente == op.numero + 1
print('persistencia verificada')
'''
        import json
        # Los subprocess deben compartir un directorio accesible, también bajo
        # el aislamiento de Windows (su TEMP puede ser distinto por proceso).
        from django.conf import settings
        temporary_root = Path(settings.BASE_DIR) / 'tmp'
        temporary_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temporary_root) as directory:
            env = dict(os.environ, PERSISTENCE_TEST_DB=str(Path(directory) / 'prueba.sqlite3'))

            def run(code):
                result = subprocess.run([sys.executable, '-c', prelude + code],
                    env=env, capture_output=True, text=True, encoding='utf-8', timeout=60)
                self.assertEqual(result.returncode, 0, result.stderr)
                return result.stdout.strip()

            prepared = json.loads(run(prepare))
            env.update(DRAFT_ID=prepared['id'], DRAFT_HASH=prepared['huella'])
            with ThreadPoolExecutor(max_workers=4) as executor:
                results = list(executor.map(lambda _: json.loads(run(send)), range(4)))
            self.assertEqual(len({(f['id'], f['encf']) for f in results}), 1)
            # Un proceso reclama trabajo y termina sin completarlo. Otro proceso
            # recupera su bloqueo vencido, con la misma factura y reserva.
            run("""
from datetime import timedelta
from django.utils import timezone
from frontend_data.models import OperacionEmision
from frontend_data.emission import reclamar
op = reclamar(OperacionEmision.objects.get().id)
assert op is not None
OperacionEmision.objects.filter(pk=op.id).update(bloqueo_hasta=timezone.now()-timedelta(seconds=1))
""")
            self.assertEqual(run(verify), 'persistencia verificada')

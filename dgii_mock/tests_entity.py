from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import tempfile
from unittest.mock import patch
from uuid import uuid4

from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from lxml import etree

from comprobantes.items import resumen_lineas
from comprobantes.xml_document import construir_documento
from frontend_data.configuration import get_emisor_info
from frontend_data.entities import LineaFactura
from frontend_data.sqlite_repository import SQLiteRepository
from .forms import RangoForm
from .models import (AdministradorEntidad, AuditoriaEntidad, ConfiguracionEntidad,
                     ContribuyenteLocal, RangoLocal, RecepcionLocal)
from .security import SESSION_KEY, token
from .service import procesar_recepciones, recibir
from .validation import analizar, comprobar_xsd, validar


@override_settings(ROOT_URLCONF='dgii_mock.urls', FRONTEND_DATA_BACKEND='sqlite',
                   SESSION_ENGINE='django.contrib.sessions.backends.signed_cookies')
class EntidadTests(TestCase):
    databases = {'default', 'entidad'}

    def setUp(self):
        root = Path(settings.BASE_DIR) / 'tmp'
        root.mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(dir=root)
        self.addCleanup(self.directory.cleanup)
        self.override = override_settings(LOCAL_ENTITY_TOKEN_FILE=Path(self.directory.name) / 'api.key')
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.key = token(create=True)

    def xml(self, tipo='31', encf=None):
        repo = SQLiteRepository()
        cliente = repo.get_cliente(1 if tipo == '31' else 2)
        linea = LineaFactura(uuid4(), 'servicio', 'Gestión & soporte', '', 'Servicio',
                            Decimal('2.50'), Decimal('100.00'), Decimal('1.00'))
        factura = replace(repo.get_factura(1), tipo_ecf=tipo, e_ncf=encf or f'E{tipo}0000000900',
            cliente_id=cliente.id, lineas=(linea,), fecha_emision=timezone.now(),
            monto_total=linea.total, vencimiento_secuencia='31/12/2028')
        return construir_documento(factura, cliente, get_emisor_info(), factura.lineas,
                                   resumen_lineas(factura.lineas), factura.e_ncf).encode()

    def post_xml(self, raw):
        return self.client.post('/api/recepciones/', raw, content_type='application/xml',
                                HTTP_AUTHORIZATION=f'Bearer {self.key}')

    def setup_admin(self, client=None):
        client = client or self.client
        return client.post('/entidad/configurar/', {'usuario': 'autoridad',
            'password': 'Entidad!Pruebas-2026-segura', 'confirmar': 'Entidad!Pruebas-2026-segura'})

    def test_xsd_content_and_rules_for_both_types_never_claim_valid_signature(self):
        for tipo in ('31', '32'):
            root = analizar(self.xml(tipo))
            ok, detalle = comprobar_xsd(root, tipo, contenido=True)
            self.assertTrue(ok, detalle)
            self.assertFalse(comprobar_xsd(root, tipo)[0])
            checks = validar(root)
            self.assertFalse([c for c in checks if c['estado'] == 'error'])
            self.assertEqual(next(c for c in checks if c['codigo'] == 'FIRMA')['estado'], 'pendiente')

    def test_original_schema_hashes_are_preserved(self):
        import json
        from hashlib import sha256
        root = Path(__file__).parent / 'schemas'
        for item in json.loads((root / 'origen.json').read_text(encoding='utf-8')):
            self.assertEqual(sha256((root / item['archivo']).read_bytes()).hexdigest(), item['sha256'])

    def test_unsupported_tax_profile_is_rejected_instead_of_ignoring_fields(self):
        root = analizar(self.xml())
        etree.SubElement(root.find('DetallesItems/Item'), 'Retencion')
        checks = validar(root)
        self.assertEqual(next(c for c in checks if c['codigo'] == 'PERFIL_18')['estado'], 'error')

    def test_real_xsd_rejects_wrong_structure_and_business_rules_reject_wrong_amount(self):
        root = analizar(self.xml())
        root.find('Encabezado/Version').text = '9.0'
        checks = validar(root)
        self.assertEqual(next(c for c in checks if c['codigo'] == 'XSD_CONTENIDO')['estado'], 'error')
        root = analizar(self.xml())
        root.find('Encabezado/Totales/MontoTotal').text = '1.00'
        checks = validar(root)
        self.assertEqual(next(c for c in checks if c['codigo'] == 'TOTALES')['estado'], 'error')

    def test_padron_is_independent_from_changes_to_billing_clients(self):
        repo = SQLiteRepository()
        root = analizar(self.xml())
        identification = root.findtext('Encabezado/Comprador/RNCComprador')
        repo.set_cliente_activo(1, False)
        self.assertTrue(ContribuyenteLocal.objects.get(identificacion=identification).activo)
        ContribuyenteLocal.objects.filter(identificacion=identification).update(activo=False)
        checks = validar(root)
        self.assertEqual(next(c for c in checks if c['codigo'] == 'PADRON_RECEPTOR')['estado'], 'error')

    def test_ranges_are_independent_and_expired_range_rejects_document(self):
        RangoLocal.objects.filter(tipo='31').update(vencimiento=timezone.localdate()-timedelta(days=1))
        checks = validar(analizar(self.xml()))
        self.assertEqual(next(c for c in checks if c['codigo'] == 'RANGO')['estado'], 'error')

    def test_invalid_identifications_and_foreign_issuer_are_not_approved(self):
        root = analizar(self.xml())
        root.find('Encabezado/Comprador/RNCComprador').text = '123456789'
        self.assertEqual(next(c for c in validar(root) if c['codigo'] == 'IDENTIFICACION_RECEPTOR')['estado'], 'error')
        root.find('Encabezado/Emisor/RNCEmisor').text = '123456789'
        self.assertEqual(self.post_xml(etree.tostring(root)).status_code, 403)

    def test_duplicate_content_returns_same_track_and_conflicting_content_is_audited(self):
        raw = self.xml()
        first, second = self.post_xml(raw), self.post_xml(raw)
        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()['trackId'], second.json()['trackId'])
        conflict = self.post_xml(raw.replace(b'100.00', b'200.00'))
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(RecepcionLocal.objects.count(), 1)
        self.assertTrue(AuditoriaEntidad.objects.filter(accion='conflicto_contenido').exists())

    def test_unavailable_and_lost_response_have_different_persisted_effects(self):
        config = ConfiguracionEntidad.objects.get(pk='principal')
        config.escenario = 'indisponible'; config.save()
        self.assertEqual(self.post_xml(self.xml()).status_code, 503)
        self.assertFalse(RecepcionLocal.objects.exists())
        self.assertEqual(self.client.get('/api/consulta/?encf=E310000000900',
            HTTP_AUTHORIZATION=f'Bearer {self.key}').status_code, 503)
        config.escenario = 'respuesta_perdida'; config.save()
        self.assertEqual(self.post_xml(self.xml()).status_code, 504)
        self.assertEqual(RecepcionLocal.objects.count(), 1)
        response = self.client.get('/api/consulta/?encf=E310000000900', HTTP_AUTHORIZATION=f'Bearer {self.key}')
        self.assertEqual(response.status_code, 200)

    def test_pause_delay_manual_processing_and_restart_pending_queue(self):
        config = ConfiguracionEntidad.objects.get(pk='principal')
        config.automatico = False; config.escenario = 'demora'; config.demora_segundos = 60; config.save()
        self.post_xml(self.xml())
        self.assertEqual(procesar_recepciones(), 0)
        config.automatico = True; config.save()
        self.assertEqual(procesar_recepciones(), 0)
        self.assertEqual(procesar_recepciones(manual=True), 1)
        receipt = RecepcionLocal.objects.get()
        self.assertEqual(receipt.estado, 'validado_sin_firma')
        self.assertEqual(procesar_recepciones(manual=True), 0)

    def test_xxe_and_bad_xml_never_access_external_resources(self):
        malicious = b'<!DOCTYPE ECF [<!ENTITY x SYSTEM "file:///etc/passwd">]><ECF>&x;</ECF>'
        for raw in (malicious, b'<ECF>', b'<eCF/>', b'x'*(1024*1024+1)):
            self.assertEqual(self.post_xml(raw).status_code, 400)
        self.assertFalse(RecepcionLocal.objects.exists())

    def test_api_requires_machine_token_loopback_and_correct_content_type(self):
        self.assertEqual(self.client.post('/api/recepciones/', self.xml(), content_type='application/xml').status_code, 401)
        self.assertEqual(self.client.post('/api/recepciones/', self.xml(), content_type='application/xml',
            REMOTE_ADDR='192.0.2.1', HTTP_AUTHORIZATION=f'Bearer {self.key}').status_code, 403)
        self.assertEqual(self.client.post('/api/recepciones/', '{}', content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.key}').status_code, 415)

    def test_separate_admin_setup_login_logout_and_csrf(self):
        response = self.client.get('/entidad/')
        self.assertRedirects(response, '/entidad/configurar/', fetch_redirect_response=False)
        self.assertEqual(self.setup_admin().status_code, 302)
        admin = AdministradorEntidad.objects.get()
        self.assertNotEqual(admin.password, 'Entidad!Pruebas-2026-segura')
        self.assertContains(self.client.get('/entidad/'), 'Padrón independiente')
        self.assertEqual(self.client.get('/entidad/logout/').status_code, 405)
        self.client.post('/entidad/logout/')
        self.assertRedirects(self.client.get('/entidad/'), '/entidad/login/', fetch_redirect_response=False)
        # Una sesión de facturación no concede administración a la entidad.
        session = self.client.session; session['frontend_identity'] = 'cualquier'; session.save()
        self.assertRedirects(self.client.get('/entidad/'), '/entidad/login/', fetch_redirect_response=False)
        secure = Client(enforce_csrf_checks=True)
        self.assertEqual(secure.post('/entidad/login/', {'usuario': 'autoridad','password':'x'}).status_code, 403)
        self.assertEqual(secure.get('/entidad/configurar/').status_code, 302)

    def test_admin_changes_are_audited_and_ranges_cannot_overlap(self):
        self.setup_admin()
        config = ConfiguracionEntidad.objects.get()
        self.client.post('/entidad/', {'escenario': 'normal', 'demora_segundos': 10})
        config.refresh_from_db(); self.assertFalse(config.automatico)
        self.assertTrue(AuditoriaEntidad.objects.filter(accion='configuracion_modificada').exists())
        r = RangoLocal.objects.filter(tipo='31').first()
        form = RangoForm({'emisor': r.emisor_id, 'tipo': '31', 'desde': 1, 'hasta': 10,
                          'vencimiento': '2028-12-31', 'activo': True})
        self.assertFalse(form.is_valid())
        self.assertIn('desde', form.errors)

    def test_authority_tables_only_exist_in_entity_database(self):
        from django.db import connections
        self.assertIn('dgii_mock_recepcionlocal', connections['entidad'].introspection.table_names())
        self.assertNotIn('dgii_mock_recepcionlocal', connections['default'].introspection.table_names())
        self.assertNotIn('frontend_data_clienteregistro', connections['entidad'].introspection.table_names())

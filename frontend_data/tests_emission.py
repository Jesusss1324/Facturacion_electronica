from datetime import timedelta
from hashlib import sha256
from unittest.mock import patch

from django.core.management import call_command
from django.db import transaction
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .emission import (procesar_pendientes, reclamar, recuperar_interrumpidas,
                       terminar_preparacion, xml_operacion)
from .models import ConfiguracionEmisor, FacturaRegistro, OperacionEmision, SecuenciaLocal
from .sqlite_repository import SQLiteRepository


@override_settings(FRONTEND_DATA_BACKEND='sqlite', DEBUG=True, FRONTEND_AUTH_ENABLED=True,
                   SESSION_ENGINE='django.contrib.sessions.backends.signed_cookies')
class OperacionesTests(TestCase):
    def test_server_startup_uses_recovery_command_and_starts_worker(self):
        from django.core.management import get_commands
        from django.contrib.staticfiles.management.commands.runserver import Command as BaseCommand
        from .management.commands.runserver import Command
        self.assertEqual(get_commands()['runserver'], 'frontend_data')
        _, _, _, op = self.reserve()
        with patch.object(BaseCommand, 'inner_run'), patch('threading.Thread') as thread:
            Command().inner_run()
        op.refresh_from_db()
        self.assertEqual(op.estado, 'preparada')
        thread.return_value.start.assert_called_once()

    def setUp(self):
        self.repo = SQLiteRepository()

    def draft(self, tipo='31'):
        from datetime import date
        from decimal import Decimal
        from uuid import uuid4
        from comprobantes.totales import huella_borrador
        from .entities import LineaFactura
        b = self.repo.create_borrador(tipo, 1 if tipo == '31' else 2)
        self.repo.update_borrador(b.id, fecha_emision=date(2026, 11, 4))
        self.repo.guardar_linea(b.id, LineaFactura(uuid4(), 'servicio', 'Gestión & soporte', '',
            'Servicio', Decimal('1'), Decimal('100'), Decimal('0')), 0)
        huella = huella_borrador(self.repo.get_borrador(b.id))
        self.repo.guardar_totales(b.id, huella, recalcular=True)
        return b, huella

    def reserve(self, tipo='31'):
        b, huella = self.draft(tipo)
        f = self.repo.emitir_factura(b.id, huella)
        return b, huella, f, OperacionEmision.objects.get(factura_id=f.id)

    def test_reservation_is_persistent_unique_and_not_approved(self):
        seq = SecuenciaLocal.objects.get(pk='31')
        siguiente = seq.siguiente
        b, h, factura, op = self.reserve()
        self.assertEqual(factura.e_ncf, f'E31{siguiente:010d}')
        self.assertEqual(factura.estado, 'generado')
        self.assertEqual(factura.track_id, '')
        self.assertEqual(self.repo.emitir_factura(b.id, h), factura)
        seq.refresh_from_db()
        self.assertEqual(seq.siguiente, siguiente + 1)
        self.assertEqual(OperacionEmision.objects.count(), 1)
        self.assertEqual(op.eventos.count(), 1)

    def test_each_type_has_an_independent_counter_and_advanced_counter_is_respected(self):
        SecuenciaLocal.objects.filter(pk='31').update(siguiente=4000)
        _, _, f31, _ = self.reserve('31')
        _, _, f32, op32 = self.reserve('32')
        self.assertEqual(f31.e_ncf, 'E310000004000')
        self.assertEqual(f32.e_ncf, f'E32{op32.numero:010d}')
        self.assertEqual(SecuenciaLocal.objects.get(pk='31').siguiente, 4001)

    def test_exhausted_disabled_expired_and_colliding_sequences_do_not_create_operation(self):
        b, h = self.draft()
        original = SecuenciaLocal.objects.get(pk='31').siguiente
        cases = ({'siguiente': 200, 'limite': 199}, {'activa': False},
                 {'vencimiento': timezone.localdate() - timedelta(days=1)}, {'siguiente': 128})
        for change in cases:
            with self.subTest(change=change):
                SecuenciaLocal.objects.filter(pk='31').update(siguiente=original,
                    limite=9999999999, activa=True, vencimiento=None)
                SecuenciaLocal.objects.filter(pk='31').update(**change)
                with self.assertRaises(ValueError):
                    self.repo.emitir_factura(b.id, h)
                self.assertFalse(OperacionEmision.objects.exists())
                self.assertEqual(FacturaRegistro.objects.count(), 128)

    def test_failure_after_reservation_rolls_back_counter_invoice_and_operation(self):
        b, h = self.draft()
        siguiente = SecuenciaLocal.objects.get(pk='31').siguiente
        with patch('frontend_data.emission.evento', side_effect=RuntimeError('cierre inesperado')):
            with self.assertRaises(RuntimeError):
                self.repo.emitir_factura(b.id, h)
        self.assertEqual(SecuenciaLocal.objects.get(pk='31').siguiente, siguiente)
        self.assertEqual(FacturaRegistro.objects.count(), 128)
        self.assertFalse(OperacionEmision.objects.exists())

    def test_document_uses_frozen_snapshot_and_remains_identical_after_configuration_changes(self):
        _, _, f, op = self.reserve()
        original = xml_operacion(op)
        self.repo.update_cliente(1, nombre='Nombre nuevo')
        config = ConfiguracionEmisor.objects.get(pk='principal')
        config.datos['razon_social'] = 'Otra razón social'
        config.save()
        self.assertEqual(procesar_pendientes(), 1)
        op.refresh_from_db()
        self.assertEqual(op.xml, original)
        self.assertEqual(op.xml_sha256, sha256(original.encode()).hexdigest())
        self.assertEqual(op.estado, 'preparada')
        self.assertEqual(procesar_pendientes(), 0)
        from comprobantes.views_xml import construir_xml_factura
        self.assertEqual(construir_xml_factura(f, self.repo.get_cliente(1)), original)

    def test_expired_worker_is_recovered_and_old_token_cannot_overwrite(self):
        _, _, _, op = self.reserve()
        old = reclamar(op.id)
        self.assertIsNone(reclamar(op.id))
        self.assertEqual(recuperar_interrumpidas(), 0)
        OperacionEmision.objects.filter(pk=op.id).update(bloqueo_hasta=timezone.now() - timedelta(seconds=1))
        self.assertEqual(recuperar_interrumpidas(), 1)
        new = reclamar(op.id)
        self.assertNotEqual(old.bloqueo_token, new.bloqueo_token)
        self.assertFalse(terminar_preparacion(op.id, old.bloqueo_token, xml='obsoleto'))
        self.assertTrue(terminar_preparacion(op.id, new.bloqueo_token, xml=xml_operacion(new)))
        self.assertEqual(FacturaRegistro.objects.count(), 129)

    def test_uncertain_send_is_never_automatically_prepared_or_resent(self):
        _, _, _, op = self.reserve()
        claimed = reclamar(op.id)
        OperacionEmision.objects.filter(pk=op.id).update(envio_iniciado=timezone.now(),
            bloqueo_hasta=timezone.now() - timedelta(seconds=1))
        self.assertEqual(procesar_pendientes(), 0)
        op.refresh_from_db()
        self.assertEqual(op.estado, 'consultar')
        self.assertIsNone(reclamar(op.id))
        self.assertFalse(terminar_preparacion(op.id, claimed.bloqueo_token, xml='tardío'))

    def test_local_error_is_persisted_with_backoff_and_same_identity(self):
        _, _, _, op = self.reserve()
        with patch('frontend_data.emission.xml_operacion', side_effect=ValueError('dato inválido')):
            self.assertEqual(procesar_pendientes(), 0)
        op.refresh_from_db()
        self.assertEqual(op.estado, 'pendiente')
        self.assertIn('dato inválido', op.ultimo_error)
        self.assertGreater(op.proximo_intento, timezone.now())
        self.assertEqual(procesar_pendientes(), 0)
        OperacionEmision.objects.filter(pk=op.id).update(proximo_intento=timezone.now())
        call_command('procesar_emisiones', verbosity=0)
        op.refresh_from_db()
        self.assertEqual(op.estado, 'preparada')
        self.assertEqual(op.intentos, 2)

    def test_processing_and_result_use_persisted_state_and_retry_requires_post_and_csrf(self):
        _, _, f, op = self.reserve()
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})
        url = reverse('comprobantes:procesamiento', kwargs={'pk': f.id})
        response = self.client.get(url + '?estado=completado')
        self.assertContains(response, 'Operación de emisión')
        self.assertNotContains(response, '¡Comprobante Timbrado y Aceptado!')
        self.assertRedirects(self.client.get(reverse('comprobantes:resultado', kwargs={'pk': f.id})),
            url, fetch_redirect_response=False)
        retry = reverse('comprobantes:reanudar_operacion', kwargs={'pk': f.id})
        self.assertEqual(self.client.get(retry).status_code, 405)
        self.assertEqual(self.client.post(retry).status_code, 302)
        state = self.client.get(reverse('comprobantes:estado_operacion', kwargs={'pk': f.id}))
        self.assertEqual(state.json()['estado'], 'preparada')
        self.assertEqual(state['Cache-Control'], 'no-store')
        from django.test import Client
        protected = Client(enforce_csrf_checks=True)
        protected.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})
        self.assertEqual(protected.post(retry).status_code, 403)

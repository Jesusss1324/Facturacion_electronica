from dataclasses import replace
from datetime import date
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from django.test import Client, SimpleTestCase, override_settings
from frontend_data import get_repository
from frontend_data.entities import LineaFactura
from frontend_data.repository import FrontendRepository
from .totales import huella_borrador


@override_settings(DEBUG=True, FRONTEND_AUTH_ENABLED=True, SESSION_ENGINE='django.contrib.sessions.backends.signed_cookies')
class TotalesTests(SimpleTestCase):
    def setUp(self):
        source = get_repository()
        self.repo = FrontendRepository(source.list_clientes(), source.list_facturas())
        patcher = patch('comprobantes.views_totales.get_repository', return_value=self.repo)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})
        self.draft = self.repo.create_borrador('31', 1)
        self.id = self.draft.id
        self.url = f'/facturas/borradores/{self.id}/totales/'
        lineas = tuple(LineaFactura(uuid4(), 'servicio', name, '', 'Unidad', Decimal(qty), Decimal(price), Decimal(discount)) for name, qty, price, discount in [('Consultoría', '2', '45000', '0'), ('Servidor', '1', '180000', '10000'), ('Licencia', '3', '8500', '0')])
        self.repo.update_borrador(self.id, fecha_emision=date(2026, 10, 1), lineas=lineas)

    def post(self, action, **extra):
        return self.client.post(self.url, {'accion': action, 'huella': huella_borrador(self.repo.get_borrador(self.id)), **extra})

    def test_reference_totals_and_get_does_not_save(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'RD$ 336,890.00')
        self.assertEqual(response.context['resumen']['itbis'], Decimal('51390.00'))
        self.assertEqual(response.context['resumen']['base'], Decimal('285500.00'))
        self.assertFalse(response.context['bloqueado'])
        self.assertIsNone(self.repo.get_borrador(self.id).totales_guardados)

    def test_save_and_continue_ignore_posted_amounts(self):
        self.assertRedirects(self.post('guardar', total='0', itbis='0'), self.url, fetch_redirect_response=False)
        draft = self.repo.get_borrador(self.id)
        self.assertEqual(dict(draft.totales_guardados)['total'], Decimal('336890.00'))
        self.assertIsNotNone(draft.fecha_guardado)
        self.assertRedirects(self.post('continuar'), f'/facturas/borradores/{self.id}/revision/', fetch_redirect_response=False)

    def test_inconsistent_saved_total_blocks_and_recalculates(self):
        self.post('guardar')
        draft = self.repo.get_borrador(self.id)
        totals = dict(draft.totales_guardados)
        totals['total'] += Decimal('250')
        self.repo.update_borrador(self.id, totales_guardados=tuple(totals.items()))
        response = self.client.get(self.url)
        self.assertTrue(response.context['bloqueado'])
        self.assertEqual(response.context['diferencia'], Decimal('250'))
        self.assertEqual(self.post('continuar').status_code, 409)
        self.assertEqual(self.post('guardar').status_code, 409)
        self.assertEqual(self.post('recalcular').status_code, 302)
        self.assertFalse(self.client.get(self.url).context['bloqueado'])

    def test_changed_lines_and_conditions_require_new_confirmation(self):
        self.post('guardar')
        self.repo.update_borrador(self.id, forma_pago='03')
        self.assertTrue(self.client.get(self.url).context['inconsistente'])
        self.post('recalcular')
        draft = self.repo.get_borrador(self.id)
        self.repo.guardar_linea(self.id, replace(draft.lineas[0], precio=Decimal('46000')), draft.revision_lineas, editar=True)
        self.assertTrue(self.client.get(self.url).context['inconsistente'])

    def test_stale_tab_blocked(self):
        old = huella_borrador(self.repo.get_borrador(self.id))
        self.repo.update_borrador(self.id, forma_pago='03')
        self.assertEqual(self.post('continuar', huella=old).status_code, 409)
        self.assertIsNone(self.repo.get_borrador(self.id).totales_guardados)

    def test_prerequisites_and_missing_draft(self):
        self.assertEqual(self.client.get(f'/facturas/borradores/{uuid4()}/totales/').status_code, 404)
        self.repo.update_borrador(self.id, lineas=())
        self.assertTrue(self.client.get(self.url).url.endswith('/items/'))
        self.repo.update_borrador(self.id, fecha_emision=None)
        self.assertTrue(self.client.get(self.url).url.endswith('/datos/'))
        self.repo.set_cliente_activo(1, False)
        self.assertTrue(self.post('continuar').url.endswith('/cliente/'))

    def test_invalid_credit_conditions_block(self):
        self.repo.update_borrador(self.id, tipo_pago='credito', fecha_vencimiento=None)
        self.assertTrue(self.client.get(self.url).context['bloqueado'])
        self.assertEqual(self.post('recalcular').status_code, 409)
        self.repo.update_borrador(self.id, fecha_vencimiento=date(2026, 10, 31))
        response = self.client.get(self.url)
        self.assertFalse(response.context['bloqueado'])
        self.assertContains(response, '31/10/2026')

    def test_auth_csrf_and_invalid_action(self):
        client = Client(enforce_csrf_checks=True)
        client.cookies = self.client.cookies
        self.assertEqual(client.post(self.url, {'accion': 'guardar'}).status_code, 403)
        self.assertEqual(self.post('otro').status_code, 400)
        self.client.logout()
        self.assertIn('/acceso/iniciar-sesion/', self.client.get(self.url).url)

    def test_text_is_escaped_in_modal(self):
        draft = self.repo.get_borrador(self.id)
        self.repo.update_borrador(self.id, lineas=(replace(draft.lineas[0], concepto='<script>alert(1)</script>'),))
        response = self.client.get(self.url)
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')

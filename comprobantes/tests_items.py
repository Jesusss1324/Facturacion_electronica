from datetime import date
from decimal import Decimal
from uuid import uuid4
from unittest.mock import patch

from django.test import Client, SimpleTestCase, override_settings
from frontend_data import get_repository
from frontend_data.repository import FrontendRepository
from .items import resumen_lineas


@override_settings(DEBUG=True, FRONTEND_AUTH_ENABLED=True, SESSION_ENGINE='django.contrib.sessions.backends.signed_cookies')
class BienesServiciosTests(SimpleTestCase):
    def setUp(self):
        source = get_repository()
        self.repo = FrontendRepository(source.list_clientes(), source.list_facturas())
        patcher = patch('comprobantes.views_items.get_repository', return_value=self.repo)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})
        self.draft = self.repo.create_borrador('31', 1)
        self.repo.update_borrador(self.draft.id, fecha_emision=date(2026, 10, 1))
        self.url = f'/facturas/borradores/{self.draft.id}/items/'
        self.data = {'accion': 'guardar', 'revision': '0', 'tipo': 'servicio', 'concepto': 'Consultoría tecnológica', 'descripcion': 'Informe de infraestructura', 'unidad': 'Hora', 'cantidad': '2', 'precio': '45000', 'descuento': '0'}

    def test_empty_and_editor_render(self):
        self.assertContains(self.client.get(self.url), 'Tu factura comienza aquí')
        self.assertContains(self.client.get(self.url + '?nuevo=1'), 'Agregar a la factura')
        self.assertEqual(self.client.post(self.url, {'accion': 'continuar'}).status_code, 200)
        self.assertEqual(len(self.repo.get_borrador(self.draft.id).lineas), 0)

    def test_add_edit_delete_and_totals(self):
        response = self.client.post(self.url, self.data)
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        linea = self.repo.get_borrador(self.draft.id).lineas[0]
        self.assertEqual(linea.total, Decimal('106200.00'))
        self.assertContains(self.client.get(self.url + f'?editar={linea.id}'), 'Editar concepto')
        response = self.client.post(self.url, {**self.data, 'linea_id': str(linea.id), 'revision': 1, 'precio': '180000', 'cantidad': '1', 'descuento': '10000'})
        updated = self.repo.get_borrador(self.draft.id).lineas[0]
        self.assertEqual(updated.total, Decimal('200600.00'))
        self.assertEqual(updated.itbis, Decimal('30600.00'))
        self.assertEqual(resumen_lineas((updated,))['base'], Decimal('170000.00'))
        self.assertRedirects(self.client.post(self.url, {'accion': 'continuar'}), f'/facturas/borradores/{self.draft.id}/totales/', fetch_redirect_response=False)
        self.client.post(self.url, {'accion': 'quitar', 'linea_id': str(linea.id), 'revision': 2})
        self.assertEqual(self.repo.get_borrador(self.draft.id).lineas, ())

    def test_preview_is_not_saved_and_escapes_html(self):
        response = self.client.post(self.url, {**self.data, 'accion': 'previsualizar', 'concepto': '<img src=x onerror=alert(1)>'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('RD$ 106,200.00', response.json()['html'])
        self.assertNotIn('<img src=x', response.json()['html'])
        self.assertIn('&lt;img', response.json()['html'])
        self.assertEqual(self.repo.get_borrador(self.draft.id).lineas, ())

    def test_invalid_numbers_and_choices(self):
        for field, value in [('cantidad', '0'), ('cantidad', '-1'), ('cantidad', '1.001'), ('precio', 'NaN'), ('precio', 'Infinity'), ('precio', '999999999999'), ('precio', "1; DROP TABLE"), ('descuento', '-1'), ('descuento', '90001'), ('tipo', 'otro'), ('concepto', '   ')]:
            with self.subTest(field=field, value=value):
                response = self.client.post(self.url, {**self.data, field: value})
                self.assertEqual(response.status_code, 200)
                self.assertIn(field, response.context['form'].errors)
        self.assertEqual(self.repo.get_borrador(self.draft.id).lineas, ())

    def test_rounding_and_discount_applied_before_tax(self):
        self.client.post(self.url, {**self.data, 'cantidad': '3', 'precio': '0.05', 'descuento': '0.01'})
        linea = self.repo.get_borrador(self.draft.id).lineas[0]
        self.assertEqual((linea.bruto, linea.base, linea.itbis, linea.total), (Decimal('.15'), Decimal('.14'), Decimal('.03'), Decimal('.17')))

    def test_revision_prevents_duplicate_submit_and_stale_updates(self):
        self.client.post(self.url, self.data)
        response = self.client.post(self.url, self.data)
        self.assertContains(response, 'El borrador cambió')
        draft = self.repo.get_borrador(self.draft.id)
        self.assertEqual(len(draft.lineas), 1)
        response = self.client.post(self.url, {'accion': 'quitar', 'revision': 0, 'linea_id': str(draft.lineas[0].id)})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(len(self.repo.get_borrador(self.draft.id).lineas), 1)

    def test_unknown_and_foreign_lines(self):
        self.assertEqual(self.client.get(self.url + '?editar=invalid').status_code, 404)
        self.assertEqual(self.client.post(self.url, {**self.data, 'linea_id': str(uuid4())}).status_code, 404)
        self.assertEqual(self.client.post(self.url, {**self.data, 'revision': 'abc'}).status_code, 400)
        self.assertEqual(self.client.post(self.url, {'accion': 'otro'}).status_code, 400)

    def test_prerequisites_and_authentication(self):
        self.repo.update_borrador(self.draft.id, fecha_emision=None)
        self.assertTrue(self.client.get(self.url).url.endswith('/datos/'))
        self.repo.set_cliente_activo(1, False)
        self.assertTrue(self.client.get(self.url).url.endswith('/cliente/'))
        self.client.logout()
        self.assertIn('/acceso/iniciar-sesion/', self.client.get(self.url).url)

    def test_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.cookies = self.client.cookies
        self.assertEqual(client.post(self.url, self.data).status_code, 403)

    def test_line_limit(self):
        for revision in range(100):
            self.client.post(self.url, {**self.data, 'revision': revision})
        response = self.client.post(self.url, {**self.data, 'revision': 100})
        self.assertContains(response, 'hasta 100 conceptos')
        self.assertEqual(len(self.repo.get_borrador(self.draft.id).lineas), 100)

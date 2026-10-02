from unittest.mock import patch
from django.test import SimpleTestCase, override_settings
from frontend_data import get_repository
from frontend_data.repository import FrontendRepository


@override_settings(DEBUG=True, FRONTEND_AUTH_ENABLED=True, SESSION_ENGINE='django.contrib.sessions.backends.signed_cookies')
class DetalleClienteTests(SimpleTestCase):
    def setUp(self):
        original = get_repository()
        self.repository = FrontendRepository(original.list_clientes(), original.list_facturas())
        patcher = patch('clientes.views.get_repository', return_value=self.repository)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})

    def test_customer_and_only_its_latest_invoices(self):
        response = self.client.get('/clientes/1/')
        self.assertContains(response, self.repository.get_cliente(1).nombre)
        invoices = response.context['facturas']
        self.assertTrue(invoices)
        self.assertLessEqual(len(invoices), 3)
        self.assertTrue(all(item.cliente_id == 1 for item in invoices))
        self.assertEqual(list(invoices), sorted(invoices, key=lambda item: (item.fecha_emision, item.id), reverse=True))
        self.assertContains(response, '/facturas/nueva/?cliente=1')

    def test_profile_shows_registration_date_and_ecf_types(self):
        response = self.client.get('/clientes/1/')
        cliente = self.repository.get_cliente(1)
        self.assertContains(response, 'Registrado el')
        self.assertContains(response, 'e-CF Receptor Certificado')
        tipos = self.repository.tipos_ecf_cliente(1)
        self.assertTrue(tipos)
        for tipo in tipos:
            self.assertContains(response, tipo)
        self.assertContains(response, 'Habilitado e-CF')
        self.assertContains(response, 'Fecha de alta en plataforma')

    def test_state_changes_return_to_detail_and_preserve_history(self):
        before = self.repository.recent_facturas_cliente(1)
        response = self.client.post('/clientes/1/estado/', {'activo': '0', 'volver': 'detalle'}, follow=True)
        self.assertEqual(response.redirect_chain, [('/clientes/1/', 302)])
        self.assertContains(response, 'Cliente temporalmente inactivo')
        self.assertNotContains(response, '/facturas/nueva/?cliente=1')
        self.assertEqual(before, self.repository.recent_facturas_cliente(1))
        response = self.client.post('/clientes/1/estado/', {'activo': '1', 'volver': 'detalle'}, follow=True)
        self.assertNotContains(response, 'Cliente temporalmente inactivo')
        self.assertContains(response, '/facturas/nueva/?cliente=1')

    def test_inactive_notice_shows_fiscal_text(self):
        self.repository.set_cliente_activo(1, False)
        response = self.client.get('/clientes/1/')
        self.assertContains(response, 'deshabilitado para emitir nuevas facturas')
        self.assertContains(response, 'trazabilidad histórica')
        self.assertContains(response, 'Deshabilitado para timbrado temporal')

    def test_dialog_shows_audit_note_for_inactivation(self):
        response = self.client.get('/clientes/1/')
        self.assertContains(response, 'Acción preventiva de seguridad fiscal')
        self.assertContains(response, 'Nota de auditoría')
        self.assertContains(response, 'no se borrarán ni alterarán')

    def test_empty_and_missing_contacts(self):
        customer = self.repository.create_cliente(nombre='Ana del Valle', identificacion='40278877857', tipo_identificacion='Cédula', telefono='', direccion='', email='')
        response = self.client.get(f'/clientes/{customer.id}/')
        self.assertContains(response, 'Este cliente todavía no tiene facturas registradas')
        self.assertContains(response, 'No registrado')
        self.assertContains(response, 'Crear primera factura')
        self.repository.set_cliente_activo(customer.id, False)
        self.assertNotContains(self.client.get(f'/clientes/{customer.id}/'), 'Crear primera factura')

    def test_missing_customer_and_private_access(self):
        self.assertEqual(self.client.get('/clientes/9999/').status_code, 404)
        self.assertEqual(self.client.post('/clientes/1/').status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.get('/clientes/1/').status_code, 302)

    def test_redirect_target_cannot_be_external(self):
        response = self.client.post('/clientes/1/estado/', {'activo': '0', 'volver': 'https://example.com/'})
        self.assertEqual(response.url, '/clientes/')

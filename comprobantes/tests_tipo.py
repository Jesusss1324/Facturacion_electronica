from unittest.mock import patch

from django.test import Client, SimpleTestCase, override_settings

from frontend_data import get_repository
from frontend_data.repository import FrontendRepository


@override_settings(DEBUG=True, FRONTEND_AUTH_ENABLED=True, SESSION_ENGINE='django.contrib.sessions.backends.signed_cookies')
class TipoComprobanteTests(SimpleTestCase):
    def setUp(self):
        original = get_repository()
        self.repository = FrontendRepository(original.list_clientes(), original.list_facturas())
        patcher = patch('comprobantes.views.get_repository', return_value=self.repository)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})

    def test_access_requires_login(self):
        self.client.logout()
        response = self.client.get('/facturas/nueva/tipo/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/acceso/iniciar-sesion/', response.url)

    def test_screen_renders_wizard_steps_and_cards(self):
        response = self.client.get('/facturas/nueva/tipo/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-current="step"')
        self.assertContains(response, 'Tipo')
        self.assertContains(response, 'Nueva factura electrónica')
        self.assertContains(response, 'Selecciona el tipo de comprobante fiscal electrónico')
        self.assertContains(response, 'Factura de Crédito Fiscal Electrónica')
        self.assertContains(response, 'Factura de Consumo Electrónica')
        self.assertContains(response, 'E31')
        self.assertContains(response, 'E32')
        self.assertContains(response, '¿No sabes cuál elegir? Guía rápida de selección')
        self.assertContains(response, 'Continuar al Paso 2: Cliente')
        self.assertNotContains(response, 'Simulador Docente')
        self.assertNotContains(response, 'Ambiente Didáctico')

    def test_preselected_client_is_preserved_and_displayed(self):
        cliente = self.repository.get_cliente(1)
        response = self.client.get(f'/facturas/nueva/tipo/?cliente={cliente.id}')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, cliente.nombre)
        self.assertContains(response, f'value="{cliente.id}"')
        self.assertContains(response, 'Cliente preseleccionado:')

    def test_preselected_cedula_client_defaults_to_e32(self):
        # Client 2 has Cédula type in fixtures
        cliente = self.repository.get_cliente(2)
        self.assertEqual(cliente.tipo_identificacion, 'Cédula')
        response = self.client.get(f'/facturas/nueva/tipo/?cliente={cliente.id}')
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertEqual(form.initial['tipo_ecf'], '32')

    def test_successful_post_creates_draft_and_advances_to_step_2(self):
        payload = {'tipo_ecf': '31'}
        response = self.client.post('/facturas/nueva/tipo/', payload)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/facturas/borradores/', response.url)
        self.assertIn('/cliente/', response.url)

        # Extract draft UUID from redirect URL
        parts = response.url.strip('/').split('/')
        # parts: ['facturas', 'borradores', '<uuid>', 'cliente']
        from uuid import UUID
        borrador_id = UUID(parts[2])
        borrador = self.repository.get_borrador(borrador_id)
        self.assertEqual(borrador.tipo_ecf, '31')
        self.assertIsNone(borrador.cliente_id)

    def test_successful_post_with_client_preserves_client_in_draft_and_url(self):
        cliente = self.repository.get_cliente(1)
        payload = {'tipo_ecf': '31', 'cliente': str(cliente.id)}
        response = self.client.post('/facturas/nueva/tipo/', payload)
        self.assertEqual(response.status_code, 302)
        self.assertIn(f'?cliente={cliente.id}', response.url)

        parts = response.url.split('?')[0].strip('/').split('/')
        from uuid import UUID
        borrador_id = UUID(parts[2])
        borrador = self.repository.get_borrador(borrador_id)
        self.assertEqual(borrador.tipo_ecf, '31')
        self.assertEqual(borrador.cliente_id, cliente.id)

    def test_invalid_type_rejected(self):
        response = self.client.post('/facturas/nueva/tipo/', {'tipo_ecf': '99'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Selecciona un tipo de comprobante')

    def test_inactive_client_rejected(self):
        # Client 43 is inactive in fixtures
        self.assertFalse(self.repository.get_cliente(43).activo)
        response = self.client.post('/facturas/nueva/tipo/', {'tipo_ecf': '31', 'cliente': '43'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'El cliente seleccionado está inactivo')

    def test_csrf_protection_is_enforced(self):
        client = Client(enforce_csrf_checks=True)
        client.get('/acceso/iniciar-sesion/')
        client.post('/acceso/iniciar-sesion/', {
            'username': 'user',
            'password': '1234',
            'csrfmiddlewaretoken': client.cookies['csrftoken'].value,
        })
        response = client.post('/facturas/nueva/tipo/', {'tipo_ecf': '31'})
        self.assertEqual(response.status_code, 403)

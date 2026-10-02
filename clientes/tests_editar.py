from unittest.mock import patch

from django.test import Client, SimpleTestCase, override_settings

from frontend_data import get_repository
from frontend_data.repository import FrontendRepository


@override_settings(DEBUG=True, FRONTEND_AUTH_ENABLED=True, SESSION_ENGINE='django.contrib.sessions.backends.signed_cookies')
class EditarClienteTests(SimpleTestCase):
    def setUp(self):
        original = get_repository()
        self.repository = FrontendRepository(original.list_clientes(), original.list_facturas())
        patcher = patch('clientes.views.get_repository', return_value=self.repository)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})

    def test_access_requires_login(self):
        self.client.logout()
        response = self.client.get('/clientes/1/editar/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/acceso/iniciar-sesion/', response.url)

    def test_missing_client_returns_404(self):
        response = self.client.get('/clientes/9999/editar/')
        self.assertEqual(response.status_code, 404)

    def test_initial_data_prepopulated_in_form(self):
        cliente = self.repository.get_cliente(1)
        response = self.client.get('/clientes/1/editar/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, cliente.nombre)
        self.assertContains(response, cliente.identificacion_display)
        self.assertContains(response, 'Identificación Tributaria y Régimen e-CF')
        self.assertContains(response, 'Información General y Entrega e-CF')
        self.assertContains(response, 'Estado Operativo en el Sistema')
        self.assertContains(response, 'Guardar cambios')

    def test_successful_update_redirects_to_detail_with_message(self):
        payload = {
            'tipo_identificacion': 'RNC',
            'identificacion': '1-01-00000-1',
            'nombre': 'Comercial Nova Caribe Actualizada, SRL',
            'email': 'nuevo_contacto@novacaribe.com.do',
            'telefono': '809-555-9988',
            'direccion': 'Av. Principal 123, Ensanche Naco, Santo Domingo',
            'activo': '1',
        }
        response = self.client.post('/clientes/1/editar/', payload, follow=True)
        self.assertEqual(response.redirect_chain, [('/clientes/1/', 302)])
        self.assertContains(response, 'Comercial Nova Caribe Actualizada, SRL')
        self.assertContains(response, '¡Cambios guardados!')

        actualizado = self.repository.get_cliente(1)
        self.assertEqual(actualizado.nombre, 'Comercial Nova Caribe Actualizada, SRL')
        self.assertEqual(actualizado.email, 'nuevo_contacto@novacaribe.com.do')
        self.assertEqual(actualizado.telefono, '809-555-9988')
        self.assertEqual(actualizado.direccion, 'Av. Principal 123, Ensanche Naco, Santo Domingo')
        self.assertTrue(actualizado.activo)

    def test_keeping_own_identification_does_not_trigger_duplicate_error(self):
        cliente = self.repository.get_cliente(1)
        payload = {
            'tipo_identificacion': 'RNC',
            'identificacion': cliente.identificacion,
            'nombre': 'Nombre Modificado Solamente',
            'email': cliente.email,
            'telefono': cliente.telefono,
            'direccion': cliente.direccion,
            'activo': '1',
        }
        response = self.client.post('/clientes/1/editar/', payload, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain, [('/clientes/1/', 302)])
        self.assertEqual(self.repository.get_cliente(1).nombre, 'Nombre Modificado Solamente')

    def test_duplicate_identification_with_another_client_is_rejected(self):
        cliente3 = self.repository.get_cliente(3)
        payload = {
            'tipo_identificacion': 'RNC',
            'identificacion': cliente3.identificacion,  # ID belonging to client 3 (RNC)
            'nombre': 'Intento de Duplicado',
            'email': 'test@example.com',
            'telefono': '809-555-1234',
            'direccion': 'Calle Test',
            'activo': '1',
        }
        response = self.client.post('/clientes/1/editar/', payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Esta identificación ya pertenece a otro cliente registrado.')
        # Client 1 was not modified
        self.assertNotEqual(self.repository.get_cliente(1).nombre, 'Intento de Duplicado')

    def test_status_change_to_inactive_updates_repository(self):
        payload = {
            'tipo_identificacion': 'RNC',
            'identificacion': '1-01-00000-1',
            'nombre': 'Comercial Nova Caribe, SRL',
            'email': 'contacto@test.com',
            'telefono': '809-555-1001',
            'direccion': 'Calle 1',
            'activo': '0',
        }
        response = self.client.post('/clientes/1/editar/', payload, follow=True)
        self.assertEqual(response.redirect_chain, [('/clientes/1/', 302)])
        self.assertFalse(self.repository.get_cliente(1).activo)
        self.assertContains(response, 'Cliente temporalmente inactivo')

    def test_validation_errors_preserve_submitted_data(self):
        payload = {
            'tipo_identificacion': 'RNC',
            'identificacion': '123',  # Invalid short RNC
            'nombre': 'Nombre Que Debe Preservarse',
            'email': 'email-invalido',
            'telefono': 'telefono-letras',
            'direccion': 'Direccion Test',
            'activo': '1',
        }
        response = self.client.post('/clientes/1/editar/', payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nombre Que Debe Preservarse')
        self.assertContains(response, 'La identificación debe contener 9 dígitos.')
        self.assertContains(response, 'Ingresa un correo electrónico válido.')
        self.assertContains(response, 'Ingresa sólo los 10 números del teléfono.')

    def test_csrf_protection_is_enforced(self):
        client = Client(enforce_csrf_checks=True)
        client.get('/acceso/iniciar-sesion/')
        client.post('/acceso/iniciar-sesion/', {
            'username': 'user',
            'password': '1234',
            'csrfmiddlewaretoken': client.cookies['csrftoken'].value,
        })
        # POST without token should be 403 Forbidden
        response = client.post('/clientes/1/editar/', {'nombre': 'Hacker'})
        self.assertEqual(response.status_code, 403)

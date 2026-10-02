from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from frontend_data import get_repository
from frontend_data.repository import FrontendRepository


@override_settings(DEBUG=True, FRONTEND_AUTH_ENABLED=True, SESSION_ENGINE='django.contrib.sessions.backends.signed_cookies')
class CrearClienteTests(SimpleTestCase):
    def setUp(self):
        original = get_repository()
        self.repository = FrontendRepository(original.list_clientes(), original.list_facturas())
        patcher = patch('clientes.views.get_repository', return_value=self.repository)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})
        self.data = {'tipo_identificacion': 'RNC', 'identificacion': '1-31-23456-7', 'nombre': 'Servicios del Atlántico, SRL', 'telefono': '(809) 555-1234', 'email': 'contacto@example.com', 'direccion': 'Calle Central 24'}

    def test_form_and_required_errors_preserve_values(self):
        self.assertContains(self.client.get('/clientes/nuevo/'), 'Ficha de contribuyente')
        response = self.client.post('/clientes/nuevo/', {'email': 'incorrecto', 'direccion': 'Calle Central'})
        self.assertEqual(set(response.context['form'].errors), {'tipo_identificacion', 'identificacion', 'nombre', 'email'})
        self.assertContains(response, 'Calle Central')
        self.assertEqual(len(self.repository.list_clientes()), 44)

    def test_create_and_search_without_database(self):
        response = self.client.post('/clientes/nuevo/', self.data)
        self.assertRedirects(response, '/clientes/', fetch_redirect_response=False)
        customer = self.repository.find_cliente_by_identificacion('131234567')
        self.assertTrue(customer.activo)
        self.assertEqual(customer.nombre, self.data['nombre'])
        self.assertEqual(customer.telefono, '809-555-1234')
        self.assertContains(self.client.get(response.url), self.data['nombre'])
        self.assertEqual(self.repository.resumen_inicio().clientes_activos, 43)

    def test_personal_and_optional_fields(self):
        data = {'tipo_identificacion': 'CEDULA', 'identificacion': '001-2345678-9', 'nombre': 'Ana del Valle'}
        self.assertEqual(self.client.post('/clientes/nuevo/', data).status_code, 302)
        self.assertEqual(self.repository.find_cliente_by_identificacion('00123456789').email, '')

    def test_duplicate_normalization_including_inactive(self):
        existing = self.repository.get_cliente(1)
        self.repository.set_cliente_activo(1, False)
        response = self.client.post('/clientes/nuevo/', {**self.data, 'identificacion': existing.identificacion_display})
        self.assertContains(response, 'Contribuyente ya registrado')
        self.assertContains(response, 'Ver cliente existente')
        self.assertEqual(response.context['form'].duplicate.id, 1)
        self.assertEqual(len(self.repository.list_clientes()), 44)

    def test_invalid_format_and_contact(self):
        for changes, field in [({'identificacion': '123'}, 'identificacion'), ({'identificacion': 'a31234567'}, 'identificacion'), ({'tipo_identificacion': 'CEDULA'}, 'identificacion'), ({'telefono': '123'}, 'telefono'), ({'email': 'incorrecto'}, 'email')]:
            with self.subTest(changes=changes):
                response = self.client.post('/clientes/nuevo/', {**self.data, **changes})
                self.assertIn(field, response.context['form'].errors)

    def test_repeated_submissions_do_not_duplicate(self):
        self.client.post('/clientes/nuevo/', self.data)
        self.assertContains(self.client.post('/clientes/nuevo/', self.data), 'Contribuyente ya registrado')
        self.assertEqual(len(self.repository.list_clientes()), 45)

    def test_numeric_fields_reject_letters_and_sql_payloads(self):
        for field, value in [('identificacion', "131234567' OR 1=1--"), ('telefono', '809abc5551044'), ('telefono', '18095551044')]:
            response = self.client.post('/clientes/nuevo/', {**self.data, field: value})
            self.assertIn(field, response.context['form'].errors)
        self.assertEqual(len(self.repository.list_clientes()), 44)

    def test_text_is_normalized_and_html_is_escaped(self):
        name = "  O'Brien   <script>alert(1)</script>  "
        response = self.client.post('/clientes/nuevo/', {**self.data, 'nombre': name})
        self.assertEqual(response.url, '/clientes/')
        customer = self.repository.find_cliente_by_identificacion('131234567')
        self.assertEqual(customer.nombre, "O'Brien <script>alert(1)</script>")
        response = self.client.get('/clientes/', {'q': '131234567'})
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')

    def test_control_characters_rejected(self):
        response = self.client.post('/clientes/nuevo/', {**self.data, 'nombre': 'Empresa\u200bOculta'})
        self.assertIn('nombre', response.context['form'].errors)

    def test_repository_serializes_concurrent_creates(self):
        data = {**self.data, 'identificacion': '131234567'}
        def create(_):
            try:
                return self.repository.create_cliente(**data).id
            except ValueError:
                return None
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(create, range(2)))
        self.assertEqual(sum(result is not None for result in results), 1)

    def test_access_and_csrf(self):
        self.client.logout()
        self.assertEqual(self.client.get('/clientes/nuevo/').status_code, 302)
        from django.test import Client
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.cookies = self.client.cookies
        self.assertEqual(csrf_client.post('/clientes/nuevo/', self.data).status_code, 403)

from unittest.mock import patch

from django.test import Client, SimpleTestCase, override_settings

from frontend_data import get_repository
from frontend_data.repository import FrontendRepository


@override_settings(DEBUG=True, FRONTEND_AUTH_ENABLED=True, SESSION_ENGINE='django.contrib.sessions.backends.signed_cookies')
class DirectorioClientesTests(SimpleTestCase):
    def setUp(self):
        original = get_repository()
        self.repository = FrontendRepository(original.list_clientes(), original.list_facturas())
        for target in ['clientes.views.get_repository', 'core.views.get_repository']:
            patcher = patch(target, return_value=self.repository)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})

    def test_directory_paginates_and_counts_without_database(self):
        response = self.client.get('/clientes/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['page_obj']), 6)
        self.assertEqual(response.context['page_obj'].paginator.count, 44)
        self.assertEqual([filtro['count'] for filtro in response.context['filtros']], [44, 42, 2])
        self.assertContains(response, 'Comercial Nova Caribe, SRL')

    def test_search_ignores_accents_and_identification_punctuation(self):
        for query, expected in [('Juan Perez', 2), ('1-01-00000-1', 1), ('00123450022', 2)]:
            with self.subTest(query=query):
                response = self.client.get('/clientes/', {'q': query})
                self.assertEqual([cliente.id for cliente in response.context['page_obj']], [expected])

    def test_invoice_entry_preserves_selected_client(self):
        response = self.client.get('/facturas/nueva/?cliente=2')
        self.assertRedirects(response, '/facturas/nueva/tipo/?cliente=2', fetch_redirect_response=False)

    def test_filters_and_pagination_preserve_search(self):
        response = self.client.get('/clientes/', {'q': 'SRL', 'estado': 'activos', 'page': 2})
        self.assertEqual(response.context['page_obj'].number, 2)
        self.assertTrue(all(cliente.activo for cliente in response.context['page_obj']))
        self.assertIn('q=SRL', response.context['previous_url'])
        self.assertIn('estado=activos', response.context['previous_url'])
        inactive = self.client.get('/clientes/', {'estado': 'inactivos'})
        self.assertEqual(len(inactive.context['page_obj']), 2)
        self.assertNotContains(inactive, '> Crear factura ')

    def test_no_results_and_empty_directory_are_different(self):
        self.assertContains(self.client.get('/clientes/', {'q': 'sin-coincidencias-xyz'}), 'No se encontraron clientes')
        with patch('clientes.views.get_repository', return_value=FrontendRepository()):
            response = self.client.get('/clientes/')
            self.assertContains(response, 'No hay clientes registrados todavía')
            self.assertContains(response, 'Registrar primer cliente')

    def test_invalid_page_and_filter_are_handled(self):
        response = self.client.get('/clientes/', {'page': 'texto', 'estado': 'otro'})
        self.assertEqual(response.context['page_obj'].number, 1)
        self.assertEqual(response.context['estado'], 'todos')
        self.assertEqual(self.client.get('/clientes/', {'page': 999}).context['page_obj'].number, 8)

    def test_inactivate_and_reactivate_update_shared_data_only(self):
        response = self.client.post('/clientes/1/estado/', {'activo': '0', 'q': 'Nova', 'estado': 'activos'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.repository.get_cliente(1).activo)
        self.assertEqual(self.repository.resumen_inicio().clientes_activos, 41)
        self.assertContains(response, 'inactivado para nuevos e-CF')
        self.assertEqual(self.client.get('/inicio/').context['resumen'].clientes_activos, 41)
        self.client.post('/clientes/1/estado/', {'activo': '1'})
        self.assertTrue(self.repository.get_cliente(1).activo)
        self.assertEqual(len(self.repository.list_facturas()), 128)

    def test_state_changes_validate_method_id_and_value(self):
        self.assertEqual(self.client.get('/clientes/1/estado/').status_code, 405)
        self.assertEqual(self.client.post('/clientes/1/estado/', {'activo': 'otro'}).status_code, 400)
        self.assertEqual(self.client.post('/clientes/999/estado/', {'activo': '0'}).status_code, 404)

    def test_csrf_and_private_access_are_enforced(self):
        anonymous = Client()
        self.assertEqual(anonymous.get('/clientes/').status_code, 302)
        self.assertEqual(anonymous.post('/clientes/1/estado/', {'activo': '0'}).status_code, 302)
        guarded = Client(enforce_csrf_checks=True)
        guarded.get('/acceso/iniciar-sesion/')
        guarded.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234', 'csrfmiddlewaretoken': guarded.cookies['csrftoken'].value})
        self.assertEqual(guarded.post('/clientes/1/estado/', {'activo': '0'}).status_code, 403)

    def test_search_is_escaped_and_simulator_controls_are_absent(self):
        response = self.client.get('/clientes/', {'q': '<script>alert(1)</script>'})
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertNotContains(response, 'Simulador')
        self.assertNotContains(response, 'Académico')

import uuid
from unittest.mock import patch

from django.test import Client, SimpleTestCase, override_settings

from frontend_data import get_repository
from frontend_data.repository import FrontendRepository


@override_settings(DEBUG=True, FRONTEND_AUTH_ENABLED=True, SESSION_ENGINE='django.contrib.sessions.backends.signed_cookies')
class SeleccionarClienteTests(SimpleTestCase):
    def setUp(self):
        original = get_repository()
        self.repository = FrontendRepository(original.list_clientes(), original.list_facturas())
        patcher = patch('comprobantes.views.get_repository', return_value=self.repository)
        patcher.start()
        self.addCleanup(patcher.stop)

        # Authenticate user
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})

        # Create test drafts
        self.borrador_e31 = self.repository.create_borrador(tipo_ecf='31')
        self.url_e31 = f'/facturas/borradores/{self.borrador_e31.id}/cliente/'

        self.borrador_e32 = self.repository.create_borrador(tipo_ecf='32')
        self.url_e32 = f'/facturas/borradores/{self.borrador_e32.id}/cliente/'

    def test_access_requires_login(self):
        self.client.logout()
        response = self.client.get(self.url_e31)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/acceso/iniciar-sesion/', response.url)

    def test_nonexistent_draft_returns_404(self):
        fake_id = uuid.uuid4()
        response = self.client.get(f'/facturas/borradores/{fake_id}/cliente/')
        self.assertEqual(response.status_code, 404)

    def test_screen_renders_wizard_steps_and_layout(self):
        response = self.client.get(self.url_e31)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'PASO 2')
        self.assertContains(response, 'RECEPTOR FISCAL')
        self.assertContains(response, 'Selecciona un cliente receptor')
        self.assertContains(response, 'Ficha del Receptor')
        self.assertContains(response, 'Continuar al Paso 3: Datos Emisión')
        self.assertContains(response, 'Registrar Cliente Receptor Rápido')
        self.assertContains(response, 'Consultar DGII')
        self.assertContains(response, 'Nuevo')
        # Redundant success banner removed
        self.assertNotContains(response, 'Cliente seleccionado exitosamente')
        self.assertNotContains(response, 'Simulador Docente')
        self.assertNotContains(response, 'Ambiente Didáctico')
        self.assertNotContains(response, 'Modulador docente')

    def test_automatic_fiscal_filtering_for_e31_shows_only_rnc(self):
        response = self.client.get(self.url_e31)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Empresas y Contribuyentes (RNC)')
        clientes = response.context['clientes']
        self.assertTrue(all(c.tipo_identificacion == 'RNC' for c in clientes))
        self.assertGreater(len(clientes), 0)
        # Ensure no Cédula personas are included in E31
        self.assertFalse(any(c.tipo_identificacion in {'CEDULA', 'Cédula'} for c in clientes))
        # Compliance text for E31 includes crédito deducible
        self.assertContains(response, 'crédito deducible')

    def test_automatic_fiscal_filtering_for_e32_shows_only_cedula(self):
        response = self.client.get(self.url_e32)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Personas Físicas (Cédula)')
        clientes = response.context['clientes']
        self.assertTrue(all(c.tipo_identificacion in {'CEDULA', 'Cédula'} for c in clientes))
        self.assertGreater(len(clientes), 0)
        # Ensure no RNC companies are included in E32
        self.assertFalse(any(c.tipo_identificacion == 'RNC' for c in clientes))
        # Compliance text for E32 does not promise crédito deducible
        self.assertNotContains(response, 'crédito deducible')
        self.assertContains(response, 'Consumidor final')

    def test_pagination_of_client_cards(self):
        response = self.client.get(self.url_e31)
        self.assertEqual(response.status_code, 200)
        page_obj = response.context['page_obj']
        # Max 6 cards per page
        self.assertLessEqual(len(page_obj.object_list), 6)
        self.assertGreater(page_obj.paginator.num_pages, 1)
        self.assertContains(response, 'aria-label="Páginas de clientes receptores"')

        # Navigate to page 2
        response_p2 = self.client.get(f'{self.url_e31}?page=2')
        self.assertEqual(response_p2.status_code, 200)
        self.assertEqual(response_p2.context['page_obj'].number, 2)

    def test_search_by_name_and_rnc_in_e31(self):
        # Client 1 is an active RNC client
        cliente = self.repository.get_cliente(1)
        search_term = cliente.nombre.split()[1] if len(cliente.nombre.split()) > 1 else cliente.nombre
        response = self.client.get(f'{self.url_e31}?q={search_term}')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, cliente.nombre)

        # Search by raw RNC without dashes
        response = self.client.get(f'{self.url_e31}?q={cliente.identificacion}')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, cliente.nombre)

    def test_preselected_client_from_url_parameter(self):
        cliente = self.repository.get_cliente(1)
        response = self.client.get(f'{self.url_e31}?cliente={cliente.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['cliente_seleccionado'].id, cliente.id)
        self.assertContains(response, cliente.nombre)
        self.assertContains(response, cliente.identificacion_display)

    def test_advance_with_active_client_updates_draft_and_redirects(self):
        cliente = self.repository.get_cliente(1)
        self.assertTrue(cliente.activo)
        self.assertEqual(cliente.tipo_identificacion, 'RNC')

        response = self.client.post(self.url_e31, {'cliente_id': str(cliente.id)})
        self.assertEqual(response.status_code, 302)
        expected_url = f'/facturas/borradores/{self.borrador_e31.id}/datos/'
        self.assertEqual(response.url, expected_url)

        borrador = self.repository.get_borrador(self.borrador_e31.id)
        self.assertEqual(borrador.cliente_id, cliente.id)

    def test_advance_with_incompatible_fiscal_type_rejected(self):
        # Client 2 has Cédula
        cliente_cedula = self.repository.get_cliente(2)
        self.assertEqual(cliente_cedula.tipo_identificacion, 'Cédula')

        # Submitting Cédula for E31 (Crédito Fiscal) must be rejected
        response = self.client.post(self.url_e31, {'cliente_id': str(cliente_cedula.id)})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Incompatibilidad fiscal')
        self.assertContains(response, 'debe poseer RNC habilitado')

        # Client 1 has RNC
        cliente_rnc = self.repository.get_cliente(1)
        self.assertEqual(cliente_rnc.tipo_identificacion, 'RNC')

        # Submitting RNC for E32 (Consumidor Final) must be rejected
        response = self.client.post(self.url_e32, {'cliente_id': str(cliente_rnc.id)})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Incompatibilidad fiscal')
        self.assertContains(response, 'debe ser una persona física (Cédula)')

    def test_advance_with_inactive_client_rejected(self):
        # Client 43 is inactive RNC
        cliente_inactivo = self.repository.get_cliente(43)
        self.assertFalse(cliente_inactivo.activo)

        response = self.client.post(self.url_e31, {'cliente_id': str(cliente_inactivo.id)})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Restricción Fiscal DGII')
        self.assertContains(response, 'inactivo')

        borrador = self.repository.get_borrador(self.borrador_e31.id)
        self.assertIsNone(borrador.cliente_id)

    def test_advance_without_client_rejected(self):
        response = self.client.post(self.url_e31, {'cliente_id': ''})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Debes seleccionar un cliente receptor')

    def test_advance_with_invalid_client_id_rejected(self):
        response = self.client.post(self.url_e31, {'cliente_id': '99999'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'El cliente seleccionado no existe')

    def test_modal_quick_client_creation_valid_for_e31(self):
        modal_payload = {
            'accion': 'crear_cliente',
            'tipo_identificacion': 'RNC',
            'identificacion': '1-32-99881-2',
            'nombre': 'Constructora Moderna SRL',
            'telefono': '809-555-7788',
            'email': 'contabilidad@moderna.do',
            'direccion': 'Av. Winston Churchill #105, Piantini',
        }
        response = self.client.post(self.url_e31, modal_payload)
        self.assertEqual(response.status_code, 302)

        nuevo = self.repository.find_cliente_by_identificacion('132998812')
        self.assertIsNotNone(nuevo)
        self.assertEqual(nuevo.nombre, 'Constructora Moderna SRL')
        self.assertEqual(nuevo.tipo_identificacion, 'RNC')

        borrador = self.repository.get_borrador(self.borrador_e31.id)
        self.assertEqual(borrador.cliente_id, nuevo.id)

    def test_modal_quick_client_creation_valid_for_e32(self):
        modal_payload = {
            'accion': 'crear_cliente',
            'tipo_identificacion': 'CEDULA',
            'identificacion': '402-9988776-5',
            'nombre': 'Guillermo Valdez Peña',
            'telefono': '809-555-3344',
            'email': 'gvaldez@correo.do',
            'direccion': 'Calle del Sol #45, Santiago',
        }
        response = self.client.post(self.url_e32, modal_payload)
        self.assertEqual(response.status_code, 302)

        nuevo = self.repository.find_cliente_by_identificacion('40299887765')
        self.assertIsNotNone(nuevo)
        self.assertEqual(nuevo.nombre, 'Guillermo Valdez Peña')
        self.assertEqual(nuevo.tipo_identificacion, 'Cédula')

        borrador = self.repository.get_borrador(self.borrador_e32.id)
        self.assertEqual(borrador.cliente_id, nuevo.id)

    def test_modal_quick_client_creation_incompatible_type_rejected(self):
        # Attempting to create Cédula in E31
        modal_payload = {
            'accion': 'crear_cliente',
            'tipo_identificacion': 'CEDULA',
            'identificacion': '402-1122334-5',
            'nombre': 'Persona en E31 Inválida',
        }
        response = self.client.post(self.url_e31, modal_payload)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['abrir_modal'])
        self.assertContains(response, 'debe poseer RNC')

    def test_modal_quick_client_creation_duplicate_rejected(self):
        cliente1 = self.repository.get_cliente(1)
        modal_payload = {
            'accion': 'crear_cliente',
            'tipo_identificacion': 'RNC',
            'identificacion': cliente1.identificacion,
            'nombre': 'Otro Nombre Repetido',
        }
        response = self.client.post(self.url_e31, modal_payload)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['abrir_modal'])
        self.assertContains(response, 'Esta identificación ya pertenece a un cliente registrado')

    def test_csrf_protection_is_enforced(self):
        client = Client(enforce_csrf_checks=True)
        client.get('/acceso/iniciar-sesion/')
        client.post('/acceso/iniciar-sesion/', {
            'username': 'user',
            'password': '1234',
            'csrfmiddlewaretoken': client.cookies['csrftoken'].value,
        })
        response = client.post(self.url_e31, {'cliente_id': '1'})
        self.assertEqual(response.status_code, 403)

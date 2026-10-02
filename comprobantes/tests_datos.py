from datetime import timedelta
from unittest.mock import patch
import uuid

from django.test import Client, SimpleTestCase, override_settings
from django.utils import timezone

from frontend_data import get_repository
from frontend_data.repository import FrontendRepository


@override_settings(DEBUG=True, FRONTEND_AUTH_ENABLED=True, SESSION_ENGINE='django.contrib.sessions.backends.signed_cookies')
class DatosGeneralesTests(SimpleTestCase):
    def setUp(self):
        original = get_repository()
        self.repository = FrontendRepository(original.list_clientes(), original.list_facturas())
        patcher = patch('comprobantes.views.get_repository', return_value=self.repository)
        patcher.start()
        self.addCleanup(patcher.stop)

        # Authenticate user
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})

        # Setup standard client and draft
        self.cliente = self.repository.get_cliente(1)
        self.borrador = self.repository.create_borrador(tipo_ecf='31', cliente_id=self.cliente.id)
        self.url = f'/facturas/borradores/{self.borrador.id}/datos/'

    def test_access_requires_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/acceso/iniciar-sesion/', response.url)

    def test_nonexistent_draft_returns_404(self):
        fake_id = uuid.uuid4()
        response = self.client.get(f'/facturas/borradores/{fake_id}/datos/')
        self.assertEqual(response.status_code, 404)

    def test_draft_without_client_redirects_to_step_2(self):
        borrador_sin_cliente = self.repository.create_borrador(tipo_ecf='31')
        url_sin_cliente = f'/facturas/borradores/{borrador_sin_cliente.id}/datos/'
        response = self.client.get(url_sin_cliente)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            f'/facturas/borradores/{borrador_sin_cliente.id}/cliente/'
        )

    def test_screen_renders_wizard_steps_and_layout(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        # Wizard stepper
        self.assertContains(response, 'aria-current="step"')
        self.assertContains(response, 'Datos generales')

        # Top context cards
        self.assertContains(response, 'E31')
        self.assertContains(response, 'Factura de Crédito Fiscal Electrónica')
        self.assertContains(response, self.cliente.nombre)
        self.assertContains(response, self.cliente.tipo_identificacion)
        self.assertContains(response, 'Cambiar')

        # Page Title & Header
        self.assertContains(response, 'Datos generales de la factura')
        self.assertContains(response, 'Paso 3 de 6 · Clasificación Comercial y Fiscal')

        # Section 1: Información técnica
        self.assertContains(response, 'Información técnica del comprobante')
        self.assertContains(response, 'E31 — Factura de Crédito Fiscal Electrónica')
        self.assertContains(response, 'AUTO TIMBRADO')
        self.assertContains(response, 'id="id_fecha_emision"')

        # Section 2: Clasificación fiscal
        self.assertContains(response, 'Clasificación de la operación fiscal')
        self.assertContains(response, '01 — Ingresos por operaciones (No financieros)')
        self.assertContains(response, 'Nota de imputación fiscal')

        # Section 3: Condiciones y modalidad de pago
        self.assertContains(response, 'Condiciones y modalidad de pago')
        self.assertContains(response, 'Contado')
        self.assertContains(response, 'Crédito')
        self.assertContains(response, 'Gratuito')
        self.assertContains(response, 'Definición de vencimiento comercial')
        self.assertContains(response, 'Forma de pago principal')
        self.assertContains(response, '&lt;FormaPago&gt;')

        # Footer Actions
        self.assertContains(response, 'Volver al Paso 2 (Cliente)')
        self.assertContains(response, 'Continuar al Paso 4: Ítems y Servicios')

        # Strict checks against simulator / academic claims
        self.assertNotContains(response, 'Simulador Docente')
        self.assertNotContains(response, 'Ambiente Didáctico')
        self.assertNotContains(response, 'Modulador docente')
        self.assertNotContains(response, 'Simulador de Casos Fiscales')

    def test_change_type_modal_rendered_correctly(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="change-type-modal"')
        self.assertContains(response, '¿Cambiar tipo de comprobante?')
        self.assertContains(response, f'href="/facturas/nueva/tipo/?cliente={self.cliente.id}&tipo=31"')

    def test_post_contado_valid_updates_draft_and_redirects_to_items(self):
        hoy = timezone.localdate()
        payload = {
            'fecha_emision': hoy.strftime('%Y-%m-%d'),
            'tipo_ingreso': '01',
            'tipo_pago': 'contado',
            'forma_pago': '02',
        }
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            f'/facturas/borradores/{self.borrador.id}/items/'
        )

        borrador_actualizado = self.repository.get_borrador(self.borrador.id)
        self.assertEqual(borrador_actualizado.fecha_emision, hoy)
        self.assertEqual(borrador_actualizado.tipo_ingreso, '01')
        self.assertEqual(borrador_actualizado.tipo_pago, 'contado')
        self.assertEqual(borrador_actualizado.forma_pago, '02')
        self.assertIsNone(borrador_actualizado.fecha_vencimiento)

    def test_post_credito_valid_updates_draft_with_due_date(self):
        hoy = timezone.localdate()
        vencimiento = hoy + timedelta(days=30)
        payload = {
            'fecha_emision': hoy.strftime('%Y-%m-%d'),
            'tipo_ingreso': '01',
            'tipo_pago': 'credito',
            'termino_pago': '30_dias',
            'fecha_vencimiento': vencimiento.strftime('%Y-%m-%d'),
            'forma_pago': '04',
        }
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            f'/facturas/borradores/{self.borrador.id}/items/'
        )

        borrador_actualizado = self.repository.get_borrador(self.borrador.id)
        self.assertEqual(borrador_actualizado.tipo_pago, 'credito')
        self.assertEqual(borrador_actualizado.termino_pago, '30_dias')
        self.assertEqual(borrador_actualizado.fecha_vencimiento, vencimiento)
        self.assertEqual(borrador_actualizado.forma_pago, '04')

    def test_post_credito_missing_due_date_fails(self):
        hoy = timezone.localdate()
        payload = {
            'fecha_emision': hoy.strftime('%Y-%m-%d'),
            'tipo_ingreso': '01',
            'tipo_pago': 'credito',
            'termino_pago': '30_dias',
            'fecha_vencimiento': '',
            'forma_pago': '04',
        }
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Debes indicar la fecha límite de pago para ventas a crédito.')

    def test_post_credito_due_date_before_emision_fails(self):
        hoy = timezone.localdate()
        vencimiento_invalido = hoy - timedelta(days=5)
        payload = {
            'fecha_emision': hoy.strftime('%Y-%m-%d'),
            'tipo_ingreso': '01',
            'tipo_pago': 'credito',
            'termino_pago': '30_dias',
            'fecha_vencimiento': vencimiento_invalido.strftime('%Y-%m-%d'),
            'forma_pago': '04',
        }
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'La fecha límite debe ser igual o posterior a la fecha de emisión')

    def test_post_invalid_tipo_ingreso_fails(self):
        hoy = timezone.localdate()
        payload = {
            'fecha_emision': hoy.strftime('%Y-%m-%d'),
            'tipo_ingreso': '99',
            'tipo_pago': 'contado',
            'forma_pago': '02',
        }
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Debes seleccionar un tipo de ingreso válido según la DGII')

    def test_post_gratuito_valid_clears_expiry(self):
        hoy = timezone.localdate()
        payload = {
            'fecha_emision': hoy.strftime('%Y-%m-%d'),
            'tipo_ingreso': '06',
            'tipo_pago': 'gratuito',
            'forma_pago': '08',
        }
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, 302)
        borrador_actualizado = self.repository.get_borrador(self.borrador.id)
        self.assertEqual(borrador_actualizado.tipo_pago, 'gratuito')
        self.assertIsNone(borrador_actualizado.fecha_vencimiento)

    def test_csrf_protection_enforced(self):
        client = Client(enforce_csrf_checks=True)
        client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})
        response = client.post(self.url, {'tipo_pago': 'contado'})
        self.assertEqual(response.status_code, 403)

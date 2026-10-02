from datetime import date
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from django.test import SimpleTestCase, override_settings
from django.urls import reverse

from frontend_data import get_repository
from frontend_data.entities import LineaFactura
from frontend_data.repository import FrontendRepository
from .totales import huella_borrador


@override_settings(
    DEBUG=True,
    FRONTEND_AUTH_ENABLED=True,
    SESSION_ENGINE='django.contrib.sessions.backends.signed_cookies',
)
class DetalleFacturaTests(SimpleTestCase):
    def setUp(self):
        source = get_repository()
        self.repo = FrontendRepository(source.list_clientes(), source.list_facturas())
        patcher = patch('comprobantes.views_detalle.get_repository', return_value=self.repo)
        patcher.start()
        self.addCleanup(patcher.stop)

        # Factura existente de los fixtures (ej: id=1)
        self.factura = self.repo.get_factura(1)
        self.url = reverse('comprobantes:detalle', kwargs={'pk': self.factura.id})

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(
            response,
            f"{reverse('usuarios:login')}?next={self.url}",
            fetch_redirect_response=False,
        )

    def test_404_for_non_existent_invoice(self):
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})
        url_inexistente = reverse('comprobantes:detalle', kwargs={'pk': 99999})
        response = self.client.get(url_inexistente)
        self.assertEqual(response.status_code, 404)

    def test_render_aprobado_default(self):
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        # Emisor y Encabezado
        self.assertContains(response, 'SOLUCIONES TECNOLÓGICAS DEL CARIBE, SRL')
        self.assertContains(response, 'EMISOR AUTORIZADO E-CF')
        self.assertContains(response, '1-30-98765-4')
        self.assertContains(response, 'DGII · FACTURA ELECTRÓNICA')
        self.assertContains(response, '● APROBADO DGII')
        self.assertContains(response, self.factura.e_ncf)
        self.assertContains(response, f'data-encf="{self.factura.e_ncf}"')

        # Receptor
        cliente = self.repo.get_cliente(self.factura.cliente_id)
        self.assertContains(response, cliente.nombre)
        self.assertContains(response, cliente.identificacion_display)
        self.assertContains(response, 'CONDICIÓN DE PAGO:')

        # Tabla y totales
        self.assertContains(response, 'DESCRIPCIÓN DEL BIEN O SERVICIO')
        self.assertContains(response, 'TOTAL NETO')
        self.assertContains(response, 'CANTIDAD EN LETRAS')
        self.assertContains(response, 'VERIFICACIÓN FISCAL INMEDIATA')
        self.assertContains(response, 'LIQUIDACIÓN TRIBUTARIA DEL COMPROBANTE')
        self.assertContains(response, 'TOTAL FACTURA')

        # Acciones superiores
        self.assertContains(response, 'Volver al historial')
        self.assertContains(response, 'FACSIMIL TRIBUTARIO DIGITAL · LEY 32-23')
        self.assertContains(response, 'Imprimir Factura')
        self.assertContains(response, 'Ver XML Firmado')
        self.assertContains(response, 'Descargar PDF Oficial')

        # No debe mostrar alertas de rechazo ni anulación
        self.assertNotContains(response, 'RECHAZO FISCAL DGII')
        self.assertNotContains(response, 'COMPROBANTE FISCAL ANULADO')

    def test_render_rechazado_simulado(self):
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})
        url_rechazado = f'{self.url}?simular_estado=rechazado'
        response = self.client.get(url_rechazado)
        self.assertEqual(response.status_code, 200)

        # Banner y estado de rechazo
        self.assertContains(response, '● RECHAZADO DGII')
        self.assertContains(response, 'RECHAZO FISCAL DGII')
        self.assertContains(response, 'Ver XML Rechazado')
        self.assertNotContains(response, 'COMPROBANTE FISCAL ANULADO')

    def test_render_anulado_simulado(self):
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})
        url_anulado = f'{self.url}?simular_estado=anulado'
        response = self.client.get(url_anulado)
        self.assertEqual(response.status_code, 200)

        # Banner y estado de anulación
        self.assertContains(response, '● ANULADO')
        self.assertContains(response, 'COMPROBANTE FISCAL ANULADO (SIN EFECTO TRIBUTARIO)')
        self.assertContains(response, 'Acta de Anulación #')
        self.assertNotContains(response, 'RECHAZO FISCAL DGII')

    def test_emitted_invoice_from_draft_renders_custom_lines(self):
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})
        cliente = self.repo.get_cliente(1)
        linea1 = LineaFactura(
            id=uuid4(),
            tipo='servicio',
            concepto='Consultoría Especializada en Seguridad DGII',
            descripcion='Auditoría de certificados y cifrado RSA',
            unidad='Servicio',
            cantidad=Decimal('2.00'),
            precio=Decimal('10000.00'),
            descuento=Decimal('500.00'),
        )
        borrador = self.repo.create_borrador(tipo_ecf='31', cliente_id=cliente.id)
        self.repo.update_borrador(
            borrador.id,
            fecha_emision=date(2026, 10, 20),
            tipo_ingreso='01',
            tipo_pago='contado',
            forma_pago='02',
            lineas=(linea1,),
            revision_lineas=1,
        )
        huella = huella_borrador(self.repo.get_borrador(borrador.id))
        self.repo.guardar_totales(borrador.id, huella=huella, recalcular=True)
        factura_emitida = self.repo.emitir_factura(borrador.id, huella=huella)

        url_emitida = reverse('comprobantes:detalle', kwargs={'pk': factura_emitida.id})
        response = self.client.get(url_emitida)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, 'Consultoría Especializada en Seguridad DGII')
        self.assertContains(response, 'Auditoría de certificados y cifrado RSA')
        self.assertContains(response, factura_emitida.e_ncf)

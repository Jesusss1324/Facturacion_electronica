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
class RepresentacionImpresaPdfTests(SimpleTestCase):
    def setUp(self):
        source = get_repository()
        self.repo = FrontendRepository(source.list_clientes(), source.list_facturas())
        patcher = patch('comprobantes.views_pdf.get_repository', return_value=self.repo)
        patcher.start()
        self.addCleanup(patcher.stop)

        # Factura existente de los fixtures (ej: id=1)
        self.factura = self.repo.get_factura(1)
        self.url = reverse('comprobantes:pdf', kwargs={'pk': self.factura.id})

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(
            response,
            f"{reverse('usuarios:login')}?next={self.url}",
            fetch_redirect_response=False,
        )

    def test_404_for_non_existent_invoice(self):
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})
        url_inexistente = reverse('comprobantes:pdf', kwargs={'pk': 99999})
        response = self.client.get(url_inexistente)
        self.assertEqual(response.status_code, 404)

    def test_render_pdf_view_success(self):
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        # Encabezado y títulos
        self.assertContains(response, 'Representación Impresa PDF')
        self.assertContains(response, self.factura.e_ncf)
        self.assertContains(response, 'SOLUCIONES TECNOLÓGICAS DEL CARIBE, SRL')
        self.assertContains(response, 'COMPROBANTE FISCAL ELECTRÓNICO (e-CF)')

        # Elementos del visor de papel PDF
        self.assertContains(response, 'id="pdf-workbench"')
        self.assertContains(response, 'id="paper-sheet"')
        self.assertContains(response, 'id="btn-zoom-in"')
        self.assertContains(response, 'id="btn-zoom-out"')
        self.assertContains(response, 'id="btn-fit-width"')
        self.assertContains(response, 'Ajustar ancho')
        self.assertContains(response, 'Regla 300 DPI')
        self.assertContains(response, 'Márgenes ISO')

        # Contenido fiscal impreso en el papel
        self.assertContains(response, 'REPÚBLICA DOMINICANA')
        self.assertContains(response, 'DATOS DEL RECEPTOR')
        self.assertContains(response, 'CÓDIGO QR OFICIAL DGII')
        self.assertContains(response, 'CANTIDAD EN LETRAS')
        self.assertContains(response, 'TOTAL FACTURA')
        self.assertContains(response, 'Página 1 de 1 — Representación Gráfica e-CF')

        # Botones de acción
        self.assertContains(response, 'Imprimir')
        self.assertContains(response, 'Descargar PDF')
        self.assertContains(response, reverse('comprobantes:xml', kwargs={'pk': self.factura.id}))
        self.assertContains(response, reverse('comprobantes:detalle', kwargs={'pk': self.factura.id}))

    def test_emitted_invoice_custom_items_rendered_in_paper(self):
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})
        cliente = self.repo.get_cliente(1)
        linea = LineaFactura(
            id=uuid4(),
            tipo='servicio',
            concepto='Servicio de Timbrado Fiscal Integrado',
            descripcion='Interconexión y timbrado con plataforma DGII',
            unidad='Servicio',
            cantidad=Decimal('1.00'),
            precio=Decimal('25000.00'),
            descuento=Decimal('0.00'),
        )
        borrador = self.repo.create_borrador(tipo_ecf='31', cliente_id=cliente.id)
        self.repo.update_borrador(
            borrador.id,
            fecha_emision=date(2026, 10, 25),
            tipo_ingreso='01',
            tipo_pago='contado',
            forma_pago='02',
            lineas=(linea,),
            revision_lineas=1,
        )
        huella = huella_borrador(self.repo.get_borrador(borrador.id))
        self.repo.guardar_totales(borrador.id, huella=huella, recalcular=True)
        factura_emitida = self.repo.emitir_factura(borrador.id, huella=huella)

        url_emitida = reverse('comprobantes:pdf', kwargs={'pk': factura_emitida.id})
        response = self.client.get(url_emitida)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, 'Servicio de Timbrado Fiscal Integrado')
        self.assertContains(response, factura_emitida.e_ncf)

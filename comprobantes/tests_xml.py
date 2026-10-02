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
from .views_xml import construir_xml_factura


@override_settings(
    DEBUG=True,
    FRONTEND_AUTH_ENABLED=True,
    SESSION_ENGINE='django.contrib.sessions.backends.signed_cookies',
)
class DocumentoXmlTests(SimpleTestCase):
    def setUp(self):
        source = get_repository()
        self.repo = FrontendRepository(source.list_clientes(), source.list_facturas())
        patcher = patch('comprobantes.views_xml.get_repository', return_value=self.repo)
        patcher.start()
        self.addCleanup(patcher.stop)

        # Factura existente de los fixtures (ej: id=1)
        self.factura = self.repo.get_factura(1)
        self.url = reverse('comprobantes:xml', kwargs={'pk': self.factura.id})

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(
            response,
            f"{reverse('usuarios:login')}?next={self.url}",
            fetch_redirect_response=False,
        )

    def test_404_for_non_existent_invoice(self):
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})
        url_inexistente = reverse('comprobantes:xml', kwargs={'pk': 99999})
        response = self.client.get(url_inexistente)
        self.assertEqual(response.status_code, 404)

    def test_render_xml_view_success(self):
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        # Metadatos del encabezado y cards
        self.assertContains(response, self.factura.e_ncf)
        self.assertContains(response, 'DGII e-CF v1.0')
        self.assertContains(response, 'Esquema XSD Validado ✔')
        self.assertContains(response, 'RSA-SHA256')
        self.assertContains(response, 'SELLO DIGITAL XML-DSIG')

        # Estructura del visor de código
        self.assertContains(response, f'e-CF_{self.factura.e_ncf}.xml')
        self.assertContains(response, '&lt;eCF xmlns=&quot;http://dgii.gov.do/ecf/v1.0&quot;')
        self.assertContains(response, '&lt;Encabezado&gt;')
        self.assertContains(response, '&lt;Signature')

        # Botones de acción
        self.assertContains(response, 'Volver a la factura')
        self.assertContains(response, 'Copiar XML completo')
        self.assertContains(response, 'Descargar XML (.xml)')
        self.assertContains(response, 'id="btn-descargar-xml-file"')

    def test_construir_xml_factura_content_and_structure(self):
        cliente = self.repo.get_cliente(self.factura.cliente_id)
        xml = construir_xml_factura(self.factura, cliente)

        self.assertTrue(xml.startswith('<?xml version="1.0" encoding="UTF-8"?>'))
        self.assertIn('<eCF xmlns="http://dgii.gov.do/ecf/v1.0"', xml)
        self.assertIn(f'<eNCF>{self.factura.e_ncf}</eNCF>', xml)
        self.assertIn(f'<RNCEmisor>130987654</RNCEmisor>', xml)
        self.assertIn(f'<RNCComprador>{cliente.identificacion}</RNCComprador>', xml)
        self.assertIn('<Signature xmlns="http://www.w3.org/2000/09/xmldsig#">', xml)
        self.assertIn('<DigestValue>', xml)
        self.assertIn('<SignatureValue>', xml)
        self.assertIn('</eCF>', xml)

    def test_emitted_invoice_custom_items_rendered_in_xml(self):
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})
        cliente = self.repo.get_cliente(1)
        linea = LineaFactura(
            id=uuid4(),
            tipo='servicio',
            concepto='Licencia Enterprise e-CF Transaccional',
            descripcion='Licenciamiento anual de software fiscal',
            unidad='Servicio',
            cantidad=Decimal('1.00'),
            precio=Decimal('80000.00'),
            descuento=Decimal('0.00'),
        )
        borrador = self.repo.create_borrador(tipo_ecf='31', cliente_id=cliente.id)
        self.repo.update_borrador(
            borrador.id,
            fecha_emision=date(2026, 10, 22),
            tipo_ingreso='01',
            tipo_pago='contado',
            forma_pago='02',
            lineas=(linea,),
            revision_lineas=1,
        )
        huella = huella_borrador(self.repo.get_borrador(borrador.id))
        self.repo.guardar_totales(borrador.id, huella=huella, recalcular=True)
        factura_emitida = self.repo.emitir_factura(borrador.id, huella=huella)

        xml = construir_xml_factura(factura_emitida, cliente)
        self.assertIn('Licencia Enterprise e-CF Transaccional', xml)
        self.assertIn('<MontoTotal>94400.00</MontoTotal>', xml)

        # En la vista web también debe renderizar
        url_emitida = reverse('comprobantes:xml', kwargs={'pk': factura_emitida.id})
        response = self.client.get(url_emitida)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Licencia Enterprise e-CF Transaccional')

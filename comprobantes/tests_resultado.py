from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from django.urls import reverse

from frontend_data import get_repository
from frontend_data.repository import FrontendRepository


@override_settings(
    DEBUG=True,
    FRONTEND_AUTH_ENABLED=True,
    SESSION_ENGINE='django.contrib.sessions.backends.signed_cookies',
)
class ResultadoEmisionTests(SimpleTestCase):
    def setUp(self):
        source = get_repository()
        self.repo = FrontendRepository(source.list_clientes(), source.list_facturas())
        patcher = patch('comprobantes.views_resultado.get_repository', return_value=self.repo)
        patcher.start()
        self.addCleanup(patcher.stop)

        # Factura existente de los fixtures (ej: id=1)
        self.factura = self.repo.get_factura(1)
        self.url = reverse('comprobantes:resultado', kwargs={'pk': self.factura.id})

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(
            response,
            f"{reverse('usuarios:login')}?next={self.url}",
            fetch_redirect_response=False,
        )

    def test_404_for_non_existent_invoice(self):
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})
        url_inexistente = reverse('comprobantes:resultado', kwargs={'pk': 99999})
        response = self.client.get(url_inexistente)
        self.assertEqual(response.status_code, 404)

    def test_render_aprobado_default(self):
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        # Contenidos clave del banner aprobado
        self.assertContains(response, 'Factura Electrónica Emitida Exitosamente')
        self.assertContains(response, 'Comprobante Aceptado por DGII')
        self.assertContains(response, self.factura.e_ncf)
        self.assertContains(response, f'data-encf="{self.factura.e_ncf}"')
        self.assertContains(response, 'MCK-200')
        self.assertContains(response, 'XML-DSig RSA-SHA256 OK')

        # Cédula fiscal
        self.assertContains(response, 'Cédula Fiscal del Comprobante')
        self.assertContains(response, 'MONTO TOTAL LIQUIDADO')
        self.assertContains(response, 'ARTEFACTOS FISCALES DISPONIBLES')
        self.assertContains(response, 'Representación Impresa PDF')
        self.assertContains(response, 'Documento XML firmado')

        # Botones de navegación
        self.assertContains(response, reverse('comprobantes:detalle', kwargs={'pk': self.factura.id}))
        self.assertContains(response, reverse('comprobantes:pdf', kwargs={'pk': self.factura.id}))
        self.assertContains(response, reverse('comprobantes:xml', kwargs={'pk': self.factura.id}))
        self.assertContains(response, 'Ver factura')
        self.assertContains(response, 'Ver representación PDF')
        self.assertContains(response, 'Ver XML firmado')

        # No debe contener alertas de error ni motivos de rechazo
        self.assertNotContains(response, 'Emisión Rechazada por DGII')
        self.assertNotContains(response, 'Motivo del Rechazo')

    def test_render_rechazado_simulado(self):
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})
        url_rechazado = f'{self.url}?simular_estado=rechazado'
        response = self.client.get(url_rechazado)
        self.assertEqual(response.status_code, 200)

        # Contenidos clave del banner rechazado
        self.assertContains(response, 'Emisión Rechazada por DGII')
        self.assertContains(response, 'Rechazado por DGII')
        self.assertContains(response, 'Motivo del Rechazo')
        self.assertContains(response, 'ACCIÓN CORRECTIVA SUGERIDA')
        self.assertContains(response, 'Crear nueva factura con estos datos')
        self.assertContains(response, 'Ver XML rechazado')

        # No debe tener los artefactos fiscales de éxito
        self.assertNotContains(response, 'ARTEFACTOS FISCALES DISPONIBLES')

    def test_xml_node_inspection_accordion_present(self):
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, 'Inspección de Nodo XML Fiscal')
        self.assertContains(response, 'id="xml-dictamen-code"')
        self.assertContains(response, 'RespuestaRecepcion')
        self.assertContains(response, 'id="btn-copiar-xml-nodo"')

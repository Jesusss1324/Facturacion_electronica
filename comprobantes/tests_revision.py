from datetime import date
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from django.test import SimpleTestCase, override_settings
from django.urls import reverse

from frontend_data import get_repository
from frontend_data.entities import LineaFactura
from frontend_data.repository import FrontendRepository
from .revision import EMISOR_INFO, generar_xml_ecf, monto_en_letras
from .totales import huella_borrador


@override_settings(
    DEBUG=True,
    FRONTEND_AUTH_ENABLED=True,
    SESSION_ENGINE='django.contrib.sessions.backends.signed_cookies',
)
class RevisionFacturaTests(SimpleTestCase):
    def setUp(self):
        source = get_repository()
        self.repo = FrontendRepository(source.list_clientes(), source.list_facturas())
        patcher = patch('comprobantes.views_revision.get_repository', return_value=self.repo)
        patcher.start()
        self.addCleanup(patcher.stop)

        # Iniciar sesión localmente en memoria
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})

        self.cliente = self.repo.get_cliente(1)
        self.linea = LineaFactura(
            id=uuid4(),
            tipo='servicio',
            concepto='Consultoría Tecnológica Especializada',
            descripcion='Implementación y pruebas e-CF',
            unidad='Servicio',
            cantidad=Decimal('1.00'),
            precio=Decimal('10000.00'),
            descuento=Decimal('1000.00'),
        )
        self.borrador = self.repo.create_borrador(
            tipo_ecf='31',
            cliente_id=self.cliente.id,
        )
        self.borrador_id = self.borrador.id
        self.repo.update_borrador(
            self.borrador_id,
            fecha_emision=date(2026, 10, 14),
            tipo_ingreso='01',
            tipo_pago='contado',
            termino_pago='30_dias',
            fecha_vencimiento=date(2026, 11, 14),
            forma_pago='02',
            lineas=(self.linea,),
            revision_lineas=1,
        )
        huella = huella_borrador(self.repo.get_borrador(self.borrador_id))
        self.repo.guardar_totales(self.borrador_id, huella=huella, recalcular=True)
        self.url = reverse('comprobantes:revision', kwargs={'borrador_id': self.borrador_id})

    def test_unauthenticated_user_is_redirected_to_login(self):
        self.client.post('/acceso/cerrar-sesion/')
        response = self.client.get(self.url)
        self.assertRedirects(response, f'{reverse("usuarios:login")}?next={self.url}', fetch_redirect_response=False)

    def test_nonexistent_draft_returns_404(self):
        fake_id = uuid4()
        response = self.client.get(reverse('comprobantes:revision', kwargs={'borrador_id': fake_id}))
        self.assertEqual(response.status_code, 404)

    def test_guard_redirects_to_cliente_if_client_is_missing_or_inactive(self):
        self.repo.update_borrador(self.borrador_id, cliente_id=None)
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('comprobantes:cliente', kwargs={'borrador_id': self.borrador_id}), fetch_redirect_response=False)

        # Con cliente inactivo
        cliente_inactivo = [c for c in self.repo.list_clientes() if not c.activo][0]
        self.repo.update_borrador(self.borrador_id, cliente_id=cliente_inactivo.id)
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('comprobantes:cliente', kwargs={'borrador_id': self.borrador_id}), fetch_redirect_response=False)

    def test_guard_redirects_to_datos_if_emission_date_missing(self):
        self.repo.update_borrador(self.borrador_id, fecha_emision=None)
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('comprobantes:datos', kwargs={'borrador_id': self.borrador_id}), fetch_redirect_response=False)

    def test_guard_redirects_to_items_if_no_lines(self):
        self.repo.update_borrador(self.borrador_id, lineas=())
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('comprobantes:items', kwargs={'borrador_id': self.borrador_id}), fetch_redirect_response=False)

    def test_guard_redirects_to_totales_if_totals_not_saved(self):
        self.repo.update_borrador(self.borrador_id, totales_guardados=None)
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('comprobantes:totales', kwargs={'borrador_id': self.borrador_id}), fetch_redirect_response=False)

    def test_guard_redirects_to_totales_if_hash_inconsistent(self):
        # Alterar una propiedad después de guardar totales
        self.repo.update_borrador(self.borrador_id, revision_lineas=99)
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('comprobantes:totales', kwargs={'borrador_id': self.borrador_id}), fetch_redirect_response=False)

    def test_get_renders_invoice_sheet_with_all_sections(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        # Cabecera de emisor y e-NCF
        self.assertContains(response, 'SOLUCIONES DIGITALES DEL CARIBE, SRL')
        self.assertContains(response, '1-31-89012-3')
        self.assertContains(response, 'FACTURA ELECTRÓNICA DGII')
        self.assertContains(response, 'FACTURA DE CRÉDITO FISCAL ELECTRÓNICA')
        self.assertContains(response, self.borrador.secuencia_encf_display)

        # Receptor y condiciones
        self.assertContains(response, self.cliente.nombre)
        self.assertContains(response, self.cliente.identificacion_display)
        self.assertContains(response, 'CONDICIONES DE VENTA')
        self.assertContains(response, '02 — Cheque / Transferencia / Depósito')

        # Tabla de conceptos y marca de agua
        self.assertContains(response, 'BORRADOR PRE-TIMBRADO')
        self.assertContains(response, 'Consultoría Tecnológica Especializada')
        self.assertContains(response, '1 Ítems Verificados')

        # Totales y monto en letras
        self.assertContains(response, 'Monto Subtotal Gravado:')
        self.assertContains(response, 'TOTAL GENERAL A PAGAR')
        self.assertContains(response, '10,620.00')  # (10000 - 1000) * 1.18 = 10620.00
        self.assertContains(response, 'pesos dominicanos con 00/100 M.N.')

        # Panel de control de emisión y telemetría
        self.assertContains(response, 'Fiscal Dispatch Command')
        self.assertContains(response, 'Consola de Pre-Vuelo &amp; Timbrado')
        self.assertContains(response, 'Listo para Emisión')
        self.assertContains(response, 'POST /fe/recepcion/v1/ecf')
        self.assertContains(response, 'e-CF_FacturaCreditoFiscal_v1.0.xsd')

        # Modales de confirmación y XML
        self.assertContains(response, 'id="modal-confirmar-emision"')
        self.assertContains(response, '¿Confirmas la Emisión y Timbrado?')
        self.assertContains(response, 'id="modal-xml-crudo"')
        self.assertContains(response, 'Vista Previa XML e-CF (Estándar DGII)')

    def test_post_guardar_borrador_updates_timestamp_and_redirects(self):
        response = self.client.post(self.url, {'accion': 'guardar'})
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        borrador = self.repo.get_borrador(self.borrador_id)
        self.assertIsNotNone(borrador.fecha_guardado)

    def test_post_invalid_action_returns_bad_request(self):
        response = self.client.post(self.url, {'accion': 'invalida'})
        self.assertEqual(response.status_code, 400)

    def test_monto_en_letras_unit(self):
        self.assertEqual(
            monto_en_letras(Decimal('336890.00')),
            'Son: Trescientos treinta y seis mil ochocientos noventa pesos dominicanos con 00/100 M.N.'
        )
        self.assertEqual(
            monto_en_letras(Decimal('1.00')),
            'Son: Un peso dominicano con 00/100 M.N.'
        )
        self.assertEqual(
            monto_en_letras(Decimal('150000.50')),
            'Son: Ciento cincuenta mil pesos dominicanos con 50/100 M.N.'
        )
        self.assertEqual(
            monto_en_letras(Decimal('0.00')),
            'Son: Cero pesos dominicanos con 00/100 M.N.'
        )
        self.assertEqual(
            monto_en_letras(Decimal('1000000.00')),
            'Son: Un millón pesos dominicanos con 00/100 M.N.'
        )

    def test_generar_xml_ecf_unit(self):
        resumen = {'bruto': Decimal('10000.00'), 'descuento': Decimal('1000.00'), 'base': Decimal('9000.00'), 'itbis': Decimal('1620.00'), 'total': Decimal('10620.00')}
        borrador = self.repo.get_borrador(self.borrador_id)
        xml = generar_xml_ecf(borrador, self.cliente, resumen, EMISOR_INFO)
        self.assertIn('<TipoeCF>31</TipoeCF>', xml)
        self.assertIn('<RNCEmisor>131890123</RNCEmisor>', xml)
        self.assertIn(f'<RNCComprador>{self.cliente.identificacion}</RNCComprador>', xml)
        self.assertIn('<MontoTotal>10620.00</MontoTotal>', xml)
        self.assertIn('<NombreItem>Consultoría Tecnológica Especializada</NombreItem>', xml)

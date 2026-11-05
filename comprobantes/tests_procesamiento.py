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
@override_settings(FRONTEND_DATA_BACKEND="memory")
class ProcesamientoFacturaTests(SimpleTestCase):
    def setUp(self):
        source = get_repository()
        self.repo = FrontendRepository(source.list_clientes(), source.list_facturas())
        patcher_view = patch('comprobantes.views_procesamiento.get_repository', return_value=self.repo)
        patcher_view.start()
        self.addCleanup(patcher_view.stop)

        # Iniciar sesión localmente en memoria
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})

        self.cliente = self.repo.get_cliente(1)
        self.linea = LineaFactura(
            id=uuid4(),
            tipo='servicio',
            concepto='Servicio de Facturación Electrónica',
            descripcion='Pruebas integradas de emisión e-CF',
            unidad='Servicio',
            cantidad=Decimal('1.00'),
            precio=Decimal('5000.00'),
            descuento=Decimal('0.00'),
        )
        self.borrador = self.repo.create_borrador(
            tipo_ecf='31',
            cliente_id=self.cliente.id,
        )
        self.repo.update_borrador(
            self.borrador.id,
            fecha_emision=date(2026, 10, 14),
            tipo_ingreso='01',
            tipo_pago='contado',
            forma_pago='02',
            lineas=(self.linea,),
            revision_lineas=1,
        )
        huella = huella_borrador(self.repo.get_borrador(self.borrador.id))
        self.repo.guardar_totales(self.borrador.id, huella=huella, recalcular=True)

        # Emitir la factura de prueba
        self.factura = self.repo.emitir_factura(self.borrador.id, huella=huella)
        self.url = reverse('comprobantes:procesamiento', kwargs={'pk': self.factura.id})

    def test_unauthenticated_user_redirected_to_login(self):
        self.client.post('/acceso/cerrar-sesion/')
        response = self.client.get(self.url)
        self.assertRedirects(response, f'{reverse("usuarios:login")}?next={self.url}', fetch_redirect_response=False)

    def test_nonexistent_invoice_returns_404(self):
        response = self.client.get(reverse('comprobantes:procesamiento', kwargs={'pk': 999999}))
        self.assertEqual(response.status_code, 404)

    def test_get_procesamiento_renders_pipeline_and_summary(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        # Encabezado y fases del pipeline
        self.assertContains(response, 'El comprobante se está procesando de manera segura')
        self.assertContains(response, 'Preparar')
        self.assertContains(response, 'XML e-CF')
        self.assertContains(response, 'Validación')
        self.assertContains(response, 'Firma')
        self.assertContains(response, 'Envío')
        self.assertContains(response, 'Acuse')

        # Tarjeta de contexto del comprobante
        self.assertContains(response, self.factura.e_ncf)
        self.assertContains(response, self.cliente.nombre)
        self.assertContains(response, 'MONTO A LIQUIDAR')
        self.assertContains(response, '5,900.00')  # 5000 * 1.18 = 5900.00

    def test_get_procesamiento_completed_state(self):
        response = self.client.get(f'{self.url}?estado=completado')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '¡Comprobante Timbrado y Aceptado!')
        self.assertContains(response, self.factura.track_id_display)
        self.assertContains(response, reverse('comprobantes:resultado', kwargs={'pk': self.factura.id}))

    def test_get_procesamiento_validation_error_state(self):
        response = self.client.get(f'{self.url}?simular_error=validacion')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Detenido: Inconsistencia detectada en validación fiscal (Regla RN-032)')

    def test_get_procesamiento_timeout_error_state(self):
        response = self.client.get(f'{self.url}?simular_error=timeout')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'El servicio tardó más de lo esperado en responder')
        self.assertContains(response, 'Reintentar transmisión')

    def test_post_not_allowed_on_procesamiento(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 405)


@override_settings(
    DEBUG=True,
    FRONTEND_AUTH_ENABLED=True,
    SESSION_ENGINE='django.contrib.sessions.backends.signed_cookies',
)
@override_settings(FRONTEND_DATA_BACKEND="memory")
class EmitirComprobanteTests(SimpleTestCase):
    def test_emitted_draft_pages_redirect_to_existing_invoice(self):
        from contextlib import ExitStack
        factura = self.repo.emitir_factura(self.borrador.id, self.huella)
        with ExitStack() as stack:
            for module in ('draft_access', 'views', 'views_items', 'views_totales', 'views_revision'):
                stack.enter_context(patch(f'comprobantes.{module}.get_repository', return_value=self.repo))
            for step in ('cliente', 'datos', 'items', 'totales', 'revision'):
                url = reverse(f'comprobantes:{step}', kwargs={'borrador_id': self.borrador.id})
                for method in (self.client.get, self.client.post):
                    with self.subTest(step=step, method=method.__name__):
                        self.assertRedirects(method(url), reverse('comprobantes:detalle', kwargs={'pk': factura.id}),
                                             fetch_redirect_response=False)

    def test_repeated_posts_return_the_same_invoice(self):
        before = len(self.repo.list_facturas())
        first = self.client.post(self.emitir_url, {'huella': self.huella})
        second = self.client.post(self.emitir_url, {'huella': self.huella})
        self.assertEqual(first.status_code, 302)
        self.assertEqual(first['Location'], second['Location'])
        self.assertEqual(len(self.repo.list_facturas()), before + 1)

    def test_concurrent_emissions_create_only_one_invoice(self):
        from concurrent.futures import ThreadPoolExecutor
        before = len(self.repo.list_facturas())
        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(
                lambda _: self.repo.emitir_factura(self.borrador.id, self.huella), range(16)))
        self.assertEqual(len({factura.id for factura in results}), 1)
        self.assertEqual(len(self.repo.list_facturas()), before + 1)
        with self.assertRaises(ValueError):
            self.repo.update_borrador(self.borrador.id, tipo_pago='credito')

    def test_missing_hash_and_changed_draft_cannot_emit(self):
        with self.assertRaises(ValueError):
            self.repo.emitir_factura(self.borrador.id)
        self.repo.update_borrador(self.borrador.id, forma_pago='01')
        with self.assertRaises(ValueError):
            self.repo.emitir_factura(self.borrador.id, self.huella)

    def setUp(self):
        source = get_repository()
        self.repo = FrontendRepository(source.list_clientes(), source.list_facturas())
        patcher = patch('comprobantes.views_procesamiento.get_repository', return_value=self.repo)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})
        self.cliente = self.repo.get_cliente(1)
        self.borrador = self.repo.create_borrador('31', self.cliente.id)
        linea = LineaFactura(
            id=uuid4(),
            tipo='servicio',
            concepto='Desarrollo a Medida',
            descripcion='',
            unidad='Servicio',
            cantidad=Decimal('1.00'),
            precio=Decimal('20000.00'),
            descuento=Decimal('0.00'),
        )
        self.repo.update_borrador(
            self.borrador.id,
            fecha_emision=date(2026, 10, 14),
            tipo_ingreso='01',
            tipo_pago='contado',
            forma_pago='02',
            lineas=(linea,),
            revision_lineas=1,
        )
        self.huella = huella_borrador(self.repo.get_borrador(self.borrador.id))
        self.repo.guardar_totales(self.borrador.id, huella=self.huella, recalcular=True)
        self.emitir_url = reverse('comprobantes:emitir', kwargs={'borrador_id': self.borrador.id})

    def test_unauthenticated_user_cannot_emit(self):
        self.client.post('/acceso/cerrar-sesion/')
        response = self.client.post(self.emitir_url, {'huella': self.huella})
        self.assertRedirects(response, f'{reverse("usuarios:login")}?next={self.emitir_url}', fetch_redirect_response=False)

    def test_emit_unknown_draft_returns_404(self):
        response = self.client.post(reverse('comprobantes:emitir', kwargs={'borrador_id': uuid4()}))
        self.assertEqual(response.status_code, 404)

    def test_emit_invalid_hash_redirects_to_revision(self):
        response = self.client.post(self.emitir_url, {'huella': 'hash-invalido-o-desfasado'})
        self.assertRedirects(
            response,
            reverse('comprobantes:revision', kwargs={'borrador_id': self.borrador.id}),
            fetch_redirect_response=False,
        )

    def test_emit_valid_draft_creates_invoice_and_redirects_to_procesamiento(self):
        response = self.client.post(self.emitir_url, {'huella': self.huella})
        # Verifica redirección hacia /facturas/<pk>/procesamiento/
        self.assertEqual(response.status_code, 302)
        target_url = response.headers.get('Location')
        self.assertIn('/procesamiento/', target_url)

        # La factura debe existir en el repositorio con estado aprobado y secuencia e-NCF
        facturas = self.repo.list_facturas()
        factura_emitida = [f for f in facturas if f.monto_total == Decimal('23600.00')][0]
        self.assertEqual(factura_emitida.estado, 'aprobado')
        self.assertTrue(factura_emitida.e_ncf.startswith('E31'))
        self.assertTrue(factura_emitida.track_id_display.startswith('DGII-REC-'))

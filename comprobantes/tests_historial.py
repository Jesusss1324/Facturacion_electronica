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
class HistorialFacturasTests(SimpleTestCase):
    def setUp(self):
        source = get_repository()
        self.repo = FrontendRepository(source.list_clientes(), source.list_facturas())
        patcher = patch('comprobantes.views_historial.get_repository', return_value=self.repo)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.url = reverse('comprobantes:historial')

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(
            response,
            f"{reverse('usuarios:login')}?next={self.url}",
            fetch_redirect_response=False,
        )

    def test_render_historial_default_split_view(self):
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        # Encabezado y búsqueda
        self.assertContains(response, 'Historial de facturas & Expediente Activo')
        self.assertContains(response, 'id="input-busqueda"')
        self.assertContains(response, '+ Nueva factura')
        self.assertContains(response, 'Exportar CSV')

        # Pills rápidos
        self.assertContains(response, 'E31 Crédito Fiscal')
        self.assertContains(response, 'E32 Consumo')
        self.assertContains(response, '✔ Aprobados')
        self.assertContains(response, '⊗ Rechazados')

        # Vista dividida activa
        self.assertContains(response, 'split-layout')
        self.assertContains(response, 'EXPEDIENTE FISCAL ACTIVO')
        self.assertContains(response, 'Abrir expediente completo')

        # Paginación presente
        self.assertContains(response, 'pagination-footer')

    def test_search_by_encf_and_empty_results(self):
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})
        primera_factura = self.repo.list_facturas()[0]

        # Búsqueda con resultado
        url_busqueda = f"{self.url}?q={primera_factura.e_ncf}"
        response = self.client.get(url_busqueda)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, primera_factura.e_ncf)

        # Búsqueda sin coincidencias
        url_vacia = f"{self.url}?q=NCF_QUE_NO_EXISTE_9999"
        response_vacia = self.client.get(url_vacia)
        self.assertEqual(response_vacia.status_code, 200)
        self.assertContains(response_vacia, 'No se encontraron comprobantes fiscales')
        self.assertContains(response_vacia, 'Restablecer criterios')

    def test_filter_by_tipo_and_estado(self):
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})

        # Filtro E32
        res_e32 = self.client.get(f"{self.url}?filtro=e32")
        self.assertEqual(res_e32.status_code, 200)
        for item in res_e32.context['page_obj']:
            self.assertEqual(item.factura.tipo_ecf, '32')

        # Filtro rechazados
        res_rechazados = self.client.get(f"{self.url}?filtro=rechazados")
        self.assertEqual(res_rechazados.status_code, 200)
        for item in res_rechazados.context['page_obj']:
            self.assertEqual(item.factura.estado, 'rechazado')

    def test_table_view_mode(self):
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})
        res_tabla = self.client.get(f"{self.url}?vista=tabla")
        self.assertEqual(res_tabla.status_code, 200)
        self.assertContains(res_tabla, 'full-history-table')
        self.assertContains(res_tabla, 'table-view-card')

    def test_export_csv(self):
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})
        response = self.client.get(f"{self.url}?export=csv")
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response.headers.get('Content-Type'))
        self.assertIn('attachment; filename="Historial_Facturas_eCF.csv"', response.headers.get('Content-Disposition'))

        content = response.content.decode('utf-8-sig')
        self.assertTrue(content.startswith('e-NCF,Tipo e-CF'))
        self.assertIn('TrackId DGII', content)

    def test_empty_database_state(self):
        # Repositorio sin facturas
        repo_vacio = FrontendRepository(self.repo.list_clientes(), ())
        with patch('comprobantes.views_historial.get_repository', return_value=repo_vacio):
            self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})
            response = self.client.get(self.url)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Historial de comprobantes vacío')
            self.assertContains(response, '+ Crear primera factura')

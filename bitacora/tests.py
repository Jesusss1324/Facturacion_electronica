from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from frontend_data import get_repository


class LogViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='operador', password='test-access-4921')
        cls.repo = get_repository()

    def test_anonymous_user_redirected_to_login(self):
        urls = [
            reverse('bitacora:listado'),
            reverse('bitacora:detalle', kwargs={'pk': 234}),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(response, f'{reverse("usuarios:login")}?next={url}', fetch_redirect_response=False)

    def test_list_view_renders_200_and_shows_audit_header(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('bitacora:listado'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Logs de eventos')
        self.assertContains(response, 'AUDITORÍA REGULATORIA DGII')
        self.assertContains(response, 'Registro Criptográfico Inmutable (Solo lectura)')
        self.assertContains(response, '234 eventos auditados')
        self.assertContains(response, 'Zona horaria: America/Santo_Domingo (UTC-4)')
        self.assertContains(response, 'Exportar CSV')
        self.assertContains(response, 'Integridad XML-DSig')
        self.assertContains(response, 'Recepción y Acuse DGII')
        self.assertContains(response, 'Cadena de No Repudio')

    def test_list_view_shows_top_ten_events_on_page_one(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('bitacora:listado'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Factura aprobada por DGII')
        self.assertContains(response, 'Comprobante enviado a DGII')
        self.assertContains(response, 'Documento firmado con XML-DSig')
        self.assertContains(response, 'XML e-CF v1.0 generado')
        self.assertContains(response, 'E310000000004')
        self.assertContains(response, 'Inspeccionar')

    def test_list_view_filter_by_query(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('bitacora:listado'), {'q': 'E310000000004'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'E310000000004')
        self.assertContains(response, 'Búsqueda: E310000000004')

    def test_list_view_filter_by_module(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('bitacora:listado'), {'modulo': 'dgii'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Servicio DGII')
        self.assertContains(response, 'Módulo: Servicio DGII')

    def test_list_view_filter_by_result(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('bitacora:listado'), {'resultado': 'error'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Error')

    def test_list_view_empty_state_when_no_match(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('bitacora:listado'), {'q': 'no_existe_este_evento_xyz_9999'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No se encontraron eventos técnicos')
        self.assertContains(response, 'Restablecer filtros')

    def test_export_csv(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('bitacora:listado'), {'format': 'csv'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('attachment;', response['Content-Disposition'])
        content = response.content.decode('utf-8-sig')
        self.assertIn('Fecha_Hora_MS', content)
        self.assertIn('Hash_SHA256', content)
        self.assertIn('Factura aprobada por DGII', content)

    def test_detail_view_renders_200_for_existing_event(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('bitacora:detalle', kwargs={'pk': 234}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Detalle del log #234')
        self.assertContains(response, 'INTEGRIDAD CRIPTOGRÁFICA Y HASH')
        self.assertContains(response, 'PARÁMETROS DE ORIGEN Y SESIÓN')
        self.assertContains(response, 'PAYLOAD TÉCNICO COMPLETO')
        self.assertContains(response, 'DigestValue SHA-256')

    def test_detail_view_returns_404_for_nonexistent_event(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('bitacora:detalle', kwargs={'pk': 999999}))
        self.assertEqual(response.status_code, 404)

    def test_post_methods_not_allowed(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.post(reverse('bitacora:listado')).status_code, 405)
        self.assertEqual(self.client.post(reverse('bitacora:detalle', kwargs={'pk': 234})).status_code, 405)

    def test_logs_url_alias_works(self):
        self.client.force_login(self.user)
        response = self.client.get('/logs/')
        self.assertRedirects(response, reverse('bitacora:listado'), fetch_redirect_response=False)

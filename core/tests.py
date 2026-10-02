from pathlib import Path
from uuid import UUID

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import NoReverseMatch, resolve, reverse

from .navigation import SCREENS


class InterfaceStructureTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='operador', password='test-access-4921')
        cls.draft_id = UUID('38e16ecb-119c-42cc-bccb-18e7f1c2cd48')

    def screen_url(self, name):
        if name in {'comprobantes:cliente', 'comprobantes:datos', 'comprobantes:items',
                    'comprobantes:totales', 'comprobantes:revision'}:
            return reverse(name, kwargs={'borrador_id': self.draft_id})
        if name in {'clientes:detalle', 'clientes:editar', 'comprobantes:detalle',
                    'comprobantes:procesamiento', 'comprobantes:resultado',
                    'comprobantes:xml', 'comprobantes:pdf', 'bitacora:detalle'}:
            return reverse(name, kwargs={'pk': 1})
        return reverse(name)

    def test_named_routes_roundtrip_and_do_not_shadow_each_other(self):
        for name in SCREENS:
            with self.subTest(name=name):
                self.assertEqual(resolve(self.screen_url(name)).view_name, name)
        self.assertEqual(reverse('clientes:crear'), '/clientes/nuevo/')
        self.assertEqual(reverse('comprobantes:historial'), '/facturas/')
        self.assertEqual(reverse('core:inicio'), '/inicio/')

    def test_private_pages_require_login_and_preserve_destination(self):
        for name in SCREENS:
            if name == 'usuarios:login':
                continue
            with self.subTest(name=name):
                url = self.screen_url(name)
                self.assertRedirects(
                    self.client.get(url), f'{reverse("usuarios:login")}?next={url}',
                    fetch_redirect_response=False,
                )

    def test_reserved_screens_render_shared_layout_without_claiming_completion(self):
        self.client.force_login(self.user)
        for name, screen in SCREENS.items():
            if name in {'usuarios:login', 'core:inicio', 'clientes:listado', 'clientes:crear', 'clientes:detalle', 'clientes:editar', 'comprobantes:tipo', 'comprobantes:cliente', 'comprobantes:datos', 'comprobantes:items', 'comprobantes:totales', 'comprobantes:revision', 'comprobantes:procesamiento', 'comprobantes:resultado', 'comprobantes:detalle', 'comprobantes:xml', 'comprobantes:pdf', 'comprobantes:historial', 'bitacora:listado', 'bitacora:detalle', 'core:marco_legal'}:
                continue
            with self.subTest(name=name):
                response = self.client.get(self.screen_url(name))
                self.assertContains(response, screen.title, status_code=501)
                self.assertContains(response, 'Sección en preparación', status_code=501)
                self.assertContains(response, '/static/css/global.css', status_code=501)
                if name != 'usuarios:login':
                    self.assertContains(response, 'aria-label="Navegación principal"', status_code=501)
                    self.assertContains(response, 'aria-current="page"', status_code=501)
                if screen.step:
                    self.assertContains(response, 'aria-current="step"', status_code=501)

    def test_root_and_new_invoice_redirect_to_canonical_routes(self):
        self.assertRedirects(self.client.get('/'), '/inicio/', fetch_redirect_response=False)
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get('/facturas/nueva/'), '/facturas/nueva/tipo/', fetch_redirect_response=False)

    def test_reads_cannot_change_client_state_or_emit_an_invoice(self):
        self.client.force_login(self.user)
        urls = [
            reverse('clientes:cambiar_estado', kwargs={'pk': 1}),
            reverse('comprobantes:emitir', kwargs={'borrador_id': self.draft_id}),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 405)
                self.assertEqual(self.client.post(url).status_code, 400 if '/clientes/' in url else 404)

    def test_reserved_actions_are_protected_by_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        for url in [reverse('clientes:cambiar_estado', kwargs={'pk': 1}),
                    reverse('comprobantes:emitir', kwargs={'borrador_id': self.draft_id}),
                    reverse('usuarios:logout')]:
            with self.subTest(url=url):
                self.assertEqual(client.post(url).status_code, 403)

    def test_pending_forms_reject_post_until_implemented(self):
        self.client.force_login(self.user)
        for name in []:
            with self.subTest(name=name):
                self.assertEqual(self.client.post(self.screen_url(name)).status_code, 405)

    def test_pending_downloads_never_serve_fake_documents(self):
        for name in ['comprobantes:descargar_xml', 'comprobantes:descargar_pdf']:
            with self.subTest(name=name):
                url = reverse(name, kwargs={'pk': 1})
                self.assertEqual(self.client.get(url).status_code, 302)
                self.client.force_login(self.user)
                response = self.client.get(url)
                self.assertEqual(response.status_code, 501)
                self.assertNotIn('Content-Disposition', response.headers)
                self.client.logout()

    def test_logout_requires_post_and_ends_session(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('usuarios:logout')).status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)
        self.assertRedirects(self.client.post(reverse('usuarios:logout')), reverse('usuarios:login'), fetch_redirect_response=False)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_invalid_identifiers_do_not_resolve(self):
        self.client.force_login(self.user)
        for url in ['/clientes/no-es-un-id/', '/facturas/borradores/no-es-un-uuid/datos/']:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_audit_has_no_write_or_delete_route(self):
        for name in ['bitacora:crear', 'bitacora:editar', 'bitacora:eliminar']:
            with self.subTest(name=name), self.assertRaises(NoReverseMatch):
                reverse(name)
        self.client.force_login(self.user)
        self.assertEqual(self.client.post(reverse('bitacora:listado')).status_code, 405)

    @override_settings(DEBUG=False, ALLOWED_HOSTS=['testserver'])
    def test_shared_error_pages_keep_http_status(self):
        response = self.client.get('/direccion-inexistente/')
        self.assertContains(response, 'Página no encontrada', status_code=404)
        from .views import bad_request, permission_denied, server_error
        for handler, status in [(bad_request, 400), (permission_denied, 403), (server_error, 500)]:
            with self.subTest(status=status):
                request = self.client.request().wsgi_request
                response = handler(request) if status == 500 else handler(request, Exception('detalle privado'))
                self.assertEqual(response.status_code, status)
                self.assertNotIn('detalle privado', response.content.decode())

    def test_interface_copy_has_no_academic_or_fake_operational_claims(self):
        for root in [settings.BASE_DIR / 'templates', settings.BASE_DIR / 'static',
                     settings.BASE_DIR / 'usuarios' / 'templates']:
            for path in Path(root).rglob('*'):
                if path.suffix not in {'.html', '.js'}:
                    continue
                content = path.read_text(encoding='utf-8').lower()
                for forbidden in ['académico', 'academico', 'educativo', 'simulación', 'simulador', 'dgii producción']:
                    with self.subTest(path=path, forbidden=forbidden):
                        self.assertNotIn(forbidden, content)

    def test_marco_legal_requires_login(self):
        url = reverse('core:marco_legal')
        response = self.client.get(url)
        self.assertRedirects(response, f'{reverse("usuarios:login")}?next={url}', fetch_redirect_response=False)

    def test_marco_legal_renders_200_and_shows_laws(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('core:marco_legal'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Marco Legal y Normativo')
        self.assertContains(response, 'Ley Núm. 32-23')
        self.assertContains(response, 'Ley Núm. 126-02')
        self.assertContains(response, 'Norma General Núm. 06-2023')
        self.assertContains(response, 'Norma General Núm. 06-2018')
        self.assertContains(response, 'Especificación Técnica e-CF v1.0')
        self.assertContains(response, 'Matriz de Cumplimiento Técnico-Legal')
        self.assertContains(response, 'Plena Validez Legal, Probatoria y Ejecutiva')

    def test_marco_legal_filter_by_type(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('core:marco_legal'), {'tipo': 'ley'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ley Núm. 32-23')
        self.assertNotContains(response, 'Norma General Núm. 06-2023')

    def test_marco_legal_post_not_allowed(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('core:marco_legal'))
        self.assertEqual(response.status_code, 405)

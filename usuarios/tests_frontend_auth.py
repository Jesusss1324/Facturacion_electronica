from django.test import Client, SimpleTestCase, override_settings

from . import frontend_auth


@override_settings(DEBUG=True, FRONTEND_AUTH_ENABLED=True,
                   SESSION_ENGINE='django.contrib.sessions.backends.signed_cookies')
class FrontendAccessTests(SimpleTestCase):
    # SimpleTestCase rechaza cualquier consulta SQL durante todo el flujo HTTP.
    def test_login_dashboard_refresh_and_logout_without_database(self):
        response = self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})
        self.assertRedirects(response, '/inicio/')
        self.assertContains(self.client.get('/inicio/'), 'Facturas recientes')
        self.assertContains(self.client.get('/inicio/'), 'user')
        self.assertContains(self.client.get('/inicio/'), 'Administrador')
        self.assertNotIn('1234', str(dict(self.client.session)))
        self.assertRedirects(self.client.post('/acceso/cerrar-sesion/'), '/acceso/iniciar-sesion/')
        self.assertRedirects(self.client.get('/inicio/'), '/acceso/iniciar-sesion/?next=/inicio/')

    def test_wrong_credentials_rejected_without_database(self):
        for username, password in [('user', 'incorrecta'), ('otro', '1234')]:
            response = self.client.post('/acceso/iniciar-sesion/', {'username': username, 'password': password})
            self.assertContains(response, 'Usuario o contraseña incorrectos.')
            self.assertNotIn(frontend_auth.SESSION_KEY, self.client.session)

    def test_csrf_is_enforced(self):
        client = Client(enforce_csrf_checks=True)
        credentials = {'username': 'user', 'password': '1234'}
        self.assertEqual(client.post('/acceso/iniciar-sesion/', credentials).status_code, 403)
        client.get('/acceso/iniciar-sesion/')
        credentials['csrfmiddlewaretoken'] = client.cookies['csrftoken'].value
        self.assertRedirects(client.post('/acceso/iniciar-sesion/', credentials), '/inicio/')

    def test_external_next_is_not_followed(self):
        response = self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234', 'next': 'https://externo.example/'})
        self.assertRedirects(response, '/inicio/')

    def test_user_has_no_administrative_privileges(self):
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})
        self.assertRedirects(self.client.get('/admin/'), '/admin/login/?next=/admin/', fetch_redirect_response=False)

    def test_access_is_disabled_outside_debug(self):
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})
        with override_settings(DEBUG=False):
            self.assertIsNone(frontend_auth.authenticate('user', '1234'))
            self.assertEqual(self.client.get('/inicio/').status_code, 302)

    def test_tampered_cookie_cannot_authenticate(self):
        self.client.post('/acceso/iniciar-sesion/', {'username': 'user', 'password': '1234'})
        cookie_name = 'frontend_sessionid'
        self.client.cookies[cookie_name] = self.client.cookies[cookie_name].value + 'invalid'
        self.assertEqual(self.client.get('/inicio/').status_code, 302)

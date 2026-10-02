from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse


@override_settings(FRONTEND_AUTH_ENABLED=False)
class InicioSesionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.credentials = {'username': 'operador', 'password': 'Acceso-real-4921'}
        cls.user = get_user_model().objects.create_user(**cls.credentials)
        get_user_model().objects.create_user(
            username='inactivo', password=cls.credentials['password'], is_active=False,
        )

    def test_public_login_has_real_form_and_empty_credentials(self):
        response = self.client.get(reverse('usuarios:login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'usuarios/login.html')
        self.assertContains(response, 'csrfmiddlewaretoken')
        self.assertContains(response, 'autocomplete="username"')
        self.assertContains(response, 'autocomplete="current-password"')
        self.assertIsNone(response.context['form']['username'].value())
        self.assertIsNone(response.context['form']['password'].value())

    def test_valid_credentials_start_session_and_go_to_home(self):
        response = self.client.post(reverse('usuarios:login'), self.credentials)
        self.assertRedirects(response, reverse('core:inicio'), fetch_redirect_response=False)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)
        self.assertNotIn('password', self.client.session)

    def test_login_returns_to_requested_private_page(self):
        target = reverse('clientes:listado')
        response = self.client.post(reverse('usuarios:login'), {**self.credentials, 'next': target})
        self.assertRedirects(response, target, fetch_redirect_response=False)

    def test_get_preserves_next_in_the_form(self):
        response = self.client.get(reverse('usuarios:login'), {'next': '/facturas/'})
        self.assertContains(response, 'name="next" value="/facturas/"')

    def test_external_redirects_fall_back_to_home(self):
        for target in ['https://externo.example/login', '//externo.example/', 'javascript:alert(1)']:
            with self.subTest(target=target):
                self.client.logout()
                response = self.client.post(reverse('usuarios:login'), {**self.credentials, 'next': target})
                self.assertRedirects(response, reverse('core:inicio'), fetch_redirect_response=False)

    def test_empty_fields_have_accessible_errors(self):
        response = self.client.post(reverse('usuarios:login'), {'username': '', 'password': ''})
        self.assertContains(response, 'Ingresa tu usuario.')
        self.assertContains(response, 'Ingresa tu contraseña.')
        self.assertContains(response, 'aria-invalid="true"', count=2)
        self.assertContains(response, 'aria-describedby="id_username_error"')
        self.assertContains(response, 'aria-describedby="id_password_error"')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_wrong_credentials_keep_username_and_clear_password(self):
        response = self.client.post(reverse('usuarios:login'), {'username': 'operador', 'password': 'clave-incorrecta'})
        self.assertContains(response, 'Usuario o contraseña incorrectos.')
        self.assertContains(response, 'value="operador"')
        self.assertNotContains(response, 'clave-incorrecta')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_unknown_and_inactive_users_have_same_generic_error(self):
        for username in ['desconocido', 'inactivo']:
            with self.subTest(username=username):
                response = self.client.post(reverse('usuarios:login'), {**self.credentials, 'username': username})
                self.assertContains(response, 'Usuario o contraseña incorrectos.')
                self.assertNotIn('_auth_user_id', self.client.session)

    def test_existing_session_skips_login(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get(reverse('usuarios:login')), reverse('core:inicio'), fetch_redirect_response=False)

    def test_csrf_is_required_and_valid_token_authenticates(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse('usuarios:login'), self.credentials).status_code, 403)
        client.get(reverse('usuarios:login'))
        token = client.cookies['csrftoken'].value
        response = client.post(reverse('usuarios:login'), {**self.credentials, 'csrfmiddlewaretoken': token})
        self.assertRedirects(response, reverse('core:inicio'), fetch_redirect_response=False)

    def test_logout_then_login_form_is_available_again(self):
        self.client.post(reverse('usuarios:login'), self.credentials)
        self.client.post(reverse('usuarios:logout'))
        self.assertEqual(self.client.get(reverse('usuarios:login')).status_code, 200)

    def test_username_is_escaped_when_redisplayed(self):
        response = self.client.post(reverse('usuarios:login'), {'username': '<script>alert(1)</script>', 'password': ''})
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, SimpleTestCase
from django.urls import resolve, reverse

from frontend_data.repository import FrontendRepository, get_repository
from usuarios.models import Usuario

from .templatetags.ui_format import moneda_rd


class InicioTests(SimpleTestCase):
    # SimpleTestCase prohíbe acceder a la BD: ni fixtures SQL ni usuarios guardados.
    def setUp(self):
        self.factory = RequestFactory()
        self.user = Usuario(username='operador', first_name='Ismael', last_name='Batista')

    def response(self, user=None, method='get'):
        request = getattr(self.factory, method)(reverse('core:inicio'))
        request.user = user if user is not None else self.user
        request.resolver_match = resolve(request.path)
        response = request.resolver_match.func(request)
        if hasattr(response, 'render'):
            response.render()
        return response

    def test_dashboard_renders_without_any_database_access(self):
        response = self.response()
        self.assertContains(response, 'Ismael')
        self.assertContains(response, 'Facturas recientes')
        self.assertContains(response, '128')
        self.assertContains(response, '119')
        self.assertContains(response, 'Mostrando <strong>5</strong> de <strong>128</strong>')
        self.assertContains(response, 'Comercial Nova Caribe, SRL')
        self.assertContains(response, 'RD$ 145,280.00')
        self.assertEqual(response.template_name, ['core/inicio.html'])

    def test_dashboard_requires_an_authenticated_user(self):
        response = self.response(user=AnonymousUser())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/acceso/iniciar-sesion/?next=/inicio/')

    def test_links_reference_canonical_routes_and_shared_record_ids(self):
        response = self.response()
        for name in ['clientes:crear', 'comprobantes:nueva', 'comprobantes:historial']:
            self.assertContains(response, f'href="{reverse(name)}"')
        for item in get_repository().recent_facturas():
            self.assertContains(response, f'href="{reverse("comprobantes:detalle", kwargs={"pk": item.factura.id})}"', count=2)

    def test_greeting_uses_local_hour(self):
        for utc_hour, expected in [(13, 'Buenos días'), (18, 'Buenas tardes'), (0, 'Buenas noches')]:
            with self.subTest(hour=utc_hour), patch('core.views.timezone.now', return_value=datetime(2026, 10, 1, utc_hour, tzinfo=timezone.utc)):
                self.assertContains(self.response(), expected)

    def test_username_fallback_and_escaping(self):
        user = Usuario(username='operador', first_name='')
        self.assertContains(self.response(user=user), 'operador')
        user.first_name = '<script>alert(1)</script>'
        response = self.response(user=user)
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')

    @patch('core.views.get_repository', return_value=FrontendRepository())
    def test_empty_state_has_useful_action_and_no_table_rows(self, mock_repository):
        response = self.response()
        self.assertContains(response, 'No hay facturas registradas todavía')
        self.assertNotContains(response, '<tbody>')
        self.assertContains(response, 'href="/facturas/nueva/"')

    def test_no_mockup_controls_or_academic_labels_are_rendered(self):
        content = self.response().content.decode().lower()
        for forbidden in ['simulador', 'académico', 'bandeja vacía', 'con registros', 'mock dgii']:
            self.assertNotIn(forbidden, content)

    def test_dashboard_does_not_accept_state_changing_methods(self):
        self.assertEqual(self.response(method='post').status_code, 405)

    def test_currency_keeps_precision_and_readable_separators(self):
        self.assertEqual(moneda_rd(Decimal('145280.00')), 'RD$ 145,280.00')
        self.assertEqual(moneda_rd(Decimal('12890.50')), 'RD$ 12,890.50')

    def test_user_profile_in_topbar_and_clean_sidebar(self):
        self.user.rol = Usuario.Rol.ADMIN
        response = self.response()
        # Topbar contains real user name, role, and logout dropdown
        self.assertContains(response, 'data-user-menu')
        self.assertContains(response, self.user.get_full_name() or self.user.get_username())
        self.assertContains(response, 'Administrador')
        self.assertContains(response, 'data-user-dropdown')
        self.assertContains(response, 'action="/acceso/cerrar-sesion/"')
        self.assertContains(response, 'Cerrar sesión')

        # Sidebar does NOT contain redundant Nueva factura buttons or user footer
        content = response.content.decode()
        sidebar_html = content[content.find('<aside class="sidebar"'):content.find('</aside>')]
        self.assertNotIn('sidebar-create', sidebar_html)
        self.assertNotIn('sidebar-footer', sidebar_html)
        self.assertNotIn('Nueva factura', sidebar_html)

        # Right side dashboard header preserves Nueva factura button
        self.assertContains(response, 'href="/facturas/nueva/"')

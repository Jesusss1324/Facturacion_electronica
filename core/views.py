"""Inicio y componentes de interfaz compartidos."""

from zoneinfo import ZoneInfo

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views import View
from django.views.generic import RedirectView, TemplateView

from frontend_data import get_repository


from .legal_data import MARCO_LEGAL


class MarcoLegalView(LoginRequiredMixin, TemplateView):
    """Pantalla UI-20: Marco legal y normativo que sustenta el sistema e-CF."""
    template_name = 'core/marco_legal.html'
    http_method_names = ['get', 'head', 'options']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filtro_tipo = self.request.GET.get('tipo', '').strip().lower()
        busqueda = self.request.GET.get('q', '').strip().lower()

        normativas_filtradas = list(MARCO_LEGAL)

        if filtro_tipo in {'ley', 'norma', 'estandar', 'decreto'}:
            normativas_filtradas = [n for n in normativas_filtradas if n['tipo'] == filtro_tipo]

        if busqueda:
            normativas_filtradas = [
                n for n in normativas_filtradas
                if busqueda in n['codigo'].lower()
                or busqueda in n['titulo'].lower()
                or busqueda in n['resumen'].lower()
                or busqueda in n['impacto_sistema'].lower()
            ]

        context.update({
            'total_normativas': len(MARCO_LEGAL),
            'normativas': normativas_filtradas,
            'filtro_tipo': filtro_tipo,
            'busqueda': busqueda,
            'conteos': {
                'todas': len(MARCO_LEGAL),
                'ley': sum(1 for n in MARCO_LEGAL if n['tipo'] == 'ley'),
                'norma': sum(1 for n in MARCO_LEGAL if n['tipo'] == 'norma'),
                'estandar': sum(1 for n in MARCO_LEGAL if n['tipo'] == 'estandar'),
                'decreto': sum(1 for n in MARCO_LEGAL if n['tipo'] == 'decreto'),
            },
        })
        return context


class InicioView(LoginRequiredMixin, TemplateView):
    template_name = 'core/inicio.html'
    http_method_names = ['get', 'head', 'options']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        repository = get_repository()
        hour = timezone.localtime(timezone.now(), ZoneInfo('America/Santo_Domingo')).hour
        saludo = 'Buenos días' if hour < 12 else 'Buenas tardes' if hour < 19 else 'Buenas noches'
        context.update({
            'saludo': saludo,
            'nombre_usuario': self.request.user.get_short_name() or self.request.user.get_username(),
            'resumen': repository.resumen_inicio(),
            'facturas_recientes': repository.recent_facturas(limit=5),
        })
        return context


class PendingScreenView(TemplateView):
    template_name = 'core/pending.html'
    layout_template = 'layouts/public.html'
    http_method_names = ['get', 'head', 'options']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['layout_template'] = self.layout_template
        return context

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        response.status_code = 501
        return response


class ProtectedPendingScreenView(LoginRequiredMixin, PendingScreenView):
    layout_template = 'layouts/app.html'


class ProtectedRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False
    http_method_names = ['get', 'head', 'options']


class PendingActionView(LoginRequiredMixin, View):
    """Reserva una acción POST sin modificar registros ni anunciar éxito."""

    http_method_names = ['post', 'options']

    def post(self, request, *args, **kwargs):
        return HttpResponse('Esta operación todavía no está disponible.', status=501)


class PendingDownloadView(LoginRequiredMixin, View):
    http_method_names = ['get', 'head', 'options']

    def get(self, request, *args, **kwargs):
        return HttpResponse('El documento todavía no está disponible.', status=501)


def bad_request(request, exception):
    return render(request, 'errors/400.html', status=400)


def permission_denied(request, exception):
    return render(request, 'errors/403.html', status=403)


def page_not_found(request, exception):
    return render(request, 'errors/404.html', status=404)


def server_error(request):
    return render(request, 'errors/500.html', status=500)

from datetime import datetime
import unicodedata
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import Http404, HttpResponseBadRequest, HttpResponseRedirect
from django.urls import reverse
from django.views import View
from django.views.generic import FormView, TemplateView

from frontend_data import get_repository
from .forms import CrearClienteForm, EditarClienteForm


class CrearClienteView(LoginRequiredMixin, FormView):
    template_name = 'clientes/crear.html'
    form_class = CrearClienteForm
    http_method_names = ['get', 'post', 'head', 'options']

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), 'repository': get_repository()}

    def form_valid(self, form):
        datos = {**form.cleaned_data}
        if datos['tipo_identificacion'] == 'CEDULA':
            datos['tipo_identificacion'] = 'Cédula'
        try:
            cliente = form.repository.create_cliente(**datos)
        except ValueError:
            form.duplicate = form.repository.find_cliente_by_identificacion(form.cleaned_data['identificacion'])
            form.add_error('identificacion', 'Esta identificación ya pertenece a un cliente registrado.')
            return self.form_invalid(form)
        messages.success(self.request, f'{cliente.nombre}: cliente registrado correctamente.')
        return HttpResponseRedirect(directory_url())


class EditarClienteView(LoginRequiredMixin, FormView):
    template_name = 'clientes/editar.html'
    form_class = EditarClienteForm
    http_method_names = ['get', 'post', 'head', 'options']

    def dispatch(self, request, *args, **kwargs):
        self.repository = get_repository()
        try:
            self.cliente = self.repository.get_cliente(self.kwargs['pk'])
        except KeyError as error:
            raise Http404('Cliente no encontrado.') from error
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        return {
            'tipo_identificacion': 'RNC' if self.cliente.tipo_identificacion == 'RNC' else 'CEDULA',
            'identificacion': self.cliente.identificacion_display,
            'nombre': self.cliente.nombre,
            'telefono': self.cliente.telefono,
            'email': self.cliente.email,
            'direccion': self.cliente.direccion,
            'activo': '1' if self.cliente.activo else '0',
        }

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['repository'] = self.repository
        kwargs['cliente'] = self.cliente
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        facturas = self.repository.facturas_cliente(self.cliente.id)
        tipos_ecf = self.repository.tipos_ecf_cliente(self.cliente.id)
        context.update(
            cliente=self.cliente,
            facturas_count=len(facturas),
            tipos_ecf=tipos_ecf,
            tipos_ecf_display=', '.join(tipos_ecf) if tipos_ecf else 'E31, E32',
        )
        return context

    def form_valid(self, form):
        datos = {**form.cleaned_data}
        if datos['tipo_identificacion'] == 'CEDULA':
            datos['tipo_identificacion'] = 'Cédula'
        datos['activo'] = datos.get('activo') == '1'
        datos['fecha_modificacion'] = datetime.now(tz=ZoneInfo('America/Santo_Domingo'))
        try:
            cliente = self.repository.update_cliente(self.cliente.id, **datos)
        except ValueError:
            form.duplicate = self.repository.find_cliente_by_identificacion(form.cleaned_data['identificacion'])
            form.add_error('identificacion', 'Esta identificación ya pertenece a otro cliente registrado.')
            return self.form_invalid(form)
        messages.success(self.request, f'{cliente.nombre}: ¡Cambios guardados!')
        return HttpResponseRedirect(reverse('clientes:detalle', kwargs={'pk': cliente.id}))


def normalized(value):
    return ''.join(char for char in unicodedata.normalize('NFKD', value.casefold()) if char.isalnum())


def directory_url(query='', estado='todos', page=1):
    params = {}
    if query:
        params['q'] = query
    if estado in {'activos', 'inactivos'}:
        params['estado'] = estado
    if str(page) != '1':
        params['page'] = page
    return reverse('clientes:listado') + ('?' + urlencode(params) if params else '')


class DirectorioClientesView(LoginRequiredMixin, TemplateView):
    template_name = 'clientes/listado.html'
    http_method_names = ['get', 'head', 'options']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        clientes = get_repository().list_clientes()
        query = self.request.GET.get('q', '').strip()[:150]
        estado = self.request.GET.get('estado', 'todos')
        if estado not in {'todos', 'activos', 'inactivos'}:
            estado = 'todos'
        terms = [normalized(term) for term in query.split() if normalized(term)]
        encontrados = [cliente for cliente in clientes if all(
            term in normalized(cliente.nombre + cliente.identificacion) for term in terms
        )]
        activos = sum(cliente.activo for cliente in encontrados)
        counts = {'todos': len(encontrados), 'activos': activos, 'inactivos': len(encontrados) - activos}
        filtrados = [cliente for cliente in encontrados if estado == 'todos' or cliente.activo == (estado == 'activos')]
        paginator = Paginator(filtrados, 6)
        page = paginator.get_page(self.request.GET.get('page', 1))
        context.update({
            'query': query, 'estado': estado, 'total_clientes': len(clientes),
            'page_obj': page,
            'filtros': [
                {'label': label, 'key': key, 'count': counts[key], 'url': directory_url(query, key)}
                for key, label in [('todos', 'Todos'), ('activos', 'Activos'), ('inactivos', 'Inactivos')]
            ],
            'pagination': [
                {'label': number, 'url': directory_url(query, estado, number) if number != paginator.ELLIPSIS else '', 'current': number == page.number}
                for number in paginator.get_elided_page_range(page.number, on_each_side=1, on_ends=1)
            ],
            'previous_url': directory_url(query, estado, page.previous_page_number()) if page.has_previous() else '',
            'next_url': directory_url(query, estado, page.next_page_number()) if page.has_next() else '',
        })
        return context


class DetalleClienteView(LoginRequiredMixin, TemplateView):
    template_name = 'clientes/detalle.html'
    http_method_names = ['get', 'head', 'options']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        repository = get_repository()
        try:
            cliente = repository.get_cliente(self.kwargs['pk'])
        except KeyError as error:
            raise Http404('Cliente no encontrado.') from error
        context.update(
            cliente=cliente,
            facturas=repository.recent_facturas_cliente(cliente.id),
            tipos_ecf=repository.tipos_ecf_cliente(cliente.id),
        )
        return context


class CambiarEstadoClienteView(LoginRequiredMixin, View):
    http_method_names = ['post', 'options']

    def post(self, request, pk):
        activo = request.POST.get('activo')
        if activo not in {'0', '1'}:
            return HttpResponseBadRequest('El estado solicitado no es válido.')
        try:
            cliente = get_repository().set_cliente_activo(pk, activo == '1')
        except KeyError as error:
            raise Http404('Cliente no encontrado.') from error
        messages.success(request, f'{cliente.nombre}: cliente {"reactivado para emisión de e-CF" if cliente.activo else "inactivado para nuevos e-CF"}.')
        if request.POST.get('volver') == 'detalle':
            return HttpResponseRedirect(reverse('clientes:detalle', kwargs={'pk': pk}))
        return HttpResponseRedirect(directory_url(
            request.POST.get('q', '').strip()[:150],
            request.POST.get('estado', 'todos'),
            request.POST.get('page', '1'),
        ))

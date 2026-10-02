from datetime import timedelta
import unicodedata
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import FormView

from clientes.forms import CrearClienteForm
from frontend_data import get_repository
from .forms import DatosGeneralesForm, SeleccionarTipoForm


def normalized(value):
    return ''.join(char for char in unicodedata.normalize('NFKD', (value or '').casefold()) if char.isalnum())


class TipoComprobanteView(LoginRequiredMixin, FormView):
    template_name = 'comprobantes/tipo.html'
    form_class = SeleccionarTipoForm
    http_method_names = ['get', 'post', 'head', 'options']

    def dispatch(self, request, *args, **kwargs):
        self.repository = get_repository()
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = {'tipo_ecf': '31'}
        tipo = self.request.GET.get('tipo')
        if tipo in {'31', '32'}:
            initial['tipo_ecf'] = tipo

        cliente_param = self.request.GET.get('cliente')
        if cliente_param:
            try:
                cliente = self.repository.get_cliente(int(cliente_param))
                initial['cliente'] = cliente.id
                if not tipo and cliente.tipo_identificacion == 'Cédula':
                    initial['tipo_ecf'] = '32'
            except (ValueError, KeyError):
                pass
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['repository'] = self.repository
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cliente_id = self.request.GET.get('cliente') or self.request.POST.get('cliente')
        if cliente_id:
            try:
                cliente = self.repository.get_cliente(int(cliente_id))
                context['cliente_preseleccionado'] = cliente
            except (ValueError, KeyError):
                pass
        return context

    def form_valid(self, form):
        tipo_ecf = form.cleaned_data['tipo_ecf']
        cliente_id = form.cleaned_data.get('cliente')
        borrador = self.repository.create_borrador(tipo_ecf=tipo_ecf, cliente_id=cliente_id)
        next_url = reverse('comprobantes:cliente', kwargs={'borrador_id': borrador.id})
        if cliente_id:
            next_url += f'?cliente={cliente_id}'
        return HttpResponseRedirect(next_url)


class SeleccionarClienteView(LoginRequiredMixin, View):
    template_name = 'comprobantes/cliente.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.repository = get_repository()
        borrador_id = self.kwargs.get('borrador_id')
        try:
            self.borrador = self.repository.get_borrador(borrador_id)
        except KeyError as error:
            raise Http404('Borrador no encontrado.') from error
        return super().dispatch(request, *args, **kwargs)

    def get_context(self, request, modal_form=None):
        q = request.GET.get('q', '').strip()
        tipo_ecf = self.borrador.tipo_ecf

        # Filtrado fiscal estricto y automático según el tipo de comprobante seleccionado:
        # E31 (Crédito Fiscal) requiere RNC.
        # E32 (Consumidor Final) es exclusivo para personas físicas con Cédula.
        todos = self.repository.list_clientes()
        if tipo_ecf == '32':
            candidatos = [c for c in todos if c.tipo_identificacion in {'CEDULA', 'Cédula'}]
            filtro_label = 'Personas Físicas (Cédula)'
        else:
            candidatos = [c for c in todos if c.tipo_identificacion == 'RNC']
            filtro_label = 'Empresas y Contribuyentes (RNC)'

        if q:
            norm_q = normalized(q)
            filtrados = [
                c for c in candidatos
                if norm_q in normalized(c.nombre) or norm_q in normalized(c.identificacion)
            ]
        else:
            filtrados = list(candidatos)

        cliente_id_param = request.GET.get('cliente') or self.borrador.cliente_id
        cliente_seleccionado = None
        if cliente_id_param:
            try:
                candidate = self.repository.get_cliente(int(cliente_id_param))
                if (tipo_ecf == '32' and candidate.tipo_identificacion in {'CEDULA', 'Cédula'}) or (tipo_ecf == '31' and candidate.tipo_identificacion == 'RNC'):
                    cliente_seleccionado = candidate
            except (ValueError, KeyError, TypeError):
                pass

        if not cliente_seleccionado and not q and filtrados:
            for c in filtrados:
                if c.activo:
                    cliente_seleccionado = c
                    break

        # Paginación (6 tarjetas por página: 3 filas de 2 columnas)
        paginator = Paginator(filtrados, 6)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        def build_page_url(page_num):
            params = {}
            if q:
                params['q'] = q
            if cliente_seleccionado:
                params['cliente'] = cliente_seleccionado.id
            if str(page_num) != '1':
                params['page'] = page_num
            base = reverse('comprobantes:cliente', kwargs={'borrador_id': self.borrador.id})
            return base + ('?' + urlencode(params) if params else '')

        pagination = [
            {
                'label': number,
                'url': build_page_url(number) if number != paginator.ELLIPSIS else '',
                'current': number == page_obj.number,
            }
            for number in paginator.get_elided_page_range(page_obj.number, on_each_side=1, on_ends=1)
        ]
        previous_url = build_page_url(page_obj.previous_page_number()) if page_obj.has_previous() else ''
        next_url = build_page_url(page_obj.next_page_number()) if page_obj.has_next() else ''

        if modal_form is None:
            initial_tipo = 'CEDULA' if tipo_ecf == '32' else 'RNC'
            modal_form = CrearClienteForm(repository=self.repository, initial={'tipo_identificacion': initial_tipo})

        return {
            'borrador': self.borrador,
            'tipo_ecf': tipo_ecf,
            'tipo_display': 'Factura de Crédito Fiscal Electrónica' if tipo_ecf == '31' else 'Factura de Consumo Electrónica',
            'filtro_label': filtro_label,
            'page_obj': page_obj,
            'clientes': page_obj.object_list,
            'pagination': pagination,
            'previous_url': previous_url,
            'next_url': next_url,
            'cliente_seleccionado': cliente_seleccionado,
            'q': q,
            'total_count': len(filtrados),
            'modal_form': modal_form,
        }

    def get(self, request, *args, **kwargs):
        context = self.get_context(request)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        accion = request.POST.get('accion')
        if accion == 'crear_cliente':
            modal_form = CrearClienteForm(request.POST, repository=self.repository)
            if modal_form.is_valid():
                datos = {**modal_form.cleaned_data}
                if datos['tipo_identificacion'] == 'CEDULA':
                    datos['tipo_identificacion'] = 'Cédula'

                # Validación de compatibilidad fiscal según el tipo de comprobante
                if self.borrador.tipo_ecf == '32' and datos['tipo_identificacion'] != 'Cédula':
                    modal_form.add_error(
                        'tipo_identificacion',
                        'Para una Factura de Consumo Electrónica (E32), el receptor debe ser una persona física (Cédula).'
                    )
                    context = self.get_context(request, modal_form=modal_form)
                    context['abrir_modal'] = True
                    return render(request, self.template_name, context)
                elif self.borrador.tipo_ecf == '31' and datos['tipo_identificacion'] != 'RNC':
                    modal_form.add_error(
                        'tipo_identificacion',
                        'Para una Factura de Crédito Fiscal Electrónica (E31), el receptor debe poseer RNC.'
                    )
                    context = self.get_context(request, modal_form=modal_form)
                    context['abrir_modal'] = True
                    return render(request, self.template_name, context)

                nuevo_cliente = self.repository.create_cliente(**datos)
                self.repository.update_borrador(self.borrador.id, cliente_id=nuevo_cliente.id)
                messages.success(request, f'{nuevo_cliente.nombre}: cliente registrado y seleccionado para el comprobante.')
                return HttpResponseRedirect(
                    reverse('comprobantes:cliente', kwargs={'borrador_id': self.borrador.id})
                    + f'?cliente={nuevo_cliente.id}'
                )
            context = self.get_context(request, modal_form=modal_form)
            context['abrir_modal'] = True
            return render(request, self.template_name, context)

        cliente_id = request.POST.get('cliente_id')
        if not cliente_id:
            messages.error(request, 'Debes seleccionar un cliente receptor para continuar.')
            return render(request, self.template_name, self.get_context(request))

        try:
            cliente = self.repository.get_cliente(int(cliente_id))
        except (ValueError, KeyError, TypeError):
            messages.error(request, 'El cliente seleccionado no existe.')
            return render(request, self.template_name, self.get_context(request))

        # Validación fiscal estricta
        if self.borrador.tipo_ecf == '32' and cliente.tipo_identificacion not in {'CEDULA', 'Cédula'}:
            messages.error(
                request,
                'Incompatibilidad fiscal: Para una Factura de Consumo Electrónica (E32), el cliente debe ser una persona física (Cédula).'
            )
            context = self.get_context(request)
            context['restriccion_inactivo'] = True
            return render(request, self.template_name, context)

        if self.borrador.tipo_ecf == '31' and cliente.tipo_identificacion != 'RNC':
            messages.error(
                request,
                'Incompatibilidad fiscal: Para una Factura de Crédito Fiscal Electrónica (E31), el receptor debe poseer RNC habilitado.'
            )
            context = self.get_context(request)
            context['restriccion_inactivo'] = True
            return render(request, self.template_name, context)

        if not cliente.activo:
            messages.error(
                request,
                f'Restricción Fiscal DGII: {cliente.nombre} figura con estado inactivo y no puede ser vinculado a un comprobante e-CF timbrado.'
            )
            context = self.get_context(request)
            context['cliente_seleccionado'] = cliente
            context['restriccion_inactivo'] = True
            return render(request, self.template_name, context)

        self.repository.update_borrador(self.borrador.id, cliente_id=cliente.id)
        return HttpResponseRedirect(
            reverse('comprobantes:datos', kwargs={'borrador_id': self.borrador.id})
        )


class DatosGeneralesView(LoginRequiredMixin, FormView):
    template_name = 'comprobantes/datos.html'
    form_class = DatosGeneralesForm
    http_method_names = ['get', 'post', 'head', 'options']

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.repository = get_repository()
        borrador_id = self.kwargs.get('borrador_id')
        try:
            self.borrador = self.repository.get_borrador(borrador_id)
        except KeyError as error:
            raise Http404('Borrador no encontrado.') from error

        # Si el borrador aún no tiene cliente vinculado, redirigir al paso 2
        if not self.borrador.cliente_id:
            messages.warning(request, 'Debes seleccionar un cliente receptor antes de completar los datos generales.')
            return HttpResponseRedirect(
                reverse('comprobantes:cliente', kwargs={'borrador_id': self.borrador.id})
            )

        try:
            self.cliente = self.repository.get_cliente(self.borrador.cliente_id)
        except KeyError as error:
            raise Http404('Cliente no encontrado.') from error

        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        hoy = timezone.localdate()
        fecha_emision = self.borrador.fecha_emision or hoy
        tipo_pago = self.borrador.tipo_pago or 'contado'
        termino_pago = self.borrador.termino_pago or '30_dias'

        if self.borrador.fecha_vencimiento:
            fecha_vencimiento = self.borrador.fecha_vencimiento
        elif tipo_pago == 'credito':
            fecha_vencimiento = hoy + timedelta(days=30)
        else:
            fecha_vencimiento = hoy + timedelta(days=30)

        forma_pago = self.borrador.forma_pago
        if not forma_pago:
            forma_pago = '04' if tipo_pago == 'credito' else '02'

        return {
            'fecha_emision': fecha_emision,
            'tipo_ingreso': self.borrador.tipo_ingreso or '01',
            'tipo_pago': tipo_pago,
            'termino_pago': termino_pago,
            'fecha_vencimiento': fecha_vencimiento,
            'forma_pago': forma_pago,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'borrador': self.borrador,
            'cliente': self.cliente,
            'tipo_ecf': self.borrador.tipo_ecf,
            'tipo_display': 'Factura de Crédito Fiscal Electrónica' if self.borrador.tipo_ecf == '31' else 'Factura de Consumo Electrónica',
            'secuencia_encf': self.borrador.secuencia_encf_display,
        })
        return context

    def form_valid(self, form):
        datos = {
            'fecha_emision': form.cleaned_data['fecha_emision'],
            'tipo_ingreso': form.cleaned_data['tipo_ingreso'],
            'tipo_pago': form.cleaned_data['tipo_pago'],
            'termino_pago': form.cleaned_data.get('termino_pago') or '',
            'fecha_vencimiento': form.cleaned_data.get('fecha_vencimiento'),
            'forma_pago': form.cleaned_data['forma_pago'],
        }
        self.repository.update_borrador(self.borrador.id, **datos)
        return HttpResponseRedirect(
            reverse('comprobantes:items', kwargs={'borrador_id': self.borrador.id})
        )


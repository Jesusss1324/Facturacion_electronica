from dataclasses import asdict
from uuid import UUID, uuid4

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views import View

from frontend_data import get_repository
from frontend_data.entities import LineaFactura
from .items import LineaFacturaForm, resumen_lineas


class BienesServiciosView(LoginRequiredMixin, View):
    http_method_names = ['get', 'post', 'head', 'options']
    template_name = 'comprobantes/items.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.repository = get_repository()
        try:
            self.borrador = self.repository.get_borrador(kwargs['borrador_id'])
            self.cliente = self.repository.get_cliente(self.borrador.cliente_id) if self.borrador.cliente_id else None
        except KeyError as error:
            raise Http404('Borrador o cliente no encontrado.') from error
        if self.cliente is None or not self.cliente.activo:
            messages.warning(request, 'Selecciona un cliente activo para continuar.')
            return HttpResponseRedirect(reverse('comprobantes:cliente', kwargs=kwargs))
        if not self.borrador.fecha_emision:
            return HttpResponseRedirect(reverse('comprobantes:datos', kwargs=kwargs))
        return super().dispatch(request, *args, **kwargs)

    def context(self, **extra):
        return {'borrador': self.borrador, 'cliente': self.cliente,
                'lineas': self.borrador.lineas, 'resumen': resumen_lineas(self.borrador.lineas),
                'form': LineaFacturaForm(), **extra}

    def line_id(self, value):
        try:
            identifier = UUID(value)
            return next(linea for linea in self.borrador.lineas if linea.id == identifier)
        except (ValueError, TypeError, StopIteration, AttributeError) as error:
            raise Http404('Concepto no encontrado en este borrador.') from error

    def get(self, request, **kwargs):
        editing = self.line_id(request.GET['editar']) if request.GET.get('editar') else None
        form = LineaFacturaForm(initial=asdict(editing)) if editing else LineaFacturaForm()
        return render(request, self.template_name, self.context(form=form, editing=editing,
                      editor_open=bool(editing or request.GET.get('nuevo'))))

    def post(self, request, **kwargs):
        action = request.POST.get('accion')
        if action not in {'guardar', 'quitar', 'continuar', 'previsualizar'}:
            return HttpResponseBadRequest('Acción no válida.')
        if action == 'continuar':
            if not self.borrador.lineas:
                return render(request, self.template_name, self.context(error='Agrega al menos un bien o servicio para continuar.'))
            return HttpResponseRedirect(reverse('comprobantes:totales', kwargs=kwargs))
        editing = self.line_id(request.POST['linea_id']) if request.POST.get('linea_id') else None
        try:
            revision = int(request.POST.get('revision', ''))
        except ValueError:
            return HttpResponseBadRequest('Versión del borrador no válida.')
        if action == 'quitar':
            if editing is None:
                return HttpResponseBadRequest('Selecciona un concepto.')
            try:
                self.repository.quitar_linea(self.borrador.id, editing.id, revision)
            except (ValueError, KeyError):
                return render(request, self.template_name, self.context(error='El borrador cambió. Recarga la página antes de continuar.'), status=409)
            messages.success(request, 'Concepto eliminado de la factura.')
            return HttpResponseRedirect(request.path)
        form = LineaFacturaForm(request.POST)
        if form.is_valid():
            linea = LineaFactura(id=editing.id if editing else uuid4(), **form.cleaned_data)
            if action == 'previsualizar':
                lineas = tuple(linea if item.id == linea.id else item for item in self.borrador.lineas) if editing else (*self.borrador.lineas, linea)
                html = render_to_string('comprobantes/includes/items_preview.html', self.context(lineas=lineas, resumen=resumen_lineas(lineas), preview_pending=True), request=request)
                return JsonResponse({'html': html})
            try:
                self.repository.guardar_linea(self.borrador.id, linea, revision, editar=bool(editing))
            except (ValueError, KeyError) as error:
                form.add_error(None, str(error) if isinstance(error, ValueError) else 'El concepto ya no existe. Recarga la página.')
            else:
                messages.success(request, 'Concepto actualizado.' if editing else 'Concepto agregado a la factura.')
                return HttpResponseRedirect(request.path)
        if action == 'previsualizar':
            return JsonResponse({'errors': form.errors.get_json_data()}, status=422)
        return render(request, self.template_name, self.context(form=form, editing=editing, editor_open=True))

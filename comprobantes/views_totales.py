from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views import View

from frontend_data import get_repository
from .totales import huella_borrador, revisar_borrador


class TotalesCondicionesView(LoginRequiredMixin, View):
    http_method_names = ['get', 'post', 'head', 'options']
    template_name = 'comprobantes/totales.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.repository = get_repository()
        try:
            self.borrador = self.repository.get_borrador(kwargs['borrador_id'])
            self.cliente = self.repository.get_cliente(self.borrador.cliente_id) if self.borrador.cliente_id else None
        except KeyError as error:
            raise Http404('Borrador o cliente no encontrado.') from error
        destino = None
        if self.cliente is None or not self.cliente.activo:
            destino = 'comprobantes:cliente'
        elif not self.borrador.fecha_emision:
            destino = 'comprobantes:datos'
        elif not self.borrador.lineas:
            destino = 'comprobantes:items'
        if destino:
            messages.warning(request, 'Completa el paso anterior para revisar los totales.')
            return HttpResponseRedirect(reverse(destino, kwargs=kwargs))
        return super().dispatch(request, *args, **kwargs)

    def context(self, **extra):
        resumen, errores = revisar_borrador(self.borrador)
        huella = huella_borrador(self.borrador)
        guardados = dict(self.borrador.totales_guardados) if self.borrador.totales_guardados is not None else None
        inconsistente = guardados is not None and (guardados != resumen or self.borrador.huella_totales != huella)
        diferencia = abs(guardados.get('total', Decimal('0')) - resumen['total']) if guardados and resumen else Decimal('0')
        return {'borrador': self.borrador, 'cliente': self.cliente, 'resumen': resumen,
                'errores': errores, 'huella': huella, 'inconsistente': inconsistente,
                'diferencia': diferencia, 'bloqueado': bool(errores or inconsistente), **extra}

    def get(self, request, **kwargs):
        return render(request, self.template_name, self.context())

    def post(self, request, **kwargs):
        action = request.POST.get('accion')
        if action not in {'guardar', 'recalcular', 'continuar'}:
            return HttpResponseBadRequest('Acción no válida.')
        try:
            self.repository.guardar_totales(self.borrador.id, request.POST.get('huella', ''), recalcular=action == 'recalcular')
        except ValueError as error:
            self.borrador = self.repository.get_borrador(self.borrador.id)
            self.cliente = self.repository.get_cliente(self.borrador.cliente_id)
            return render(request, self.template_name, self.context(error=str(error)), status=409)
        if action == 'continuar':
            return HttpResponseRedirect(reverse('comprobantes:revision', kwargs=kwargs))
        messages.success(request, 'Importes recalculados y actualizados.' if action == 'recalcular' else 'Borrador guardado correctamente.')
        return HttpResponseRedirect(request.path)

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views import View

from frontend_data import get_repository


class EmitirComprobanteView(LoginRequiredMixin, View):
    """Acción POST para emitir y timbrar formalmente un borrador e-CF."""
    http_method_names = ['post', 'options']

    def post(self, request, *args, **kwargs):
        repository = get_repository()
        borrador_id = kwargs.get('borrador_id')
        try:
            borrador = repository.get_borrador(borrador_id)
        except KeyError as error:
            raise Http404('Borrador no encontrado.') from error

        huella = request.POST.get('huella', '')

        try:
            factura = repository.emitir_factura(borrador_id, huella=huella or None)
        except ValueError as error:
            messages.error(request, str(error))
            return HttpResponseRedirect(
                reverse('comprobantes:revision', kwargs={'borrador_id': borrador_id})
            )

        messages.success(request, f'Comprobante {factura.e_ncf} emitido exitosamente.')
        return HttpResponseRedirect(
            reverse('comprobantes:procesamiento', kwargs={'pk': factura.id})
        )


class ProcesamientoFacturaView(LoginRequiredMixin, View):
    """Pantalla UI-13: Monitoreo y procesamiento de la emisión e-CF."""
    http_method_names = ['get', 'head', 'options']
    template_name = 'comprobantes/procesamiento.html'

    def get(self, request, *args, **kwargs):
        repository = get_repository()
        pk = kwargs.get('pk')
        try:
            factura = repository.get_factura(pk)
            cliente = repository.get_cliente(factura.cliente_id)
        except KeyError as error:
            raise Http404('Factura o cliente no encontrado.') from error

        simular_error = request.GET.get('simular_error')
        if simular_error == 'validacion' or factura.estado == 'rechazado':
            estado_vista = 'error_validacion'
        elif simular_error == 'timeout':
            estado_vista = 'error_timeout'
        elif request.GET.get('estado') == 'completado':
            estado_vista = 'completado'
        else:
            estado_vista = 'procesando'

        huella = factura.huella_seguridad or 'sello-local-sha256'
        huella_corta = f'{huella[:12]}...{huella[-6:]}' if len(huella) >= 18 else huella

        pasos_pipeline = [
            {'num': 1, 'nombre': 'Preparar', 'fase': '1/6'},
            {'num': 2, 'nombre': 'XML e-CF', 'fase': '2/6'},
            {'num': 3, 'nombre': 'Validación', 'fase': '3/6'},
            {'num': 4, 'nombre': 'Firma', 'fase': '4/6'},
            {'num': 5, 'nombre': 'Envío', 'fase': '5/6'},
            {'num': 6, 'nombre': 'Acuse', 'fase': '6/6'},
        ]

        context = {
            'factura': factura,
            'cliente': cliente,
            'track_id': factura.track_id_display,
            'total_conceptos': factura.total_conceptos,
            'huella_corta': huella_corta,
            'estado_vista': estado_vista,
            'pasos_pipeline': pasos_pipeline,
        }
        return render(request, self.template_name, context)

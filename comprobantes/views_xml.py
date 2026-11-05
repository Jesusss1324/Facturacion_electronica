from frontend_data.configuration import get_emisor_info
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.views import View

from frontend_data import get_repository



def construir_xml_factura(factura, cliente, emisor=None) -> str:
    """Representación XML local, sin firma digital ni certificación fiscal."""
    from django.conf import settings
    if settings.FRONTEND_DATA_BACKEND == 'sqlite':
        operacion = get_repository().get_operacion_factura(factura.id)
        if operacion is not None:
            from frontend_data.emission import xml_operacion
            return operacion.xml or xml_operacion(operacion)
    emisor = emisor if emisor is not None else get_emisor_info()
    from .items import resumen_lineas
    from .xml_document import construir_documento
    if factura.lineas:
        resumen = resumen_lineas(factura.lineas)
    else:
        base = (factura.monto_total / Decimal('1.18')).quantize(Decimal('0.01'))
        resumen = dict(bruto=base, descuento=Decimal('0.00'), base=base,
                       itbis=factura.monto_total - base, total=factura.monto_total)
    return construir_documento(factura, cliente, emisor, factura.lineas, resumen, factura.e_ncf)


class DocumentoXmlView(LoginRequiredMixin, View):
    """Pantalla UI-16: Visualizador del XML representativo local, sin firma digital."""
    http_method_names = ['get', 'head', 'options']
    template_name = 'comprobantes/xml.html'

    def get(self, request, pk, *args, **kwargs):
        repository = get_repository()
        try:
            factura = repository.get_factura(pk)
            cliente = repository.get_cliente(factura.cliente_id)
        except KeyError as error:
            raise Http404('Factura o cliente no encontrado.') from error

        # Generar XML completo
        xml_raw = construir_xml_factura(factura, cliente)
        lineas_xml = [(idx + 1, line) for idx, line in enumerate(xml_raw.splitlines())]
        tamano_kb = f'{len(xml_raw.encode("utf-8")) / 1024:.2f}'

        operacion = repository.get_operacion_factura(factura.id)
        # Estado del comprobante
        simular = None if operacion else (request.GET.get('simular_estado') or request.GET.get('estado'))
        if simular in {'aprobado', 'rechazado', 'anulado'}:
            estado = simular
        else:
            estado = factura.estado

        context = {
            'factura': factura,
            'cliente': cliente,
            'emisor': get_emisor_info(),
            'xml_raw': xml_raw,
            'lineas_xml': lineas_xml,
            'total_lineas': len(lineas_xml),
            'tamano_kb': tamano_kb,
            'estado': estado,
            'es_aprobado': estado == 'aprobado',
            'es_rechazado': estado == 'rechazado',
            'es_anulado': estado == 'anulado',
            'track_id': factura.track_id_display,
        }
        return render(request, self.template_name, context)


class DescargarXmlView(LoginRequiredMixin, View):
    """Descarga del XML local de demostración."""
    http_method_names = ['get', 'head', 'options']

    def get(self, request, pk, *args, **kwargs):
        repository = get_repository()
        try:
            factura = repository.get_factura(pk)
            cliente = repository.get_cliente(factura.cliente_id)
        except KeyError as error:
            raise Http404('Factura o cliente no encontrado.') from error

        xml_raw = construir_xml_factura(factura, cliente)
        filename = f'e-CF_{factura.e_ncf}.xml'
        response = HttpResponse(xml_raw, content_type='application/xml; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

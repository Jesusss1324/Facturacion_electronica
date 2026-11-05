from frontend_data.configuration import get_emisor_info
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import render
from django.views import View

from frontend_data import get_repository
from .revision import monto_en_letras



class RepresentacionImpresaPdfView(LoginRequiredMixin, View):
    """Pantalla UI-17: Visor de representación impresa de demostración."""
    http_method_names = ['get', 'head', 'options']
    template_name = 'comprobantes/pdf.html'

    def get_context(self, request, pk):
        repository = get_repository()
        try:
            factura = repository.get_factura(pk)
            cliente = repository.get_cliente(factura.cliente_id)
        except KeyError as error:
            raise Http404('Factura o cliente no encontrado.') from error

        operacion = repository.get_operacion_factura(factura.id)
        emisor = get_emisor_info()
        if operacion is not None:
            from frontend_data.emission import _snapshot_entity
            from frontend_data.entities import Cliente
            cliente = _snapshot_entity(operacion.instantanea['cliente'], Cliente)
            emisor = operacion.instantanea['emisor']

        # Estado del comprobante
        simular = None if operacion else (request.GET.get('simular_estado') or request.GET.get('estado'))
        if simular in {'aprobado', 'rechazado', 'anulado'}:
            estado = simular
        else:
            estado = factura.estado

        # Fechas
        fecha_emision = factura.fecha_emision
        if hasattr(fecha_emision, 'astimezone'):
            fecha_display = fecha_emision.astimezone(ZoneInfo('America/Santo_Domingo')).strftime('%d/%m/%Y - %H:%M')
            fecha_corta = fecha_emision.astimezone(ZoneInfo('America/Santo_Domingo')).strftime('%d/%m/%Y')
        elif hasattr(fecha_emision, 'strftime'):
            fecha_display = fecha_emision.strftime('%d/%m/%Y - %H:%M')
            fecha_corta = fecha_emision.strftime('%d/%m/%Y')
        else:
            fecha_display = str(fecha_emision)
            fecha_corta = str(fecha_emision).split(' ')[0]

        total = factura.monto_total

        if factura.lineas:
            items = []
            subtotal_bruto = Decimal('0.00')
            descuento_total = Decimal('0.00')
            base_imponible = Decimal('0.00')
            itbis_total = Decimal('0.00')

            for idx, linea in enumerate(factura.lineas, start=1):
                bruto = linea.bruto
                base = bruto - linea.descuento
                itbis_liq = linea.itbis
                subtotal_bruto += bruto
                descuento_total += linea.descuento
                base_imponible += base
                itbis_total += itbis_liq

                items.append({
                    'numero': f'{idx:02d}',
                    'concepto': linea.concepto,
                    'descripcion': linea.descripcion,
                    'unidad_display': 'Glb' if linea.tipo == 'servicio' else 'Ud',
                    'cantidad': linea.cantidad,
                    'precio': linea.precio,
                    'descuento': linea.descuento,
                    'itbis_pct': '18%',
                    'itbis_liq': itbis_liq,
                    'total_neto': base + itbis_liq,
                })
        else:
            base_imponible = (total / Decimal('1.18')).quantize(Decimal('0.01'))
            itbis_total = total - base_imponible
            subtotal_bruto = base_imponible
            descuento_total = Decimal('0.00')
            items = [
                {
                    'numero': '01',
                    'concepto': 'Servicios Profesionales Especializados en Tecnología',
                    'descripcion': 'Honorarios profesionales e infraestructura digital',
                    'unidad_display': 'Glb',
                    'cantidad': Decimal('1.00'),
                    'precio': base_imponible,
                    'descuento': Decimal('0.00'),
                    'itbis_pct': '18%',
                    'itbis_liq': itbis_total,
                    'total_neto': total,
                }
            ]

        # Monto formal en letras
        texto_letras = monto_en_letras(total).upper()
        texto_letras = texto_letras.replace('PESOS DOMINICANOS CON', 'PESOS CON').replace('PESO DOMINICANO CON', 'PESO CON')
        cantidad_en_letras = f'"{texto_letras}"'

        context = {
            'factura': factura,
            'cliente': cliente,
            'emisor': emisor,
            'estado': estado,
            'es_aprobado': estado == 'aprobado',
            'es_rechazado': estado == 'rechazado',
            'es_anulado': estado == 'anulado',
            'fecha_display': fecha_display,
            'fecha_corta': fecha_corta,
            'vencimiento_secuencia': factura.vencimiento_secuencia,
            'items': items,
            'subtotal_bruto': subtotal_bruto,
            'descuento_total': descuento_total,
            'base_imponible': base_imponible,
            'itbis_total': itbis_total,
            'monto_exento': Decimal('0.00'),
            'monto_total': total,
            'cantidad_en_letras': cantidad_en_letras,
            'track_id': factura.track_id_display,
        }
        return context

    def get(self, request, pk, *args, **kwargs):
        return render(request, self.template_name, self.get_context(request, pk))


class DescargarPdfView(RepresentacionImpresaPdfView):
    """Descarga PDF de demostración con los mismos datos que el visor."""
    def get(self, request, pk, *args, **kwargs):
        from django.http import HttpResponse
        from .pdf_document import construir_pdf
        context = self.get_context(request, pk)
        response = HttpResponse(construir_pdf(context), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="e-CF_{context["factura"].e_ncf}.pdf"'
        return response

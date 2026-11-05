from frontend_data.configuration import get_emisor_info
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import render
from django.views import View

from frontend_data import get_repository
from .revision import monto_en_letras



class DetalleFacturaView(LoginRequiredMixin, View):
    """Pantalla UI-15: Detalle formal del comprobante fiscal emitido (e-CF)."""
    http_method_names = ['get', 'head', 'options']
    template_name = 'comprobantes/detalle.html'

    def get(self, request, pk, *args, **kwargs):
        repository = get_repository()
        try:
            factura = repository.get_factura(pk)
            cliente = repository.get_cliente(factura.cliente_id)
        except KeyError as error:
            raise Http404('Factura o cliente no encontrado.') from error

        operacion = repository.get_operacion_factura(factura.id)
        # Estado del comprobante (permite preview mediante simular_estado o estado)
        simular = None if operacion else (request.GET.get('simular_estado') or request.GET.get('estado'))
        if simular in {'aprobado', 'rechazado', 'anulado'}:
            estado = simular
        else:
            estado = factura.estado

        # Formato de fecha
        fecha_emision = factura.fecha_emision
        if hasattr(fecha_emision, 'astimezone'):
            fecha_display = fecha_emision.astimezone(ZoneInfo('America/Santo_Domingo')).strftime('%d/%m/%Y - %H:%M')
            fecha_solo_dia = fecha_emision.astimezone(ZoneInfo('America/Santo_Domingo')).strftime('%d/%m/%Y')
        elif hasattr(fecha_emision, 'strftime'):
            fecha_display = fecha_emision.strftime('%d/%m/%Y - %H:%M')
            fecha_solo_dia = fecha_emision.strftime('%d/%m/%Y')
        else:
            fecha_display = str(fecha_emision)
            fecha_solo_dia = str(fecha_emision).split(' ')[0]

        # Datos de anulación o rechazo
        acta_anulacion = factura.acta_anulacion or f'ANU-2026-{1000 + factura.id:04d}'
        fecha_anulacion = factura.fecha_anulacion or fecha_solo_dia
        causal_anulacion = factura.causal_anulacion or '02 - Modificación de plazo de pago acordado.'
        regla_error = 'RN-008' if factura.id % 2 == 0 else 'RN-032'
        motivo_error = (
            f'El RNC receptor ({cliente.identificacion_display}) no se encuentra en estado Activo en el padrón DGII al momento de la firma.'
            if regla_error == 'RN-008' else
            'Inconsistencia en Cálculo de ITBIS: El valor declarado en los montos de impuestos no coincide con la alícuota legal del 18% para ítems gravados.'
        )

        # Construcción de ítems y liquidación
        total = factura.monto_total

        if factura.lineas:
            # Factura emitida a partir de borrador con líneas
            items = []
            subtotal_bruto = Decimal('0.00')
            descuento_total = Decimal('0.00')
            base_imponible = Decimal('0.00')
            itbis_total = Decimal('0.00')

            for idx, linea in enumerate(factura.lineas, start=1):
                bruto = (linea.cantidad * linea.precio).quantize(Decimal('0.01'))
                base = bruto - linea.descuento
                itbis_liq = (base * Decimal('0.18')).quantize(Decimal('0.01'))
                neto = base + itbis_liq

                subtotal_bruto += bruto
                descuento_total += linea.descuento
                base_imponible += base
                itbis_total += itbis_liq

                items.append({
                    'numero': f'{idx:02d}',
                    'concepto': linea.concepto,
                    'descripcion': linea.descripcion,
                    'unidad_display': 'Glb' if linea.tipo == 'servicio' else 'Ud',
                    'tipo_unidad': f'({linea.tipo_display})',
                    'cantidad': linea.cantidad,
                    'precio': linea.precio,
                    'descuento': linea.descuento,
                    'itbis_pct': '18%',
                    'itbis_liq': itbis_liq,
                    'total_neto': neto,
                })
            monto_total_calc = base_imponible + itbis_total
        else:
            # Factura del fixture con desglose proporcional
            base = (total / Decimal('1.18')).quantize(Decimal('0.01'))
            itbis = total - base
            subtotal_bruto = base
            descuento_total = Decimal('0.00')
            base_imponible = base
            itbis_total = itbis
            monto_total_calc = total

            items = [
                {
                    'numero': '01',
                    'concepto': 'Servicios Profesionales Especializados en Tecnología',
                    'descripcion': 'Honorarios profesionales y consultoría en infraestructura digital',
                    'unidad_display': 'Glb',
                    'tipo_unidad': '(Servicio)',
                    'cantidad': Decimal('1.00'),
                    'precio': base,
                    'descuento': Decimal('0.00'),
                    'itbis_pct': '18%',
                    'itbis_liq': itbis,
                    'total_neto': total,
                }
            ]

        # Monto formal en letras
        texto_letras = monto_en_letras(monto_total_calc).upper()
        texto_letras = texto_letras.replace('PESOS DOMINICANOS CON', 'PESOS CON').replace('PESO DOMINICANO CON', 'PESO CON')
        cantidad_en_letras = f'"{texto_letras}"'

        context = {
            'factura': factura,
            'cliente': cliente,
            'emisor': get_emisor_info(),
            'estado': estado,
            'es_aprobado': estado == 'aprobado',
            'es_rechazado': estado == 'rechazado',
            'es_anulado': estado == 'anulado',
            'fecha_display': fecha_display,
            'vencimiento_secuencia': factura.vencimiento_secuencia,
            'items': items,
            'subtotal_bruto': subtotal_bruto,
            'descuento_total': descuento_total,
            'base_imponible': base_imponible,
            'itbis_total': itbis_total,
            'monto_exento': Decimal('0.00'),
            'monto_total': monto_total_calc,
            'cantidad_en_letras': cantidad_en_letras,
            'regla_error': regla_error,
            'motivo_error': motivo_error,
            'acta_anulacion': acta_anulacion,
            'fecha_anulacion': fecha_anulacion,
            'causal_anulacion': causal_anulacion,
        }
        return render(request, self.template_name, context)

import csv
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import HttpResponse
from django.shortcuts import render
from django.views import View

from frontend_data import get_repository
from frontend_data.entities import ResumenFactura

EMISOR_INFO = {
    'razon_social': 'SOLUCIONES TECNOLÓGICAS DEL CARIBE, SRL',
    'nombre_comercial': 'Soluciones Tecnológicas del Caribe',
    'rnc': '1-30-98765-4',
    'rnc_raw': '130987654',
    'direccion': 'Av. Winston Churchill #1099, Torre Empresarial Piantini, Piso 14',
    'sucursal': '01 Principal D.N.',
}


def obtener_items_resumen(factura):
    """Retorna lista simplificada de ítems para el expediente lateral."""
    total = factura.monto_total
    if factura.lineas:
        items = []
        for idx, linea in enumerate(factura.lineas, start=1):
            items.append({
                'numero': f'{idx:02d}',
                'concepto': linea.concepto,
                'cantidad': linea.cantidad,
                'monto': linea.total,
                'itbis_nota': 'ITBIS 18% · Gravado',
            })
        subtotal = sum(l.base for l in factura.lineas)
        return items, subtotal
    elif total == Decimal('336890.00'):
        items = [
            {
                'numero': '01',
                'concepto': 'Licencia de Software Empresarial e-CF v2',
                'cantidad': Decimal('2.00'),
                'monto': Decimal('210000.00'),
                'itbis_nota': 'ITBIS 18% · Gravado',
            },
            {
                'numero': '02',
                'concepto': 'Servicios de Consultoría de Integración Fiscal',
                'cantidad': Decimal('1.00'),
                'monto': Decimal('75500.00'),
                'itbis_nota': 'ITBIS 18% · Gravado',
            },
            {
                'numero': '03',
                'concepto': 'Mantenimiento de Servidores Mock DGII',
                'cantidad': Decimal('1.00'),
                'monto': Decimal('51390.00'),
                'itbis_nota': 'ITBIS Exento',
            },
        ]
        return items, Decimal('285500.00')
    else:
        base = (total / Decimal('1.18')).quantize(Decimal('0.01'))
        items = [
            {
                'numero': '01',
                'concepto': 'Servicios Profesionales Especializados en Tecnología',
                'cantidad': Decimal('1.00'),
                'monto': total,
                'itbis_nota': 'ITBIS 18% · Gravado',
            }
        ]
        return items, base


class HistorialFacturasView(LoginRequiredMixin, View):
    """Pantalla UI-18: Historial y archivo inmutable de facturas con expediente activo."""
    http_method_names = ['get', 'head', 'options']
    template_name = 'comprobantes/historial.html'

    def get(self, request, *args, **kwargs):
        repository = get_repository()
        facturas = repository.list_facturas()
        clientes_map = {c.id: c for c in repository.list_clientes()}

        # 1. Contadores globales para pestañas rápidas
        cuenta_todos = len(facturas)
        cuenta_e31 = sum(1 for f in facturas if f.tipo_ecf == '31')
        cuenta_e32 = sum(1 for f in facturas if f.tipo_ecf == '32')
        cuenta_aprobados = sum(1 for f in facturas if f.estado == 'aprobado')
        cuenta_rechazados = sum(1 for f in facturas if f.estado == 'rechazado')

        # 2. Captura de parámetros de filtrado
        query = (request.GET.get('q') or '').strip().lower()
        tipo_ecf = (request.GET.get('tipo_ecf') or '').strip()
        estado = (request.GET.get('estado') or '').strip()
        fecha_desde_str = (request.GET.get('fecha_desde') or '').strip()
        fecha_hasta_str = (request.GET.get('fecha_hasta') or '').strip()
        filtro_rapido = (request.GET.get('filtro') or 'todos').strip()
        vista = (request.GET.get('vista') or 'dividida').strip()  # 'dividida' o 'tabla'

        # Atajos de filtro rápido (pills)
        if filtro_rapido == 'e31':
            tipo_ecf = '31'
        elif filtro_rapido == 'e32':
            tipo_ecf = '32'
        elif filtro_rapido == 'aprobados':
            estado = 'aprobado'
        elif filtro_rapido == 'rechazados':
            estado = 'rechazado'

        # 3. Aplicación de filtros sobre facturas
        resumenes = []
        query_clean = query.replace('-', '').replace(' ', '')

        for factura in facturas:
            cliente = clientes_map.get(factura.cliente_id)
            if not cliente:
                continue

            # Filtro por tipo e-CF
            if tipo_ecf and factura.tipo_ecf != tipo_ecf:
                continue

            # Filtro por estado
            if estado and factura.estado != estado:
                continue

            # Filtro por fechas
            f_fecha = factura.fecha_emision
            if hasattr(f_fecha, 'date'):
                f_date = f_fecha.date()
            else:
                f_date = datetime.strptime(str(f_fecha)[:10], '%Y-%m-%d').date()

            if fecha_desde_str:
                try:
                    d_desde = datetime.strptime(fecha_desde_str, '%Y-%m-%d').date()
                    if f_date < d_desde:
                        continue
                except ValueError:
                    pass

            if fecha_hasta_str:
                try:
                    d_hasta = datetime.strptime(fecha_hasta_str, '%Y-%m-%d').date()
                    if f_date > d_hasta:
                        continue
                except ValueError:
                    pass

            # Búsqueda de texto (e-NCF, RNC/Cédula, nombre cliente o track_id)
            if query:
                nombre_match = query in cliente.nombre.lower()
                encf_match = query in factura.e_ncf.lower()
                track_match = query in factura.track_id_display.lower()
                id_raw = cliente.identificacion.replace('-', '')
                id_match = (query in cliente.identificacion.lower()) or (query_clean in id_raw)
                if not (nombre_match or encf_match or track_match or id_match):
                    continue

            resumenes.append(ResumenFactura(factura=factura, cliente=cliente))

        # 4. Exportar a CSV si fue solicitado
        if request.GET.get('export') == 'csv':
            response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
            response['Content-Disposition'] = 'attachment; filename="Historial_Facturas_eCF.csv"'
            writer = csv.writer(response)
            writer.writerow([
                'e-NCF', 'Tipo e-CF', 'Tipo Documento', 'RNC/Cédula Receptor',
                'Razón Social Receptor', 'Fecha Emisión', 'Monto Total (DOP)',
                'Estado DGII', 'TrackId DGII'
            ])
            for item in resumenes:
                writer.writerow([
                    item.factura.e_ncf,
                    f'E{item.factura.tipo_ecf}',
                    item.factura.tipo_display,
                    item.cliente.identificacion_display,
                    item.cliente.nombre,
                    item.factura.fecha_emision.strftime('%d/%m/%Y %H:%M') if hasattr(item.factura.fecha_emision, 'strftime') else str(item.factura.fecha_emision),
                    f'{item.factura.monto_total:.2f}',
                    item.factura.estado_display,
                    item.factura.track_id_display,
                ])
            return response

        # 5. Paginación (8 comprobantes por página según mockups)
        page_size = 8
        try:
            req_size = int(request.GET.get('mostrar', 8))
            if req_size in {8, 10, 20, 50}:
                page_size = req_size
        except (ValueError, TypeError):
            page_size = 8

        paginator = Paginator(resumenes, page_size)
        page_number = request.GET.get('page', 1)
        try:
            page_obj = paginator.page(page_number)
        except (PageNotAnInteger, EmptyPage):
            page_obj = paginator.page(1)

        # 6. Expediente activo seleccionado para el panel lateral
        selected_id = request.GET.get('selected_id')
        selected_resumen = None
        if selected_id:
            try:
                sid = int(selected_id)
                selected_resumen = next((r for r in resumenes if r.factura.id == sid), None)
            except ValueError:
                selected_resumen = None

        if not selected_resumen and page_obj.object_list:
            selected_resumen = page_obj.object_list[0]

        expediente = None
        if selected_resumen:
            f = selected_resumen.factura
            c = selected_resumen.cliente
            items_list, subtotal_gravado = obtener_items_resumen(f)
            expediente = {
                'factura': f,
                'cliente': c,
                'emisor': EMISOR_INFO,
                'items': items_list,
                'total_items': len(items_list),
                'subtotal_gravado': subtotal_gravado,
                'es_aprobado': f.estado == 'aprobado',
                'es_rechazado': f.estado == 'rechazado',
                'es_anulado': f.estado == 'anulado',
            }

        # Etiquetas de filtros activos
        filtros_activos = []
        if tipo_ecf:
            filtros_activos.append({'clave': 'tipo_ecf', 'label': f'Tipo: E{tipo_ecf}'})
        if estado:
            filtros_activos.append({'clave': 'estado', 'label': f'Estado: {estado.capitalize()}'})
        if fecha_desde_str or fecha_hasta_str:
            filtros_activos.append({'clave': 'fecha', 'label': f'Rango: {fecha_desde_str or "Inicio"} a {fecha_hasta_str or "Hoy"}'})

        context = {
            'resumenes': resumenes,
            'page_obj': page_obj,
            'paginator': paginator,
            'expediente': expediente,
            'selected_id': selected_resumen.factura.id if selected_resumen else None,
            'total_general': cuenta_todos,
            'cuenta_todos': cuenta_todos,
            'cuenta_e31': cuenta_e31,
            'cuenta_e32': cuenta_e32,
            'cuenta_aprobados': cuenta_aprobados,
            'cuenta_rechazados': cuenta_rechazados,
            'query': query,
            'tipo_ecf': tipo_ecf,
            'estado': estado,
            'fecha_desde': fecha_desde_str,
            'fecha_hasta': fecha_hasta_str,
            'filtro_rapido': filtro_rapido,
            'vista': vista,
            'page_size': page_size,
            'filtros_activos': filtros_activos,
        }
        return render(request, self.template_name, context)

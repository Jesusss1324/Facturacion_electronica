import csv
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.views import View

from frontend_data import get_repository


class LogListView(LoginRequiredMixin, View):
    """Consulta de logs de auditoría técnica y regulatoria. Solo lectura (GET)."""

    http_method_names = ['get', 'head', 'options']

    def get(self, request, *args, **kwargs):
        repository = get_repository()

        # Query parameters
        query = request.GET.get('q', '').strip()
        modulo = request.GET.get('modulo', '').strip()
        usuario = request.GET.get('usuario', '').strip()
        resultado = request.GET.get('resultado', '').strip()
        desde = request.GET.get('desde', '').strip()
        hasta = request.GET.get('hasta', '').strip()
        formato = request.GET.get('format', '').strip()

        # Filter logs
        eventos = repository.filter_logs(
            query=query,
            modulo=modulo,
            usuario=usuario,
            resultado=resultado,
            fecha_desde=desde,
            fecha_hasta=hasta,
        )

        # CSV Export handling
        if formato == 'csv' or request.GET.get('export') == 'csv':
            response = HttpResponse(content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = f'attachment; filename="logs_auditoria_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
            # Add UTF-8 BOM for Excel compatibility
            response.write('\ufeff')
            writer = csv.writer(response)
            writer.writerow([
                'ID', 'Fecha_Hora_MS', 'Usuario', 'Tipo_Usuario', 'Modulo',
                'Evento', 'Descripcion', 'Referencia_Tipo', 'Referencia_Codigo',
                'Resultado', 'Codigo_Error', 'IP', 'TrackId', 'Hash_SHA256'
            ])
            for ev in eventos:
                writer.writerow([
                    ev.id,
                    ev.timestamp_display,
                    ev.usuario,
                    ev.tipo_usuario,
                    ev.modulo_display,
                    ev.titulo,
                    ev.descripcion,
                    ev.referencia_tipo,
                    ev.referencia_codigo,
                    ev.resultado_display,
                    ev.codigo_error,
                    ev.ip,
                    ev.detalles_tecnicos.get('track_id', ''),
                    ev.hash_seguridad,
                ])
            return response

        # Active filters list for chips
        filtros_activos = []
        if query:
            filtros_activos.append({'tipo': 'q', 'label': f'Búsqueda: {query}', 'param': 'q'})
        if modulo and modulo.lower() != 'todos':
            modulo_label = {
                'dgii': 'Servicio DGII',
                'firma': 'Firma digital',
                'xml': 'XML e-CF',
                'facturacion': 'Facturación',
                'clientes': 'Clientes',
                'auth': 'Autenticación',
                'pdf': 'Representación PDF',
            }.get(modulo.lower(), modulo)
            filtros_activos.append({'tipo': 'modulo', 'label': f'Módulo: {modulo_label}', 'param': 'modulo'})
        if usuario and usuario.lower() != 'todos':
            filtros_activos.append({'tipo': 'usuario', 'label': f'Usuario: {usuario}', 'param': 'usuario'})
        if resultado and resultado.lower() != 'todos':
            filtros_activos.append({'tipo': 'resultado', 'label': f'Estado: {resultado.capitalize()}', 'param': 'resultado'})
        if desde:
            filtros_activos.append({'tipo': 'desde', 'label': f'Desde: {desde}', 'param': 'desde'})
        if hasta:
            filtros_activos.append({'tipo': 'hasta', 'label': f'Hasta: {hasta}', 'param': 'hasta'})

        # Pagination (10 per page matching reference design)
        paginator = Paginator(eventos, 10)
        page_number = request.GET.get('page', 1)
        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages if paginator.num_pages > 0 else 1)

        # Dynamic user display for the logged-in session
        nombre_sesion = request.user.get_short_name() or request.user.username

        # Build clean query string for pagination links
        query_params = request.GET.copy()
        if 'page' in query_params:
            del query_params['page']
        clean_query = query_params.urlencode()

        context = {
            'page_obj': page_obj,
            'paginator': paginator,
            'eventos_filtrados': len(eventos),
            'total_eventos': repository.total_logs(),
            'query': query,
            'modulo_actual': modulo,
            'usuario_actual': usuario,
            'resultado_actual': resultado,
            'desde_actual': desde,
            'hasta_actual': hasta,
            'filtros_activos': filtros_activos,
            'hay_filtros': bool(filtros_activos),
            'nombre_sesion': nombre_sesion,
            'clean_query': clean_query,
        }
        return render(request, 'bitacora/listado.html', context)


class LogDetalleView(LoginRequiredMixin, View):
    """Detalle forense de un evento criptográfico individual (GET)."""

    http_method_names = ['get', 'head', 'options']

    def get(self, request, pk, *args, **kwargs):
        repository = get_repository()
        try:
            evento = repository.get_log(pk)
        except KeyError:
            raise Http404('Evento de log no encontrado.')

        factura_relacionada = None
        cliente_relacionado = None
        if evento.referencia_tipo == 'factura' and evento.referencia_id:
            try:
                factura_relacionada = repository.get_factura(evento.referencia_id)
            except KeyError:
                pass
        elif evento.referencia_tipo == 'cliente' and evento.referencia_id:
            try:
                cliente_relacionado = repository.get_cliente(evento.referencia_id)
            except KeyError:
                pass

        detalles_json = json.dumps(evento.detalles_tecnicos, indent=2, ensure_ascii=False)

        context = {
            'evento': evento,
            'detalles_json': detalles_json,
            'factura': factura_relacionada,
            'cliente': cliente_relacionado,
        }
        return render(request, 'bitacora/detalle.html', context)

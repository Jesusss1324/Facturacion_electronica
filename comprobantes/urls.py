from django.urls import path

from core.views import (
    PendingActionView,
    PendingDownloadView,
    ProtectedPendingScreenView,
    ProtectedRedirectView,
)
from .views import DatosGeneralesView, SeleccionarClienteView, TipoComprobanteView
from .views_detalle import DetalleFacturaView
from .views_historial import HistorialFacturasView
from .views_items import BienesServiciosView
from .views_pdf import RepresentacionImpresaPdfView
from .views_procesamiento import EmitirComprobanteView, ProcesamientoFacturaView
from .views_resultado import ResultadoEmisionView
from .views_revision import RevisionFacturaView
from .views_totales import TotalesCondicionesView
from .views_xml import DocumentoXmlView

app_name = 'comprobantes'

urlpatterns = [
    path('', HistorialFacturasView.as_view(), name='historial'),
    path('nueva/', ProtectedRedirectView.as_view(pattern_name='comprobantes:tipo', query_string=True), name='nueva'),
    path('nueva/tipo/', TipoComprobanteView.as_view(), name='tipo'),
    # El UUID identifica el futuro borrador; no equivale al ID de una factura emitida.
    path('borradores/<uuid:borrador_id>/cliente/', SeleccionarClienteView.as_view(), name='cliente'),
    path('borradores/<uuid:borrador_id>/datos/', DatosGeneralesView.as_view(), name='datos'),
    path('borradores/<uuid:borrador_id>/items/', BienesServiciosView.as_view(), name='items'),
    path('borradores/<uuid:borrador_id>/totales/', TotalesCondicionesView.as_view(), name='totales'),
    path('borradores/<uuid:borrador_id>/revision/', RevisionFacturaView.as_view(), name='revision'),
    path('borradores/<uuid:borrador_id>/emitir/', EmitirComprobanteView.as_view(), name='emitir'),
    path('<int:pk>/', DetalleFacturaView.as_view(), name='detalle'),
    path('<int:pk>/procesamiento/', ProcesamientoFacturaView.as_view(), name='procesamiento'),
    path('<int:pk>/resultado/', ResultadoEmisionView.as_view(), name='resultado'),
    path('<int:pk>/xml/', DocumentoXmlView.as_view(), name='xml'),
    path('<int:pk>/pdf/', RepresentacionImpresaPdfView.as_view(), name='pdf'),
    path('<int:pk>/xml/descargar/', PendingDownloadView.as_view(), name='descargar_xml'),
    path('<int:pk>/pdf/descargar/', PendingDownloadView.as_view(), name='descargar_pdf'),
]

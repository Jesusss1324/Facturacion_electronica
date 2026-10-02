"""Navegación y metadatos de pantallas. No contiene lógica de facturación."""

from dataclasses import dataclass


@dataclass(frozen=True)
class NavigationItem:
    label: str
    url_name: str
    section: str
    icon: str


NAVIGATION = (
    NavigationItem('Inicio', 'core:inicio', 'inicio', 'home'),
    NavigationItem('Clientes', 'clientes:listado', 'clientes', 'users'),
    NavigationItem('Historial', 'comprobantes:historial', 'historial', 'invoices'),
    NavigationItem('Logs', 'bitacora:listado', 'bitacora', 'activity'),
    NavigationItem('Marco Legal', 'core:marco_legal', 'legal', 'shield'),
)


@dataclass(frozen=True)
class Screen:
    ui_id: str
    title: str
    section: str
    parent_url_name: str = ''
    parent_label: str = ''
    step: int = 0


SCREENS = {
    'usuarios:login': Screen('UI-01', 'Iniciar sesión', 'acceso'),
    'core:inicio': Screen('UI-02', 'Inicio', 'inicio'),
    'clientes:listado': Screen('UI-03', 'Clientes', 'clientes'),
    'clientes:crear': Screen('UI-04', 'Nuevo cliente', 'clientes', 'clientes:listado', 'Clientes'),
    'clientes:detalle': Screen('UI-05', 'Detalle del cliente', 'clientes', 'clientes:listado', 'Clientes'),
    'clientes:editar': Screen('UI-06', 'Editar cliente', 'clientes', 'clientes:listado', 'Clientes'),
    'comprobantes:tipo': Screen('UI-07', 'Tipo de comprobante', 'emision', step=1),
    'comprobantes:cliente': Screen('UI-08', 'Seleccionar cliente', 'emision', step=2),
    'comprobantes:datos': Screen('UI-09', 'Datos generales', 'emision', step=3),
    'comprobantes:items': Screen('UI-10', 'Bienes y servicios', 'emision', step=4),
    'comprobantes:totales': Screen('UI-11', 'Totales y condiciones', 'emision', step=5),
    'comprobantes:revision': Screen('UI-12', 'Revisión de factura', 'emision', step=6),
    'comprobantes:procesamiento': Screen('UI-13', 'Procesamiento de factura', 'emision'),
    'comprobantes:resultado': Screen('UI-14', 'Resultado de emisión', 'historial', 'comprobantes:historial', 'Historial'),
    'comprobantes:detalle': Screen('UI-15', 'Detalle de factura', 'historial', 'comprobantes:historial', 'Historial'),
    'comprobantes:xml': Screen('UI-16', 'Documento XML', 'historial', 'comprobantes:historial', 'Historial'),
    'comprobantes:pdf': Screen('UI-17', 'Representación impresa', 'historial', 'comprobantes:historial', 'Historial'),
    'comprobantes:historial': Screen('UI-18', 'Historial de facturas', 'historial'),
    'bitacora:listado': Screen('UI-19', 'Logs de eventos', 'bitacora'),
    'bitacora:detalle': Screen('UI-19', 'Detalle del log', 'bitacora', 'bitacora:listado', 'Logs'),
    'core:marco_legal': Screen('UI-20', 'Marco Legal y Normativo', 'legal'),
}

INVOICE_STEPS = (
    'Tipo', 'Cliente', 'Datos generales', 'Bienes y servicios', 'Totales', 'Revisión',
)

"""Contenido E31/E32 conforme al orden de los XSD; aún sin firma digital."""
from datetime import date, datetime
from xml.etree.ElementTree import Comment, Element, SubElement, indent, tostring


def _fecha(value):
    if not value:
        return ''
    if isinstance(value, (date, datetime)):
        return value.strftime('%d-%m-%Y')
    for fmt in ('%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(str(value), fmt).strftime('%d-%m-%Y')
        except ValueError:
            pass
    return str(value)


def construir_documento(datos, cliente, emisor, lineas, resumen, encf=''):
    root = Element('ECF')
    root.append(Comment(' DEMOSTRACION LOCAL: contenido sin firma digital '))

    def campos(parent, values):
        for nombre, valor in values.items():
            if valor is not None and str(valor) != '':
                SubElement(parent, nombre).text = str(valor)

    encabezado = SubElement(root, 'Encabezado')
    campos(encabezado, {'Version': '1.0'})
    id_doc = SubElement(encabezado, 'IdDoc')
    campos(id_doc, {'TipoeCF': datos.tipo_ecf, 'eNCF': encf})
    if datos.tipo_ecf == '31':
        campos(id_doc, {'FechaVencimientoSecuencia': _fecha(getattr(datos, 'vencimiento_secuencia', ''))})
    campos(id_doc, {'IndicadorMontoGravado': 0, 'TipoIngresos': datos.tipo_ingreso,
                   'TipoPago': {'contado': '1', 'credito': '2', 'gratuito': '3'}[datos.tipo_pago]})
    if datos.fecha_vencimiento:
        campos(id_doc, {'FechaLimitePago': _fecha(datos.fecha_vencimiento)})
    pagos = SubElement(id_doc, 'TablaFormasPago')
    campos(SubElement(pagos, 'FormaDePago'), {'FormaPago': datos.forma_pago, 'MontoPago': f"{resumen['total']:.2f}"})
    campos(SubElement(encabezado, 'Emisor'), {
        'RNCEmisor': emisor['rnc_raw'], 'RazonSocialEmisor': emisor['razon_social'],
        'NombreComercial': emisor['nombre_comercial'], 'DireccionEmisor': emisor['direccion'],
        'FechaEmision': _fecha(datos.fecha_emision),
    })
    campos(SubElement(encabezado, 'Comprador'), {
        'RNCComprador': cliente.identificacion, 'RazonSocialComprador': cliente.nombre,
        'ContactoComprador': cliente.telefono, 'CorreoComprador': cliente.email,
        'DireccionComprador': cliente.direccion,
    })
    campos(SubElement(encabezado, 'Totales'), {
        'MontoGravadoTotal': f"{resumen['base']:.2f}", 'MontoGravadoI1': f"{resumen['base']:.2f}",
        'ITBIS1': '18', 'TotalITBIS': f"{resumen['itbis']:.2f}",
        'TotalITBIS1': f"{resumen['itbis']:.2f}", 'MontoTotal': f"{resumen['total']:.2f}",
    })
    detalles = SubElement(root, 'DetallesItems')
    for numero, linea in enumerate(lineas, 1):
        campos(SubElement(detalles, 'Item'), {
            'NumeroLinea': numero, 'IndicadorFacturacion': 1, 'NombreItem': linea.concepto,
            'IndicadorBienoServicio': 2 if linea.tipo == 'servicio' else 1,
            'DescripcionItem': linea.descripcion, 'CantidadItem': f'{linea.cantidad:.2f}',
            'PrecioUnitarioItem': f'{linea.precio:.2f}', 'DescuentoMonto': f'{linea.descuento:.2f}',
            'MontoItem': f'{linea.base:.2f}',
        })
    indent(root, space='  ')
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(root, encoding='unicode')

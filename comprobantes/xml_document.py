"""XML representativo local; no implica validación XSD ni firma fiscal."""
from xml.etree.ElementTree import Comment, Element, SubElement, indent, tostring


def construir_documento(datos, cliente, emisor, lineas, resumen, encf=''):
    root = Element('eCF', xmlns='http://dgii.gov.do/ecf/v1.0')
    root.append(Comment(
        ' DEMOSTRACION LOCAL: sin firma digital ni validacion DGII '))

    def campos(parent, values):
        for nombre, valor in values.items():
            SubElement(parent, nombre).text = str(valor) if valor is not None else ''

    encabezado = SubElement(root, 'Encabezado')
    id_doc = SubElement(encabezado, 'IdDoc')
    campos(id_doc, {
        'TipoeCF': datos.tipo_ecf, 'eNCF': encf,
        'TipoIngresos': datos.tipo_ingreso, 'TipoPago': datos.tipo_pago,
        'FormaPago': datos.forma_pago,
    })
    if datos.fecha_vencimiento:
        campos(id_doc, {'FechaLimitePago': datos.fecha_vencimiento})
    if getattr(datos, 'termino_pago', ''):
        campos(id_doc, {'TerminoPago': datos.termino_pago})
    campos(SubElement(encabezado, 'Emisor'), {
        'RNCEmisor': emisor['rnc_raw'], 'RazonSocialEmisor': emisor['razon_social'],
        'NombreComercial': emisor['nombre_comercial'], 'DireccionEmisor': emisor['direccion'],
        'FechaEmision': datos.fecha_emision,
    })
    campos(SubElement(encabezado, 'Comprador'), {
        'RNCComprador': cliente.identificacion, 'RazonSocialComprador': cliente.nombre,
        'DireccionComprador': cliente.direccion, 'ContactoComprador': cliente.telefono,
    })
    campos(SubElement(encabezado, 'Totales'), {
        'MontoGravadoTotal': f"{resumen['base']:.2f}",
        'MontoGravadoI1': f"{resumen['base']:.2f}",
        'TotalITBIS': f"{resumen['itbis']:.2f}", 'TotalITBIS1': f"{resumen['itbis']:.2f}",
        'MontoTotal': f"{resumen['total']:.2f}",
    })
    detalles = SubElement(root, 'DetallesItems')
    for numero, linea in enumerate(lineas, 1):
        campos(SubElement(detalles, 'Item'), {
            'NumeroLinea': numero, 'IndicadorFacturacion': 1,
            'NombreItem': linea.concepto, 'DescripcionItem': linea.descripcion or linea.concepto,
            'CantidadItem': f'{linea.cantidad:.2f}', 'UnidadMedida': linea.unidad,
            'PrecioUnitarioItem': f'{linea.precio:.2f}', 'DescuentoMonto': f'{linea.descuento:.2f}',
            'MontoItem': f'{linea.total:.2f}',
        })
    campos(SubElement(root, 'Subtotales'), {
        'SubtotalMontoBruto': f"{resumen['bruto']:.2f}",
        'TotalDescuento': f"{resumen['descuento']:.2f}", 'SubtotalNeto': f"{resumen['base']:.2f}",
    })
    indent(root, space='  ')
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(root, encoding='unicode')

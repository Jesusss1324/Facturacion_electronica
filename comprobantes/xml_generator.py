from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom


def generar_xml_comprobante(comprobante):
    """
    Construye el XML del e-CF a partir de una instancia de Comprobante.
    Devuelve el XML como string formateado (pretty-printed).
    """
    root = Element('ECF')

    # --- Encabezado ---
    encabezado = SubElement(root, 'Encabezado')

    id_doc = SubElement(encabezado, 'IdDoc')
    SubElement(id_doc, 'TipoeCF').text = comprobante.tipo_ecf
    SubElement(id_doc, 'eNCF').text = comprobante.e_ncf or ''

    emisor_el = SubElement(encabezado, 'Emisor')
    SubElement(emisor_el, 'RNCEmisor').text = comprobante.emisor.rnc
    SubElement(emisor_el, 'RazonSocialEmisor').text = comprobante.emisor.razon_social
    SubElement(emisor_el, 'DireccionEmisor').text = comprobante.emisor.direccion
    SubElement(emisor_el, 'FechaEmision').text = comprobante.fecha_emision.strftime('%Y-%m-%d')

    comprador_el = SubElement(encabezado, 'Comprador')
    SubElement(comprador_el, 'RNCComprador').text = comprobante.receptor.rnc_cedula
    SubElement(comprador_el, 'RazonSocialComprador').text = comprobante.receptor.nombre

    totales_el = SubElement(encabezado, 'Totales')
    SubElement(totales_el, 'MontoGravadoTotal').text = str(comprobante.monto_gravado)
    SubElement(totales_el, 'MontoExento').text = str(comprobante.monto_exento)
    SubElement(totales_el, 'TotalITBIS').text = str(comprobante.itbis)
    SubElement(totales_el, 'MontoTotal').text = str(comprobante.monto_total)

    # --- Detalle de ítems ---
    detalles_el = SubElement(root, 'DetallesItems')
    for item in comprobante.items.all():
        item_el = SubElement(detalles_el, 'Item')
        SubElement(item_el, 'NumeroLinea').text = str(item.numero_linea)
        SubElement(item_el, 'NombreItem').text = item.nombre_item
        SubElement(item_el, 'CantidadItem').text = str(item.cantidad)
        SubElement(item_el, 'PrecioUnitarioItem').text = str(item.precio_unitario)
        SubElement(item_el, 'MontoItem').text = str(item.monto_item)

    # --- Placeholder para la firma (la llenaremos en el siguiente paso) ---
    SubElement(root, 'FirmaDigital')

    return _formatear_xml(root)


def _formatear_xml(element):
    """Convierte el Element de ElementTree a un string XML legible (con indentación)."""
    xml_crudo = tostring(element, encoding='unicode')
    return minidom.parseString(xml_crudo).toprettyxml(indent='  ')
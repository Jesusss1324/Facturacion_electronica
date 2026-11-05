"""Representación descargable de demostración, con paginación automática."""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, LongTable, TableStyle


def construir_pdf(context):
    stream = BytesIO()
    styles = getSampleStyleSheet()
    story = []

    def texto(value, style='BodyText'):
        return Paragraph(escape(str(value)), styles[style])

    factura = context['factura']
    story += [texto('Factura - demostración local', 'Title'),
              texto('SIN VALIDEZ FISCAL. Sin firma digital ni envío a DGII.'),
              Spacer(1, 5 * mm), texto(context['emisor']['razon_social'], 'Heading2'),
              texto(f"RNC: {context['emisor']['rnc']}"),
              texto(f'Comprobante: {factura.e_ncf}'),
              texto(f"Fecha: {context['fecha_display']}"),
              texto(f"Receptor: {context['cliente'].nombre}"),
              texto(f"Identificación: {context['cliente'].identificacion}"),
              texto(f"Dirección: {context['cliente'].direccion}"),
              texto(f"Estado simulado: {context['estado']}"), Spacer(1, 5 * mm)]
    rows = [[texto(v) for v in ('Concepto', 'Cantidad', 'Precio', 'Descuento', 'Total DOP')]]
    for item in context['items']:
        rows.append([texto(item['concepto']), texto(item['cantidad']),
                     texto(f"{item['precio']:.2f}"), texto(f"{item['descuento']:.2f}"),
                     texto(f"{item['total_neto']:.2f}")])
    table = LongTable(rows, colWidths=[65*mm, 22*mm, 27*mm, 27*mm, 29*mm], repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LINEBELOW', (0, 0), (-1, 0), .5, colors.grey),
    ]))
    story += [table, Spacer(1, 5*mm)]
    for label, key in [('Subtotal', 'subtotal_bruto'), ('Descuento', 'descuento_total'),
                       ('Base gravada', 'base_imponible'), ('ITBIS', 'itbis_total'),
                       ('Total DOP', 'monto_total')]:
        story.append(texto(f'{label}: {context[key]:.2f}'))
    story.append(texto(context['cantidad_en_letras']))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.drawString(20*mm, 12*mm, 'Demostración local - sin validez fiscal')
        canvas.drawRightString(190*mm, 12*mm, f'Página {doc.page}')
        canvas.restoreState()

    SimpleDocTemplate(stream, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm,
                      topMargin=18*mm, bottomMargin=20*mm).build(
                          story, onFirstPage=footer, onLaterPages=footer)
    return stream.getvalue()

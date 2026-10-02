"""Utilidades y generadores de apoyo para la revisión final del comprobante e-CF."""
from decimal import Decimal

EMISOR_INFO = {
    'rnc': '1-31-89012-3',
    'rnc_raw': '131890123',
    'razon_social': 'SOLUCIONES DIGITALES DEL CARIBE, SRL',
    'nombre_comercial': 'Soluciones Digitales del Caribe',
    'direccion': 'Av. Winston Churchill #1099, Torre Empresarial Piantini, Piso 14, Santo Domingo, D.N.',
    'telefono': '(809) 567-8900',
    'email': 'contacto@solucionescaribe.com.do',
    'actividad': 'Desarrollo de Sistemas y Consultoría Informática (CIIU 6201)',
    'autorizacion': 'Contribuyente e-CF Autorizado',
}

UNIDADES = ('', 'un', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve')
DECENAS = ('', 'diez', 'veinte', 'treinta', 'cuarenta', 'cincuenta', 'sesenta', 'setenta', 'ochenta', 'noventa')
DIEZ_Y = ('diez', 'once', 'doce', 'trece', 'catorce', 'quince', 'dieciséis', 'diecisiete', 'dieciocho', 'diecinueve')
CENTENAS = ('', 'ciento', 'doscientos', 'trescientos', 'cuatrocientos', 'quinientos', 'seiscientos', 'setecientos', 'ochocientos', 'novecientos')


def _centenas(n):
    if n == 0:
        return ''
    if n == 100:
        return 'cien'
    c = n // 100
    d = (n % 100) // 10
    u = n % 10
    partes = []
    if c > 0:
        partes.append(CENTENAS[c])
    if d == 1:
        partes.append(DIEZ_Y[u])
    elif d == 2:
        if u == 0:
            partes.append('veinte')
        elif u == 1:
            partes.append('veintiún')
        elif u == 2:
            partes.append('veintidós')
        elif u == 3:
            partes.append('veintitrés')
        elif u == 6:
            partes.append('veintiséis')
        else:
            partes.append('veinti' + UNIDADES[u])
    elif d > 2:
        if u == 0:
            partes.append(DECENAS[d])
        else:
            partes.append(f'{DECENAS[d]} y {UNIDADES[u]}')
    elif u > 0:
        partes.append(UNIDADES[u])
    return ' '.join(partes)


def _numero_a_letras(n):
    if n == 0:
        return 'cero'
    millones = n // 1_000_000
    resto = n % 1_000_000
    miles = resto // 1_000
    unidades = resto % 1_000

    partes = []
    if millones == 1:
        partes.append('un millón')
    elif millones > 1:
        partes.append(f'{_numero_a_letras(millones)} millones')

    if miles == 1:
        partes.append('mil')
    elif miles > 1:
        partes.append(f'{_centenas(miles)} mil')

    if unidades > 0:
        partes.append(_centenas(unidades))

    return ' '.join(partes).strip()


def monto_en_letras(total: Decimal) -> str:
    """Convierte un importe Decimal a su representación formal en letras según uso dominicano."""
    entero = int(total)
    centavos = int(round((total - entero) * 100))
    letras = _numero_a_letras(entero).capitalize()
    moneda = 'peso dominicano' if entero == 1 else 'pesos dominicanos'
    return f'Son: {letras} {moneda} con {centavos:02d}/100 M.N.'


def generar_xml_ecf(borrador, cliente, resumen, emisor=EMISOR_INFO) -> str:
    """Construye la estructura representativa XML bajo la especificación e-CF de la DGII."""
    fecha_emision_str = str(borrador.fecha_emision) if borrador.fecha_emision else ''
    fecha_venc_str = str(borrador.fecha_vencimiento) if borrador.fecha_vencimiento else ''
    tipo_ecf_str = borrador.tipo_ecf
    encf_str = f'E{borrador.tipo_ecf}0000000001'

    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<eCF xmlns="http://dgii.gov.do/ecf/v1.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">',
        '  <Encabezado>',
        '    <IdDoc>',
        f'      <TipoeCF>{tipo_ecf_str}</TipoeCF>',
        f'      <eNCF>{encf_str}</eNCF>',
        '      <FechaVencimientoSecuencia>2026-12-31</FechaVencimientoSecuencia>',
        '      <IndicadorMontoGravado>1</IndicadorMontoGravado>',
        f'      <TipoIngresos>{borrador.tipo_ingreso}</TipoIngresos>',
        f'      <TipoPago>{borrador.tipo_pago}</TipoPago>',
    ]
    if fecha_venc_str:
        xml_lines.append(f'      <FechaLimitePago>{fecha_venc_str}</FechaLimitePago>')
    if borrador.termino_pago:
        xml_lines.append(f'      <TerminoPago>{borrador.termino_pago}</TerminoPago>')
    xml_lines.extend([
        '    </IdDoc>',
        '    <Emisor>',
        f'      <RNCEmisor>{emisor["rnc_raw"]}</RNCEmisor>',
        f'      <RazonSocialEmisor>{emisor["razon_social"]}</RazonSocialEmisor>',
        f'      <NombreComercial>{emisor["nombre_comercial"]}</NombreComercial>',
        f'      <DireccionEmisor>{emisor["direccion"]}</DireccionEmisor>',
        f'      <FechaEmision>{fecha_emision_str}</FechaEmision>',
        '    </Emisor>',
        '    <Comprador>',
        f'      <RNCComprador>{cliente.identificacion}</RNCComprador>',
        f'      <RazonSocialComprador>{cliente.nombre}</RazonSocialComprador>',
        f'      <DireccionComprador>{cliente.direccion}</DireccionComprador>',
        '    </Comprador>',
        '    <Totales>',
        f'      <MontoGravadoTotal>{resumen["base"]:.2f}</MontoGravadoTotal>',
        f'      <MontoGravadoI1>{resumen["base"]:.2f}</MontoGravadoI1>',
        f'      <TotalITBIS>{resumen["itbis"]:.2f}</TotalITBIS>',
        f'      <TotalITBIS1>{resumen["itbis"]:.2f}</TotalITBIS1>',
        f'      <MontoTotal>{resumen["total"]:.2f}</MontoTotal>',
        '    </Totales>',
        '  </Encabezado>',
        '  <DetallesItems>',
    ])
    for num, linea in enumerate(borrador.lineas, 1):
        desc = linea.descripcion or linea.concepto
        xml_lines.extend([
            '    <Item>',
            f'      <NumeroLinea>{num}</NumeroLinea>',
            '      <IndicadorFacturacion>1</IndicadorFacturacion>',
            f'      <NombreItem>{linea.concepto}</NombreItem>',
            f'      <DescripcionItem>{desc}</DescripcionItem>',
            f'      <CantidadItem>{linea.cantidad:.2f}</CantidadItem>',
            f'      <UnidadMedida>{linea.unidad}</UnidadMedida>',
            f'      <PrecioUnitarioItem>{linea.precio:.2f}</PrecioUnitarioItem>',
            f'      <DescuentoMonto>{linea.descuento:.2f}</DescuentoMonto>',
            f'      <MontoItem>{linea.total:.2f}</MontoItem>',
            '    </Item>',
        ])
    xml_lines.extend([
        '  </DetallesItems>',
        '  <Subtotales>',
        f'    <SubtotalMontoBruto>{resumen["bruto"]:.2f}</SubtotalMontoBruto>',
        f'    <TotalDescuento>{resumen["descuento"]:.2f}</TotalDescuento>',
        f'    <SubtotalNeto>{resumen["base"]:.2f}</SubtotalNeto>',
        '  </Subtotales>',
        '</eCF>',
    ])
    return '\n'.join(xml_lines)

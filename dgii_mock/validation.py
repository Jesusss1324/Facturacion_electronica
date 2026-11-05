"""Reglas del perfil local E31/E32. Ver docs/entidad-local.md para fuentes y límites."""
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
import re

from django.utils import timezone
from lxml import etree

from .identification import valida
from .models import ContribuyenteLocal, RangoLocal

MAX_XML = 1024 * 1024
XS = {'xs': 'http://www.w3.org/2001/XMLSchema'}
DS = 'http://www.w3.org/2000/09/xmldsig#'


def analizar(raw):
    if not raw or len(raw) > MAX_XML:
        raise ValueError('XML vacío o mayor de 1 MiB.')
    parser = etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=True)
    try:
        root = etree.fromstring(raw, parser)
    except etree.XMLSyntaxError as error:
        raise ValueError('XML mal formado.') from error
    if root.getroottree().docinfo.doctype or any(isinstance(e, etree._Entity) for e in root.iter()):
        raise ValueError('No se permiten DTD ni entidades XML.')
    if root.tag != 'ECF':
        raise ValueError('La raíz debe ser ECF sin espacio de nombres.')
    return root


def comprobar_xsd(root, tipo, contenido=False):
    schema = etree.parse(str(Path(__file__).parent / 'schemas' / f'ecf{tipo}.xsd'))
    # Los archivos oficiales contienen name=" IndicadorServicioTodoIncluidoType".
    # Normalizamos el espacio léxico del NCName en memoria; originales intactos.
    for node in schema.xpath('/xs:schema/xs:simpleType', namespaces=XS):
        node.set('name', node.get('name').strip())
    if contenido:
        # El XSD oficial exige la fecha de firma y un elemento final xs:any.
        # Sólo esos dos mínimos se vuelven opcionales para la etapa previa a firma.
        seq = schema.xpath('/xs:schema/xs:element/xs:complexType/xs:sequence', namespaces=XS)[0]
        for child in seq:
            if child.get('name') == 'FechaHoraFirma' or child.tag == f'{{{XS["xs"]}}}any':
                child.set('minOccurs', '0')
    validator = etree.XMLSchema(schema)
    try:
        validator.assertValid(root)
        return True, 'Estructura conforme al XSD de contenido.' if contenido else 'XSD completo conforme.'
    except etree.DocumentInvalid as error:
        return False, '; '.join(e.message for e in list(error.error_log)[:5])[:1500]


def validar(root):
    checks = []

    def add(codigo, valido, detalle, origen='local'):
        checks.append({'codigo': codigo, 'estado': 'correcto' if valido else 'error',
                       'detalle': detalle, 'origen': origen})

    def text(path):
        return root.findtext(path, '').strip()

    tipo = text('Encabezado/IdDoc/TipoeCF')
    encf = text('Encabezado/IdDoc/eNCF')
    add('TIPO_ENCF', tipo in ('31', '32') and bool(re.fullmatch(f'E{tipo}[0-9]{{10}}', encf)),
        'Tipo soportado y e-NCF coherente (E31/E32 y diez dígitos).')
    if tipo not in ('31', '32'):
        return checks
    ok, detalle = comprobar_xsd(root, tipo, contenido=True)
    add('XSD_CONTENIDO', ok, detalle, 'XSD oficial, etapa previa a firma')
    signed = root.find(f'{{{DS}}}Signature') is not None
    if signed:
        ok, detalle = comprobar_xsd(root, tipo)
        add('XSD_COMPLETO', ok, detalle, 'XSD oficial sin modificaciones')
    else:
        checks.append({'codigo': 'XSD_COMPLETO', 'estado': 'pendiente',
                       'detalle': 'El XSD completo exige la fecha y el elemento de firma.', 'origen': 'XSD oficial'})
    rnc = text('Encabezado/Emisor/RNCEmisor')
    buyer = text('Encabezado/Comprador/RNCComprador')
    add('IDENTIFICACION_EMISOR', valida(rnc), 'Formato y dígito de control del emisor.')
    emisor = ContribuyenteLocal.objects.filter(identificacion=rnc).first()
    add('PADRON_EMISOR', bool(emisor and emisor.activo and emisor.emisor),
        'El emisor debe estar activo y habilitado en el padrón local independiente.')
    norm = lambda s: ' '.join(s.upper().split())
    add('NOMBRE_EMISOR', bool(emisor and norm(emisor.nombre) == norm(text('Encabezado/Emisor/RazonSocialEmisor'))),
        'La razón social debe coincidir con el padrón local.')
    if buyer:
        add('IDENTIFICACION_RECEPTOR', valida(buyer), 'Formato y dígito de control del receptor.')
        receptor = ContribuyenteLocal.objects.filter(identificacion=buyer).first()
        add('PADRON_RECEPTOR', bool(receptor and receptor.activo and (tipo != '31' or receptor.receptor_credito)),
            'Receptor identificado activo y, para E31, habilitado para crédito en este padrón local.')
        add('NOMBRE_RECEPTOR', bool(receptor and norm(receptor.nombre) == norm(text('Encabezado/Comprador/RazonSocialComprador'))),
            'El nombre del receptor debe coincidir con el padrón local.')
    try:
        total = Decimal(text('Encabezado/Totales/MontoTotal'))
        add('RECEPTOR_OBLIGATORIO', bool(buyer) or (tipo == '32' and total < Decimal('250000')),
            'E31 y E32 desde DOP 250,000 requieren identificar al comprador; extranjeros fuera del perfil.',
            'Formato e-CF, RNCComprador')
    except InvalidOperation:
        total = None
        add('RECEPTOR_OBLIGATORIO', False, 'No se puede evaluar el monto total.')
    try:
        fecha = datetime.strptime(text('Encabezado/Emisor/FechaEmision'), '%d-%m-%Y').date()
        add('FECHA', fecha <= timezone.localdate() + timedelta(days=1), 'Fecha de calendario válida; máximo un día futuro (política local).')
        numero = int(encf[3:])
        rango = RangoLocal.objects.filter(emisor__identificacion=rnc, tipo=tipo, activo=True,
            desde__lte=numero, hasta__gte=numero, vencimiento__gte=timezone.localdate()).first()
        add('RANGO', bool(rango and fecha <= rango.vencimiento), 'Número dentro de un rango local activo y vigente.')
        if tipo == '31':
            declarada = datetime.strptime(text('Encabezado/IdDoc/FechaVencimientoSecuencia'), '%d-%m-%Y').date()
            add('VENCIMIENTO_RANGO', bool(rango and declarada == rango.vencimiento), 'Vencimiento E31 coincide con el rango local asignado.')
        if text('Encabezado/IdDoc/TipoPago') == '2':
            limite = datetime.strptime(text('Encabezado/IdDoc/FechaLimitePago'), '%d-%m-%Y').date()
            add('PAGO_CREDITO', limite >= fecha, 'El vencimiento del crédito no es anterior a la emisión.')
    except (ValueError, TypeError):
        add('FECHA_RANGO', False, 'Fecha o secuencia inválida; no se puede comprobar el rango.')
    try:
        d = lambda path: Decimal(text(path) or '0')
        q = lambda value: value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        items = root.findall('DetallesItems/Item')
        bases, impuestos = [], []
        perfil = 1 <= len(items) <= 100 and text('Encabezado/IdDoc/IndicadorMontoGravado') == '0'
        perfil = perfil and text('Encabezado/IdDoc/TipoPago') in ('1', '2')
        totales = root.find('Encabezado/Totales')
        perfil = perfil and totales is not None and all(c.tag in {
            'MontoGravadoTotal', 'MontoGravadoI1', 'ITBIS1', 'TotalITBIS', 'TotalITBIS1', 'MontoTotal'
        } for c in totales)
        perfil = perfil and not any(root.find(p) is not None for p in ('DescuentosORecargos', 'Subtotales', 'InformacionReferencia'))
        perfil = perfil and all(d('Encabezado/Totales/' + k) == 0 for k in
            ('MontoGravadoI2', 'MontoGravadoI3', 'MontoExento', 'MontoImpuestoAdicional', 'MontoNoFacturable', 'TotalITBIS2', 'TotalITBIS3'))
        correctos = True
        for i, item in enumerate(items, 1):
            perfil = perfil and all(c.tag in {'NumeroLinea', 'IndicadorFacturacion', 'NombreItem',
                'IndicadorBienoServicio', 'DescripcionItem', 'CantidadItem', 'UnidadMedida',
                'PrecioUnitarioItem', 'DescuentoMonto', 'MontoItem'} for c in item)
            value = lambda key: Decimal(item.findtext(key, '0'))
            cantidad, precio, descuento = value('CantidadItem'), value('PrecioUnitarioItem'), value('DescuentoMonto')
            base = q(cantidad * precio) - descuento
            perfil = perfil and item.findtext('IndicadorFacturacion') == '1' and value('RecargoMonto') == 0
            correctos = correctos and item.findtext('NumeroLinea') == str(i) and cantidad > 0 and precio >= 0 and 0 <= descuento <= q(cantidad*precio) and value('MontoItem') == base
            bases.append(base)
            impuestos.append(q(base * Decimal('.18')))
        add('PERFIL_18', perfil, 'Perfil local: hasta 100 líneas gravadas al 18%, precios sin ITBIS, sin otras tasas ni recargos.')
        add('CALCULO_LINEAS', correctos and bool(items), 'Cantidad × precio, redondeo a centavos y descuento; MontoItem sin ITBIS.', 'Formato e-CF y redondeo local por línea')
        base, itbis = sum(bases, Decimal(0)), sum(impuestos, Decimal(0))
        add('TOTALES', total is not None and total == base+itbis and d('Encabezado/Totales/MontoGravadoTotal') == base
            and d('Encabezado/Totales/MontoGravadoI1') == base and d('Encabezado/Totales/ITBIS1') == 18
            and d('Encabezado/Totales/TotalITBIS') == itbis and d('Encabezado/Totales/TotalITBIS1') == itbis,
            'Bases, ITBIS y total coinciden con las líneas del documento.')
        pagos = sum((Decimal(p.findtext('MontoPago', '0')) for p in root.findall('Encabezado/IdDoc/TablaFormasPago/FormaDePago')), Decimal(0))
        add('PAGOS', total is not None and pagos == total, 'La suma de las formas de pago coincide con el total (perfil local).')
    except (InvalidOperation, ValueError, TypeError):
        add('CALCULOS', False, 'Importes no válidos para realizar los cálculos.')
    checks.append({'codigo': 'FIRMA', 'estado': 'pendiente', 'origen': 'etapa futura',
                   'detalle': 'Verificación criptográfica no implementada; no se concede aceptación fiscal.'})
    if tipo == '32' and total is not None and total < Decimal('250000'):
        checks.append({'codigo': 'RFCE', 'estado': 'pendiente', 'origen': 'límite de la recreación',
                       'detalle': 'Recepción diagnóstica del E32 completo. El circuito RFCE oficial es una extensión pendiente.'})
    return checks

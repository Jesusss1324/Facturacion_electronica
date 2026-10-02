"""Marco legal y normativo que rige el sistema de facturación electrónica (e-CF).

Sustento jurídico en la República Dominicana: Leyes, Normas Generales de la DGII,
Decretos del Poder Ejecutivo y Estándares Técnicos Oficiales.
"""

MARCO_LEGAL = (
    {
        'id': 'ley-32-23',
        'tipo': 'ley',
        'tipo_badge': 'Ley Nacional',
        'badge_class': 'badge-primary',
        'codigo': 'Ley Núm. 32-23',
        'titulo': 'Ley de Facturación Electrónica de la República Dominicana',
        'organismo': 'Congreso Nacional de la República Dominicana',
        'fecha': '16 de mayo de 2023',
        'vigencia': 'Vigente con calendario de obligatoriedad escalonado',
        'resumen': (
            'Ley marco obligatoria que instaura el uso generalizado de los Comprobantes Fiscales '
            'Electrónicos (e-CF) en todo el territorio dominicano, fijando plazos de obligatoriedad '
            'según la clasificación del contribuyente y otorgando plena validez jurídica y ejecutiva.'
        ),
        'articulos_clave': (
            {'articulo': 'Artículo 3', 'titulo': 'Definiciones Clave', 'desc': 'Define formalmente al e-CF, Emisor Electrónico, Receptor Electrónico y el acuse de recibo de recepción fiscal.'},
            {'articulo': 'Artículo 5', 'titulo': 'Obligatoriedad Escalonada', 'desc': 'Establece el calendario legal de incorporación para Grandes Nacionales, Grandes Locales, Medianos, Pequeños y Micro contribuyentes.'},
            {'articulo': 'Artículo 7', 'titulo': 'Fuerza Probatoria y Ejecutiva', 'desc': 'Los e-CF firmados digitalmente gozan de fe pública, valor probatorio en juicio y fuerza de título ejecutorio idéntico al documento en papel.'},
            {'articulo': 'Artículo 12', 'titulo': 'Conservación Digital Obligatoria', 'desc': 'Exige el resguardo y archivo de los comprobantes y acuses en formato electrónico por un plazo mínimo de 10 años.'},
            {'articulo': 'Artículo 17', 'titulo': 'Incentivos Fiscales', 'desc': 'Otorga créditos tributarios contra el ISR para aquellos contribuyentes que se incorporen de forma anticipada antes de su vencimiento legal.'},
        ),
        'impacto_sistema': (
            'Sustenta la arquitectura central del sistema: emisión exclusiva de e-CF, gestión de secuencias '
            'e-NCF autorizadas por la DGII, almacenamiento digital seguro en formato XML y preservación '
            'de la trazabilidad durante el período de prescripción legal.'
        ),
        'enlace_oficial': 'https://dgii.gov.do/facturacionElectronica/marcoLegal/Documents/Leyes/Ley32-23.pdf',
    },
    {
        'id': 'ley-126-02',
        'tipo': 'ley',
        'tipo_badge': 'Ley Nacional',
        'badge_class': 'badge-primary',
        'codigo': 'Ley Núm. 126-02',
        'titulo': 'Ley sobre Comercio Electrónico, Documentos y Firmas Digitales',
        'organismo': 'Congreso Nacional / Órgano Regulador: INDOTEL',
        'fecha': '4 de septiembre de 2002',
        'vigencia': 'Vigente',
        'resumen': (
            'Establece el principio de equivalencia funcional entre los documentos en papel y los '
            'documentos en soporte digital. Regula las firmas digitales cualificadas y los certificados '
            'emitidos por entidades de certificación autorizadas.'
        ),
        'articulos_clave': (
            {'articulo': 'Artículo 4', 'titulo': 'Equivalencia Funcional', 'desc': 'Ningún documento, factura o contrato perderá validez jurídica por el solo hecho de encontrarse en forma de mensaje de datos digital.'},
            {'articulo': 'Artículo 29', 'titulo': 'Firma Digital Cualificada', 'desc': 'La firma digital respaldada por un certificado de una entidad acreditada tiene idéntico valor legal y presunción de autenticidad que la firma manuscrita.'},
            {'articulo': 'Artículo 31', 'titulo': 'Integridad y No Repudio', 'desc': 'Garantiza que la transacción no puede ser repudiada por el emisor y que cualquier modificación posterior al sellado invalida el documento.'},
        ),
        'impacto_sistema': (
            'Obliga y fundamenta el motor criptográfico XML-DSig Enveloped: cálculo de resumen SHA-256, '
            'cifrado con clave privada RSA y uso de certificados digitales PKCS#12 autorizados para el contribuyente emisor.'
        ),
        'enlace_oficial': 'https://indotel.gob.do/marco-legal/leyes/ley-126-02/',
    },
    {
        'id': 'ley-11-92',
        'tipo': 'ley',
        'tipo_badge': 'Ley Nacional',
        'badge_class': 'badge-primary',
        'codigo': 'Ley Núm. 11-92',
        'titulo': 'Código Tributario de la República Dominicana y Modificaciones',
        'organismo': 'Congreso Nacional de la República Dominicana',
        'fecha': '16 de mayo de 1992',
        'vigencia': 'Vigente con modificaciones continuas',
        'resumen': (
            'Cuerpo legal fundamental que establece las normas tributarias generales, los deberes '
            'formales de los contribuyentes, las potestades fiscalizadoras de la DGII, los regímenes '
            'de ITBIS y las sanciones por incumplimiento fiscal.'
        ),
        'articulos_clave': (
            {'articulo': 'Artículo 50', 'titulo': 'Deberes Formales de Facturación', 'desc': 'Obligación imperativa de emitir y conservar facturas autorizadas por cada venta de bienes o prestación de servicios efectuada.'},
            {'articulo': 'Título III', 'titulo': 'Impuesto al ITBIS', 'desc': 'Norma la base imponible, alícuotas del 18% y 16%, exenciones objetivas y retenciones entre agentes de percepción autorizados.'},
            {'articulo': 'Artículo 257', 'titulo': 'Régimen de Sanciones e Infracciones', 'desc': 'Tipifica la no emisión, doble facturación o emisión sin autorización como falta formal sujeta a clausura y multas económicas.'},
        ),
        'impacto_sistema': (
            'Define los cálculos tributarios del sistema: desglose de Base Imponible, liquidación de ITBIS (18%/16%), '
            'registro del RNC del contribuyente receptor y verificación de estado activo en el padrón tributario.'
        ),
        'enlace_oficial': 'https://dgii.gov.do/legislacion/leyesTributarias/Documents/Codigo%20Tributario%20y%20Leyes%20que%20lo%20Modifican/Ley11-92.pdf',
    },
    {
        'id': 'norma-06-2023',
        'tipo': 'norma',
        'tipo_badge': 'Norma General DGII',
        'badge_class': 'badge-info',
        'codigo': 'Norma General Núm. 06-2023',
        'titulo': 'Disposiciones sobre la Emisión de Comprobantes Fiscales Electrónicos (e-CF)',
        'organismo': 'Dirección General de Impuestos Internos (DGII)',
        'fecha': '29 de junio de 2023',
        'vigencia': 'Vigente',
        'resumen': (
            'Reglamenta técnicamente la Ley 32-23 para el ecosistema de facturación electrónica. '
            'Establece la nomenclatura del e-NCF, la tipología de comprobantes, los plazos de envío telemático, '
            'el flujo de aprobación comercial entre compradores y vendedores y el protocolo de contingencia.'
        ),
        'articulos_clave': (
            {'articulo': 'Artículo 4', 'titulo': 'Estructura Alfanumérica del e-NCF', 'desc': 'Prefijo literal "E" + código de tipo (2 dígitos) + secuencia numérica de 10 dígitos (13 posiciones fijas, ej. E310000000001).'},
            {'articulo': 'Artículo 6', 'titulo': 'Catálogo de Comprobantes e-CF', 'desc': 'Establece los tipos oficiales: E31 (Crédito Fiscal), E32 (Consumo), E33 (Nota de Débito), E34 (Nota de Crédito), E41 (Compras), etc.'},
            {'articulo': 'Artículo 9', 'titulo': 'Plazo de Transmisión Telemática', 'desc': 'Los e-CF deben remitirse al Web Service de la DGII de manera sincrónica al momento de realizar la transacción comercial.'},
            {'articulo': 'Artículo 14', 'titulo': 'Flujo de Aprobación Comercial (ACECF)', 'desc': 'Mecanismo para que el receptor de un e-CF tipo E31 acepte o rechace comercialmente la factura en un plazo de hasta 30 días.'},
            {'articulo': 'Artículo 18', 'titulo': 'Procedimiento de Contingencia', 'desc': 'Regula el protocolo de reintentos y resguardo cuando los servicios de telecomunicación o los servidores de la DGII se encuentren inoperativos.'},
        ),
        'impacto_sistema': (
            'Es la norma operativa directa del software: define las validaciones de tipo de comprobante en el Wizard (Paso 1), '
            'la asignación de secuencias de 13 caracteres, la generación del XML y la gestión del acuse con TrackID.'
        ),
        'enlace_oficial': 'https://dgii.gov.do/legislacion/normas/Documents/Norma06-2023.pdf',
    },
    {
        'id': 'norma-06-2018',
        'tipo': 'norma',
        'tipo_badge': 'Norma General DGII',
        'badge_class': 'badge-info',
        'codigo': 'Norma General Núm. 06-2018',
        'titulo': 'Regulación de la Representación Impresa (RI) y Comprobantes Fiscales',
        'organismo': 'Dirección General de Impuestos Internos (DGII)',
        'fecha': '28 de febrero de 2018',
        'vigencia': 'Vigente con adecuaciones para e-CF',
        'resumen': (
            'Especifica el formato visual y los requisitos mínimos obligatorios que debe contener '
            'la Representación Impresa física o en formato PDF de las facturas electrónicas para tener plena validez ante terceros.'
        ),
        'articulos_clave': (
            {'articulo': 'Artículo 5', 'titulo': 'Recuadro Fiscal Reglamentario', 'desc': 'Ubicación en la esquina superior derecha con borde perimetral, denominación del e-CF, tipo en código y texto, e-NCF y vencimiento.'},
            {'articulo': 'Artículo 8', 'titulo': 'Código de Seguridad Visible', 'desc': 'Impresión legible de los primeros 6 caracteres alfanuméricos del DigestValue generado en el sellado de la firma digital.'},
            {'articulo': 'Artículo 11', 'titulo': 'Código QR Bidimensional', 'desc': 'Inclusión obligatoria del código QR que contiene el hipervínculo cifrado para la consulta directa de autenticidad en el portal de la DGII.'},
            {'articulo': 'Artículo 15', 'titulo': 'Desglose Formal de Importes', 'desc': 'Discriminación exacta entre Monto Gravado, Exento, ITBIS facturado, Descuentos y Total expresado en Moneda de Curso Legal (DOP).'},
        ),
        'impacto_sistema': (
            'Gobierna el diseño de la pantalla UI-17 (Visor de Representación Impresa / PDF) y la pantalla UI-12 (Revisión): '
            'disposición del recuadro fiscal, código de seguridad visible y código QR estandarizado conforme a las medidas normadas.'
        ),
        'enlace_oficial': 'https://dgii.gov.do/legislacion/normas/Documents/2018/Norma06-18.pdf',
    },
    {
        'id': 'estandar-tecnico-dgii',
        'tipo': 'estandar',
        'tipo_badge': 'Estándar Técnico',
        'badge_class': 'badge-success',
        'codigo': 'Especificación Técnica e-CF v1.0',
        'titulo': 'Estándar de Intercambio Telemático y Esquemas XSD para e-CF',
        'organismo': 'Departamento de Facturación Electrónica DGII',
        'fecha': 'Versión 1.0 Oficial',
        'vigencia': 'Vigente para Ambientes e-CF',
        'resumen': (
            'Documento de especificación de ingeniería de software que estandariza las estructuras de datos XML, '
            'los esquemas XSD oficiales, las reglas sintácticas y las 48 reglas de validación de negocio (RN-01 a RN-48).'
        ),
        'articulos_clave': (
            {'articulo': 'Namespace XML', 'titulo': 'Espacio de Nombres Oficial', 'desc': 'Declaración obligatoria de xmlns="http://dgii.gov.do/ecf/v1.0" y codificación de caracteres en UTF-8 sin BOM.'},
            {'articulo': 'XML-DSig W3C', 'titulo': 'Canonicalización y Firma Enveloped', 'desc': 'Uso del algoritmo C14N (W3C REC-xml-c14n-20010315), Digest SHA-256 y firma digital RSA-SHA256 bajo el estándar enveloped.'},
            {'articulo': 'Matriz RN-01/48', 'titulo': 'Reglas de Negocio Automatizadas', 'desc': 'Validación de cuadre de ítems, consistencia aritmética de ITBIS, correspondencia RNC y vigencia de la secuencia e-NCF.'},
            {'articulo': 'API Telemática', 'titulo': 'Protocolo de Semilla y Token', 'desc': 'Autenticación mediante Semilla XML firmada, entrega de Token JWT (vigencia 1 hora) y recepción con asignación de TrackId.'},
        ),
        'impacto_sistema': (
            'Define el formato del visor XML (UI-16), la lógica de validación previa en UI-12 (Checklist de pre-vuelo), '
            'la generación del árbol de nodos y la estructura del payload auditado en los logs del sistema.'
        ),
        'enlace_oficial': 'https://dgii.gov.do/facturacionElectronica/documentacionTecnica/',
    },
    {
        'id': 'decreto-254-06',
        'tipo': 'decreto',
        'tipo_badge': 'Decreto Presidencial',
        'badge_class': 'badge-warning',
        'codigo': 'Decreto Núm. 254-06',
        'titulo': 'Reglamento para la Regulación de la Emisión de Comprobantes Fiscales',
        'organismo': 'Poder Ejecutivo de la República Dominicana',
        'fecha': '19 de junio de 2006',
        'vigencia': 'Vigente',
        'resumen': (
            'Reglamento de aplicación que sentó las bases del control tributario mediante la autorización '
            'de Números de Comprobante Fiscal (NCF), estableciendo las obligaciones de reporte y deberes de facturación.'
        ),
        'articulos_clave': (
            {'articulo': 'Artículo 2', 'titulo': 'Control de la Emisión', 'desc': 'Toda factura emitida en territorio nacional debe contar con un número de comprobante fiscal asignado y validado por la DGII.'},
            {'articulo': 'Artículo 8', 'titulo': 'Autorización Previa de Rangos', 'desc': 'Los contribuyentes deben solicitar de forma periódica las secuencias autorizadas para emitir según su volumen de facturación.'},
        ),
        'impacto_sistema': (
            'Fundamenta la gestión de rangos de secuencias y la obligatoriedad de controlar el número disponible '
            'antes de permitir la generación y despacho del comprobante fiscal.'
        ),
        'enlace_oficial': 'https://dgii.gov.do/legislacion/decretos/Documents/Decreto254-06.pdf',
    },
    {
        'id': 'norma-05-2019',
        'tipo': 'norma',
        'tipo_badge': 'Norma General DGII',
        'badge_class': 'badge-info',
        'codigo': 'Norma General Núm. 05-2019',
        'titulo': 'Disposiciones sobre Modificación de Comprobantes Fiscales y Notas de Crédito',
        'organismo': 'Dirección General de Impuestos Internos (DGII)',
        'fecha': '28 de mayo de 2019',
        'vigencia': 'Vigente',
        'resumen': (
            'Regula los plazos y condiciones para la emisión de Notas de Crédito (E34) y Notas de Débito (E33), '
            'especificando el límite de 30 días para la restitución o deducción de ITBIS facturado previamente.'
        ),
        'articulos_clave': (
            {'articulo': 'Artículo 3', 'titulo': 'Referencia Obligatoria de Factura', 'desc': 'Toda nota de crédito debe referenciar taxativamente el e-NCF del comprobante que modifica o anula.'},
            {'articulo': 'Artículo 5', 'titulo': 'Plazo de 30 Días para ITBIS', 'desc': 'Pasados 30 días de emitida la factura, la nota de crédito no reduce el ITBIS liquidado en el período original sin autorización formal.'},
        ),
        'impacto_sistema': (
            'Determina la obligatoriedad de la sección <InformacionReferencia> en el XML para los comprobantes '
            'de modificación (E33 y E34), vinculando el e-NCF original y la fecha de emisión.'
        ),
        'enlace_oficial': 'https://dgii.gov.do/legislacion/normas/Documents/2019/Norma05-19.pdf',
    },
)

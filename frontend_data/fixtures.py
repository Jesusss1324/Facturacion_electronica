"""Conjunto determinista de registros de ejemplo. No crea ni consulta modelos."""

from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from .entities import Cliente, Factura, EventoLog

FECHA_BASE = datetime(2026, 10, 1, 10, 45, tzinfo=ZoneInfo('America/Santo_Domingo'))


def build_clientes():
    nombres = (
        ('Comercial Nova Caribe, SRL', 'RNC'),
        ('Juan Carlos Pérez Rodríguez', 'Cédula'),
        ('Distribuidora Costa Norte, SAS', 'RNC'),
        ('María Elena Santos Gómez', 'Cédula'),
        ('Tecnología Horizonte, SRL', 'RNC'),
        ('Soluciones Empresariales del Este, SRL', 'RNC'),
        ('Ana Lucía Martínez', 'Cédula'),
        ('Suministros del Atlántico, SRL', 'RNC'),
    )
    personas = (
        'Pedro Luis Ramírez', 'Rosa Isabel Castillo', 'Miguel Ángel Vargas',
        'Laura Patricia Peña', 'José Manuel Duarte', 'Elena Sofía Rivas',
        'Carlos Andrés Núñez', 'Sofía Gabriela Torres', 'Luis Alberto Méndez',
    )
    rubros = ('Servicios', 'Suministros', 'Comercial', 'Distribuidora', 'Soluciones', 'Consultores')
    marcas = ('Mirador', 'Vista Mar', 'Horizonte', 'Buenavista', 'Los Pinos', 'Costa Azul')
    clientes = []
    registro_base = datetime(2026, 1, 15, 9, 34, tzinfo=ZoneInfo('America/Santo_Domingo'))
    for index in range(1, 45):
        if index <= len(nombres):
            nombre, tipo = nombres[index - 1]
        else:
            tipo = 'Cédula' if index % 4 == 0 else 'RNC'
            nombre = f'{rubros[(index - 9) % 6]} {marcas[(index - 9) // 6]}, SRL' if tipo == 'RNC' else personas[index // 4 - 3]
        identificacion = f'{101000000 + index:09d}' if tipo == 'RNC' else f'001{2345000 + index:07d}{index % 10}'
        fecha_registro = registro_base + timedelta(days=(index - 1) * 3, hours=(index * 7) % 14, minutes=(index * 13) % 60)
        clientes.append(Cliente(
            id=index,
            nombre=nombre,
            identificacion=identificacion,
            tipo_identificacion=tipo,
            telefono=f'809-555-{1000 + index:04d}',
            direccion=f'Calle Las Palmas {index}, Santo Domingo',
            email=f'contacto{index:02d}@empresa.example',
            activo=index <= 42,
            fecha_registro=fecha_registro,
        ))
    return tuple(clientes)


def build_facturas(clientes):
    facturas = []
    montos_recientes = ('145280.00', '4750.00', '89400.00', '12890.50', '34500.00')
    fechas_recientes = (
        FECHA_BASE,
        FECHA_BASE.replace(hour=9, minute=12),
        (FECHA_BASE - timedelta(days=1)).replace(hour=16, minute=30),
        (FECHA_BASE - timedelta(days=1)).replace(hour=14, minute=15),
        (FECHA_BASE - timedelta(days=2)).replace(hour=11, minute=5),
    )
    for offset in range(128):
        sequence = 128 - offset
        cliente = clientes[offset % len(clientes)]
        tipo = '31' if cliente.tipo_identificacion == 'RNC' else '32'
        reciente = offset < 5
        fecha = fechas_recientes[offset] if reciente else FECHA_BASE - timedelta(days=3, hours=(offset - 5) * 6)
        monto = Decimal(montos_recientes[offset]) if reciente else Decimal(1500 + sequence * 735).quantize(Decimal('0.01'))
        # Un rechazo entre las cinco recientes y ocho en el resto del historial.
        rechazado = offset == 1 or offset in {13, 27, 41, 55, 69, 83, 97, 111}
        facturas.append(Factura(
            id=sequence,
            e_ncf=f'E{tipo}{sequence:010d}',
            tipo_ecf=tipo,
            cliente_id=cliente.id,
            fecha_emision=fecha,
            monto_total=monto,
            estado='rechazado' if rechazado else 'aprobado',
        ))
    return tuple(facturas)


def build_logs(clientes, facturas):
    import hashlib

    top_events_data = (
        (
            234, datetime(2026, 10, 14, 15, 42, 18, 430000, tzinfo=ZoneInfo('America/Santo_Domingo')),
            'Sistema', 'Daemon / Async', 'dgii', 'Servicio DGII',
            'Factura aprobada por DGII', 'Acuse de timbrado ARECF-000 generado con TrackId DGII-REC-89240004',
            'factura', 4, 'E310000000004', 'correcto', 'Correcto', '', '192.168.1.1',
        ),
        (
            233, datetime(2026, 10, 14, 15, 42, 15, 112000, tzinfo=ZoneInfo('America/Santo_Domingo')),
            'operador', 'Operador fiscal', 'dgii', 'Servicio DGII',
            'Comprobante enviado a DGII', 'POST /fe/recepcion/v1/ecf con envelope SOAP/XML',
            'factura', 4, 'E310000000004', 'informativo', 'Informativo', '', '192.168.1.45',
        ),
        (
            232, datetime(2026, 10, 14, 15, 42, 12, 805000, tzinfo=ZoneInfo('America/Santo_Domingo')),
            'operador', 'Operador fiscal', 'firma', 'Firma digital',
            'Documento firmado con XML-DSig', 'Certificado X.509 emitido por Autoridad de Certificación DGII',
            'factura', 4, 'E310000000004', 'correcto', 'Correcto', '', '192.168.1.45',
        ),
        (
            231, datetime(2026, 10, 14, 15, 42, 9, 914000, tzinfo=ZoneInfo('America/Santo_Domingo')),
            'operador', 'Operador fiscal', 'xml', 'XML e-CF',
            'XML e-CF v1.0 generado', 'Estructura validada contra esquema XSD oficial DGII',
            'factura', 4, 'E310000000004', 'correcto', 'Correcto', '', '192.168.1.45',
        ),
        (
            230, datetime(2026, 10, 14, 14, 18, 3, 18000, tzinfo=ZoneInfo('America/Santo_Domingo')),
            'operador', 'Operador fiscal', 'facturacion', 'Facturación',
            'Factura rechazada por regla RN-008', 'RNC receptor inactivo o suspendido en padrón DGII',
            'factura', 3, 'E310000000003', 'error', 'Error', 'RN-008', '192.168.1.45',
        ),
        (
            229, datetime(2026, 10, 14, 11, 5, 44, 733000, tzinfo=ZoneInfo('America/Santo_Domingo')),
            'operador', 'Operador fiscal', 'clientes', 'Clientes',
            'Cliente creado en directorio', 'Razón Social: Soluciones Empresariales del Este, SRL (RNC 101000006)',
            'cliente', 6, 'CLI-101000006', 'correcto', 'Correcto', '', '192.168.1.45',
        ),
        (
            228, datetime(2026, 10, 14, 10, 59, 12, 381000, tzinfo=ZoneInfo('America/Santo_Domingo')),
            'Sistema', 'Daemon / Async', 'dgii', 'Servicio DGII',
            'Error de comunicación temporal DGII', 'Timeout 504 en receptor de pruebas. Reintento automático agendado.',
            'factura', 2, 'E310000000002', 'advertencia', 'Advertencia', 'HTTP-504', '192.168.1.1',
        ),
        (
            227, datetime(2026, 10, 14, 9, 30, 4, 119000, tzinfo=ZoneInfo('America/Santo_Domingo')),
            'operador', 'Operador fiscal', 'pdf', 'Representación PDF',
            'Representación PDF generada', 'RI-e-CF con código bidimensional QR canónico renderizado',
            'factura', 2, 'E320000000002', 'correcto', 'Correcto', '', '192.168.1.45',
        ),
        (
            226, datetime(2026, 10, 14, 9, 12, 45, 621000, tzinfo=ZoneInfo('America/Santo_Domingo')),
            'operador', 'Operador fiscal', 'dgii', 'Servicio DGII',
            'Validación de reglas DGII exitosa', '14/14 reglas de estructura, montos y RNC aprobadas localmente',
            'factura', 2, 'E320000000002', 'correcto', 'Correcto', '', '192.168.1.45',
        ),
        (
            225, datetime(2026, 10, 14, 8, 0, 1, 2000, tzinfo=ZoneInfo('America/Santo_Domingo')),
            'operador', 'Operador fiscal', 'auth', 'Autenticación',
            'Inicio de sesión de usuario satisfactorio', 'Sesión autenticada para emisión de comprobantes fiscales',
            'sesion', None, 'N/A (Sesión)', 'informativo', 'Informativo', '', '192.168.1.45',
        ),
    )

    logs = []
    for item in top_events_data:
        ev_id, ts, usuario, tipo_usuario, modulo, modulo_display, titulo, desc, ref_tipo, ref_id, ref_code, res, res_disp, err_code, ip = item
        hash_seg = hashlib.sha256(f'ECF-AUDIT-{ev_id}-{ts.isoformat()}-{titulo}-{ref_code}'.encode('utf-8')).hexdigest()
        track_id = f'DGII-REC-{89240000 + ref_id}' if ref_tipo == 'factura' and ref_id else ''
        detalles = {
            'id_evento': f'EVT-{ev_id:05d}',
            'timestamp_iso': ts.isoformat(),
            'protocolo': 'HTTPS / TLS 1.3' if modulo in {'dgii', 'firma', 'xml'} else 'HTTP/2 Interno',
            'metodo': 'POST' if modulo in {'dgii', 'firma', 'xml'} else 'GET',
            'endpoint': f'/fe/{modulo}/v1/ecf' if modulo in {'dgii', 'firma', 'xml'} else f'/{modulo}/',
            'codigo_http': 200 if res == 'correcto' else (504 if res == 'advertencia' else (422 if res == 'error' else 200)),
            'tiempo_respuesta_ms': 110 + (ev_id * 13) % 280,
            'certificado_serial': 'DGII-CA-X509-89240128-SEC',
            'digest_sha256': hash_seg,
            'algoritmo_firma': 'RSA-SHA256 (PKCS#1 v1.5)',
            'track_id': track_id,
            'ip_origen': ip,
            'agente_usuario': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) FacturacionElectronica/2.4',
            'payload_resumen': {
                'modulo': modulo_display,
                'evento': titulo,
                'referencia': ref_code,
                'resultado': res_disp,
                'codigo_regla': err_code or 'N/A',
                'hash_inmutable': hash_seg,
            }
        }
        logs.append(EventoLog(
            id=ev_id, timestamp=ts, usuario=usuario, tipo_usuario=tipo_usuario,
            modulo=modulo, modulo_display=modulo_display, titulo=titulo, descripcion=desc,
            referencia_tipo=ref_tipo, referencia_id=ref_id, referencia_codigo=ref_code,
            resultado=res, resultado_display=res_disp, codigo_error=err_code, ip=ip,
            hash_seguridad=hash_seg, detalles_tecnicos=detalles,
        ))

    base_ts = datetime(2026, 10, 14, 7, 45, 0, tzinfo=ZoneInfo('America/Santo_Domingo'))
    for offset in range(224):
        ev_id = 224 - offset
        ts = base_ts - timedelta(minutes=offset * 27 + (offset * 11 % 17), seconds=(offset * 19) % 60, milliseconds=(offset * 137) % 1000)

        factura = facturas[offset % len(facturas)] if facturas else None
        cliente = clientes[offset % len(clientes)] if clientes else None

        archetype = offset % 9
        if archetype == 0:
            usuario = 'Sistema'
            tipo_usuario = 'Daemon / Async'
            modulo = 'dgii'
            modulo_display = 'Servicio DGII'
            titulo = 'Factura aprobada por DGII'
            desc = f'Acuse de timbrado ARECF-000 generado con TrackId {factura.track_id_display if factura else f"DGII-REC-{89240000 + ev_id}"}'
            ref_tipo = 'factura'
            ref_id = factura.id if factura else ev_id
            ref_code = factura.e_ncf if factura else f'E310000{ev_id:04d}'
            res = 'correcto'
            res_disp = 'Correcto'
            err_code = ''
            ip = '192.168.1.1'
        elif archetype == 1:
            usuario = 'operador'
            tipo_usuario = 'Operador fiscal'
            modulo = 'dgii'
            modulo_display = 'Servicio DGII'
            titulo = 'Comprobante enviado a DGII'
            desc = 'POST /fe/recepcion/v1/ecf con envelope SOAP/XML y certificado'
            ref_tipo = 'factura'
            ref_id = factura.id if factura else ev_id
            ref_code = factura.e_ncf if factura else f'E310000{ev_id:04d}'
            res = 'informativo'
            res_disp = 'Informativo'
            err_code = ''
            ip = '192.168.1.45'
        elif archetype == 2:
            usuario = 'operador'
            tipo_usuario = 'Operador fiscal'
            modulo = 'firma'
            modulo_display = 'Firma digital'
            titulo = 'Documento firmado con XML-DSig'
            desc = 'Certificado X.509 emitido por Autoridad de Certificación DGII'
            ref_tipo = 'factura'
            ref_id = factura.id if factura else ev_id
            ref_code = factura.e_ncf if factura else f'E310000{ev_id:04d}'
            res = 'correcto'
            res_disp = 'Correcto'
            err_code = ''
            ip = '192.168.1.45'
        elif archetype == 3:
            usuario = 'operador'
            tipo_usuario = 'Operador fiscal'
            modulo = 'xml'
            modulo_display = 'XML e-CF'
            titulo = 'XML e-CF v1.0 generado'
            desc = 'Estructura validada contra esquema XSD oficial DGII'
            ref_tipo = 'factura'
            ref_id = factura.id if factura else ev_id
            ref_code = factura.e_ncf if factura else f'E310000{ev_id:04d}'
            res = 'correcto'
            res_disp = 'Correcto'
            err_code = ''
            ip = '192.168.1.45'
        elif archetype == 4:
            usuario = 'operador'
            tipo_usuario = 'Operador fiscal'
            modulo = 'pdf'
            modulo_display = 'Representación PDF'
            titulo = 'Representación PDF generada'
            desc = 'RI-e-CF con código bidimensional QR canónico renderizado'
            ref_tipo = 'factura'
            ref_id = factura.id if factura else ev_id
            ref_code = factura.e_ncf if factura else f'E310000{ev_id:04d}'
            res = 'correcto'
            res_disp = 'Correcto'
            err_code = ''
            ip = '192.168.1.45'
        elif archetype == 5:
            usuario = 'operador'
            tipo_usuario = 'Operador fiscal'
            modulo = 'clientes'
            modulo_display = 'Clientes'
            titulo = 'Cliente registrado en directorio'
            desc = f'Razón Social: {cliente.nombre if cliente else "Empresa"} ({cliente.tipo_identificacion if cliente else "RNC"} {cliente.identificacion if cliente else "101000001"})'
            ref_tipo = 'cliente'
            ref_id = cliente.id if cliente else 1
            ref_code = f'CLI-{cliente.identificacion[:10]}' if cliente else 'CLI-101000001'
            res = 'correcto'
            res_disp = 'Correcto'
            err_code = ''
            ip = '192.168.1.45'
        elif archetype == 6:
            usuario = 'operador'
            tipo_usuario = 'Operador fiscal'
            modulo = 'auth'
            modulo_display = 'Autenticación'
            titulo = 'Inicio de sesión de usuario satisfactorio'
            desc = 'Sesión autenticada para emisión de comprobantes fiscales'
            ref_tipo = 'sesion'
            ref_id = None
            ref_code = 'N/A (Sesión)'
            res = 'informativo'
            res_disp = 'Informativo'
            err_code = ''
            ip = '192.168.1.45'
        elif archetype == 7:
            usuario = 'operador'
            tipo_usuario = 'Operador fiscal'
            modulo = 'facturacion'
            modulo_display = 'Facturación'
            titulo = 'Factura rechazada por regla RN-014'
            desc = 'Secuencia e-NCF fuera de rango o ya reportada ante DGII'
            ref_tipo = 'factura'
            ref_id = factura.id if factura else ev_id
            ref_code = factura.e_ncf if factura else f'E310000{ev_id:04d}'
            res = 'error'
            res_disp = 'Error'
            err_code = 'RN-014'
            ip = '192.168.1.45'
        else:
            usuario = 'Sistema'
            tipo_usuario = 'Daemon / Async'
            modulo = 'dgii'
            modulo_display = 'Servicio DGII'
            titulo = 'Latencia elevada en servicio DGII'
            desc = 'Tiempo de respuesta superó 3,500ms en consulta de TrackId. Reintento programado.'
            ref_tipo = 'factura'
            ref_id = factura.id if factura else ev_id
            ref_code = factura.e_ncf if factura else f'E310000{ev_id:04d}'
            res = 'advertencia'
            res_disp = 'Advertencia'
            err_code = 'HTTP-504'
            ip = '192.168.1.1'

        hash_seg = hashlib.sha256(f'ECF-AUDIT-{ev_id}-{ts.isoformat()}-{titulo}-{ref_code}'.encode('utf-8')).hexdigest()
        track_id = f'DGII-REC-{89240000 + ref_id}' if ref_tipo == 'factura' and ref_id else ''
        detalles = {
            'id_evento': f'EVT-{ev_id:05d}',
            'timestamp_iso': ts.isoformat(),
            'protocolo': 'HTTPS / TLS 1.3' if modulo in {'dgii', 'firma', 'xml'} else 'HTTP/2 Interno',
            'metodo': 'POST' if modulo in {'dgii', 'firma', 'xml'} else 'GET',
            'endpoint': f'/fe/{modulo}/v1/ecf' if modulo in {'dgii', 'firma', 'xml'} else f'/{modulo}/',
            'codigo_http': 200 if res == 'correcto' else (504 if res == 'advertencia' else (422 if res == 'error' else 200)),
            'tiempo_respuesta_ms': 90 + (ev_id * 11) % 270,
            'certificado_serial': 'DGII-CA-X509-89240128-SEC',
            'digest_sha256': hash_seg,
            'algoritmo_firma': 'RSA-SHA256 (PKCS#1 v1.5)',
            'track_id': track_id,
            'ip_origen': ip,
            'agente_usuario': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) FacturacionElectronica/2.4',
            'payload_resumen': {
                'modulo': modulo_display,
                'evento': titulo,
                'referencia': ref_code,
                'resultado': res_disp,
                'codigo_regla': err_code or 'N/A',
                'hash_inmutable': hash_seg,
            }
        }
        logs.append(EventoLog(
            id=ev_id, timestamp=ts, usuario=usuario, tipo_usuario=tipo_usuario,
            modulo=modulo, modulo_display=modulo_display, titulo=titulo, descripcion=desc,
            referencia_tipo=ref_tipo, referencia_id=ref_id, referencia_codigo=ref_code,
            resultado=res, resultado_display=res_disp, codigo_error=err_code, ip=ip,
            hash_seguridad=hash_seg, detalles_tecnicos=detalles,
        ))

    return tuple(logs)

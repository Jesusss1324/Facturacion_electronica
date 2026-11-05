# Entidad local E31/E32

Recreación educativa del receptor y validador de documentos, sin conexión al padrón ni a los servicios de la DGII. No certifica contribuyentes ni concede validez fiscal. Los datos con dígito de control válido son ejemplos sintéticos, no identidades verificadas ante la administración.

## Arranque y acceso

El arranque normal de `manage.py runserver` inicia un segundo servidor, sólo en `127.0.0.1:8001`, con `facturacion_ecf.entity_settings`. El acceso al panel es `http://127.0.0.1:8001/entidad/`, también enlazado desde el menú de facturación. La primera visita permite crear el administrador; no hay usuario/contraseña predeterminados. Después de ese registro la configuración inicial queda cerrada. El inicio de sesión de facturación no da acceso a este panel.

La entidad guarda sus datos en `entidad.sqlite3`; un router impide crear o consultar sus tablas nuevas en `db.sqlite3`. Tiene su propio padrón, rangos, recepción, configuración, auditoría y credenciales. El padrón inicial se carga una vez desde el conjunto demo versionado. Cambiar un cliente de facturación no actualiza este padrón. Los modelos antiguos `ColaContingencia`/`LogTransaccion` se conservan en la base de facturación y no se usan como autoridad.

La credencial de integración es un token aleatorio de la instalación guardado en `.local/entidad-api.key`, excluido de Git. No es la contraseña del administrador. La API requiere `Authorization: Bearer <token>` y conexiones loopback; no acepta emisor distinto al asignado a la instalación. Los formularios administrativos requieren sesión propia, POST y CSRF. Las contraseñas se guardan con el hasher de Django. El acceso se limita después de diez intentos fallidos en cinco minutos. El primer registro sólo debe realizarse desde la computadora local de confianza.

El proceso secundario se ejecuta sin consola adicional y se termina al cerrar normalmente el servidor que lo creó. Si ya hay una entidad funcionando, se reutiliza y no se termina ese proceso ajeno. Un cierre forzado puede dejar el proceso local activo; los documentos y la cola sobreviven en SQLite. El futuro ejecutable deberá conservar este ciclo de arranque y cierre.

## Contrato HTTP local

No se afirma compatibilidad completa con la API DGII: el contrato local es deliberadamente pequeño, con XML UTF-8 como cuerpo, máximo 1 MiB.

- `POST /api/recepciones/`: recibe `application/xml`, registra el documento y devuelve `202` con `trackId`. No lo aprueba durante la recepción.
- `GET /api/recepciones/<uuid>/`: obtiene estado y comprobaciones de esa recepción.
- `GET /api/consulta/?encf=<eNCF>`: recupera la recepción del emisor autorizado cuando se perdió el TrackId. Un `404` JSON `No recibido.` es la única respuesta que permite al cliente reintentar el mismo documento después de un resultado incierto.
- `GET /health/`: identifica el servicio y señala que la firma no está implementada. No revela credenciales.

Mismo emisor/e-NCF y mismos bytes SHA-256: se devuelve el TrackId existente (`200`). Mismo emisor/e-NCF con bytes diferentes: `409`, sin sustituir el original. Incluso un cambio de espacios de un XML recibido se considera contenido diferente: se exige reenviar exactamente el documento guardado. Los intentos y conflictos quedan auditados; no existe una acción para borrar recepciones desde el panel.

La recepción pendiente se procesa automáticamente cada segundo. Desactivar «Automático» permite observar la recepción y luego ejecutar «Procesar ahora». El procesamiento usa una transacción propia de SQLite: un cierre antes de confirmar deja la recepción pendiente y se reanuda al arrancar; no existe un cambio parcial de resultado.

Resultados: `recibido`, `rechazado` o `validado_sin_firma`. Este último indica que las comprobaciones implementadas no encontraron errores; la firma sigue pendiente y no se devuelve `aprobado`. No se traduce un estado desconocido a aceptación.

## Fuentes y XSD

- Catálogo oficial: https://dgii.gov.do/cicloContribuyente/facturacion/comprobantesFiscalesElectronicosE-CF/Paginas/documentacionSobreE-CF.aspx
- Formato e-CF v1.0 (octubre 2025), secciones Encabezado, Detalles, RNCComprador y MontoItem: https://dgii.gov.do/cicloContribuyente/facturacion/comprobantesFiscalesElectronicosE-CF/Documentacin%20sobre%20eCF/Formatos%20XML/Formato%20Comprobante%20Fiscal%20Electr%C3%B3nico%20(e-CF)%20V1.0.pdf
- Servicios DGII, recepción y consulta TrackId: https://dgii.gov.do/cicloContribuyente/facturacion/comprobantesFiscalesElectronicosE-CF/Documentacin%20sobre%20eCF/Informe%20y%20Descripci%C3%B3n%20T%C3%A9cnica/Descripcion%20Tecnica%20Servicios%20DGII.pdf

Los XSD E31/E32 originales están en `dgii_mock/schemas/`; `origen.json` registra sus URL, fecha de descarga y SHA-256. No se descargan al procesar documentos, de modo que se puede trabajar sin internet. La actualización de esquemas debe ser una decisión explícita con nuevas pruebas.

Los archivos publicados contienen un espacio inicial en el nombre del tipo `IndicadorServicioTodoIncluidoType`. Para compilar con libxml2 se normaliza ese espacio léxico en memoria. Los originales no se alteran. Esta compatibilidad queda aplicada tanto a la comprobación completa como a la previa a firma.

El XSD oficial completo exige `FechaHoraFirma` y un elemento final. En esta entrega no se inventa una firma para satisfacerlo. `XSD_CONTENIDO` usa el mismo esquema con sólo esos dos mínimos finales puestos en cero para validar el documento aún no firmado. `XSD_COMPLETO` queda pendiente si no hay firma. Si hay un elemento Signature, se prueba además el esquema completo, pero eso no verifica su criptografía: el XSD usa `processContents=skip` para el elemento final. `FIRMA` siempre queda pendiente en esta etapa.

## Reglas implementadas

Los códigos son propios de esta recreación; no son códigos oficiales RN de DGII.

- `TIPO_ENCF`: sólo E31/E32; tipo y prefijo deben coincidir; diez dígitos de secuencia.
- `XSD_CONTENIDO` / `XSD_COMPLETO`: estructura, orden, tipos y restricciones del esquema, con las salvedades anteriores.
- `IDENTIFICACION_*`: longitud/dígitos y control aritmético local. Referencias técnicas: https://github.com/arthurdejong/python-stdnum/blob/master/stdnum/do/rnc.py y https://github.com/arthurdejong/python-stdnum/blob/master/stdnum/do/cedula.py . No se reproducen listas de excepciones históricas ni se consulta el padrón real.
- `PADRON_EMISOR`: debe existir, estar activo y tener permiso de emisor en el padrón local.
- `PADRON_RECEPTOR`: un comprador identificado debe existir y estar activo; en E31 se requiere además el permiso local de receptor de crédito. Es una política de prueba local, no una descripción completa de las condiciones oficiales.
- `NOMBRE_*`: comparación local de nombre registrado, ignorando mayúsculas y espacios repetidos. No se pretende reproducir toda la política de coincidencia de nombres de DGII.
- `RECEPTOR_OBLIGATORIO`: E31 y E32 desde DOP 250,000 requieren comprador identificado en este perfil. La regla de obligatoriedad procede del formato e-CF. Los casos de comprador extranjero están fuera del perfil implementado.
- `FECHA`: fecha de calendario real; se permite como máximo un día futuro (política local).
- `RANGO`: emisor, tipo, secuencia y fecha dentro de una asignación local activa/vigente. No se consulta un rango autorizado real.
- `VENCIMIENTO_RANGO`: en E31, la fecha declarada coincide con la asignación local.
- `PAGO_CREDITO`: vencimiento no anterior a emisión.
- `PERFIL_18`: entre 1 y 100 líneas, gravadas al 18%, precios sin ITBIS y sin recargos, exenciones, otras tasas ni secciones de ajustes globales. Se admiten pagos al contado/crédito; las operaciones gratuitas también quedan fuera del perfil. Es un subconjunto deliberado para esta etapa, no una restricción general de E31/E32.
- `CALCULO_LINEAS`: número consecutivo, cantidad positiva, precio no negativo y descuento acotado. `MontoItem = cantidad × precio − descuento`, sin sumar ITBIS; el formato oficial define el importe de línea antes del impuesto. Se redondea el bruto y el ITBIS por línea a centavos con ROUND_HALF_UP, coherente con la aplicación.
- `TOTALES`: las bases, los ITBIS y el total coinciden con las sumas de las líneas.
- `PAGOS`: la suma de importes de formas de pago coincide con el total (perfil local).
- `FIRMA`: pendiente, incluso si hay Signature. No se afirma certificado válido ni integridad criptográfica.
- `RFCE`: para E32 menor de DOP 250,000 se señala la extensión pendiente. Esta entidad admite el E32 completo para diagnóstico local; no reproduce aún el circuito oficial de resumen RFCE. Nunca presenta ese diagnóstico como aceptación fiscal.

El generador de facturación usa ahora raíz `ECF` sin namespace, versión, orden de campos, códigos numéricos de pago y `MontoItem` antes del ITBIS. No se envía una unidad textual como si fuera un código de la tabla oficial; `UnidadMedida`, opcional en el esquema, se omite hasta incorporar esa tabla. Los límites de nombre y dirección se ajustan al XSD en los formularios. No se truncan valores silenciosamente.

## Escenarios y recuperación

- Normal: guardar recepción, después validar y permitir consulta.
- Indisponible: responder `503` sin guardar recepción.
- Respuesta perdida: guardar recepción y devolver `504`; el cliente consulta y recupera el mismo TrackId.
- Demora: guardar recepción con fecha futura de procesamiento; las consultas muestran `recibido` hasta entonces.
- Pausa manual: no se procesa automáticamente; el administrador puede avanzar una recepción.

El emisor confirma la intención de envío antes de hacer HTTP, sin mantener transacciones abiertas durante la conexión. Usa el mismo XML guardado y su huella. Un timeout, cierre durante entrega o respuesta no concluyente obliga a consultar. Sólo después de una consulta explícita «No recibido» se habilita otro envío, con la misma secuencia y bytes. Una respuesta de otro emisor, e-NCF o huella detiene la operación como conflicto. Los bloqueos temporales impiden que un trabajador vencido sobrescriba el resultado de otro.

## Datos de demostración

Las migraciones corrigen únicamente identificaciones conocidas del conjunto demo y el RNC inicial del emisor, con dígitos de control y sin colisiones. Conservan nombres, identificadores de registros y vínculos de facturas. No certifican que esas identificaciones pertenezcan a personas reales. Los registros que el usuario ya cambió se conservan cuando no coinciden con los valores demo conocidos. Las instantáneas de operaciones ya reservadas no se reescriben: si contienen datos anteriores incompatibles, la entidad los rechazará y mostrará el motivo.

## Ejecución y pruebas

Instalar las dependencias y ejecutar migraciones de facturación como de costumbre. El arranque normal inicializa la base de la entidad automáticamente. Para operación manual: `python manage.py migrate --database=entidad` y `python manage.py runserver 127.0.0.1:8001 --noreload --settings=facturacion_ecf.entity_settings`.

`manage.py test` usa bases de pruebas independientes para ambas conexiones. `dgii_mock.tests_entity` cubre esquemas, reglas, autenticación, CSRF, aislamiento, duplicados, escenarios y panel. `frontend_data.tests_entity_client` cubre entrega, consulta, recuperación y ausencia de aprobación automática. El cambio no implementa aún certificados de desarrollo, firma criptográfica, RFCE ni integración oficial.

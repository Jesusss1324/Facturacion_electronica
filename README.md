# Facturación Electrónica

Aplicación Django para gestionar clientes y demostrar el flujo de comprobantes electrónicos E31 y E32.

## Estado actual

La interfaz incluye acceso, inicio con indicadores, directorio de clientes, alta, edición, detalle y cambio de estado. El asistente permite elegir tipo y receptor, completar datos generales, gestionar conceptos, calcular descuentos e ITBIS al 18%, confirmar totales y revisar el borrador.

También están implementadas las pantallas de procesamiento simulado, resultado, detalle de factura, historial, visualización XML y representación impresa, además de bitácora y marco legal. Las rutas de descarga XML y PDF devuelven archivos adjuntos para usuarios autenticados. El PDF se genera en el servidor con ReportLab y admite varias páginas; imprimir sigue siendo una acción independiente del visor.

### Alcance de los datos

`frontend_data/` contiene las entidades que consumen las pantallas y un repositorio ORM persistente. Clientes, facturas, borradores, conceptos, totales confirmados y eventos se almacenan en `db.sqlite3`. Los cambios sobreviven a cierres y reinicios y son visibles desde otras instancias del programa que abran la misma base.

La migración `frontend_data.0002_cargar_demo` carga una sola vez los 44 clientes, las 128 facturas y los 234 eventos originales, conservando identificadores, fechas, importes y estados. La marca `demo-v1` evita duplicaciones o restauraciones involuntarias: ejecutar de nuevo `migrate` o `cargar_demo` no sobrescribe ediciones ni repone registros eliminados. Si hay datos previos sin marca de carga, se detiene la importación sin sobrescribirlos.

Los conceptos se conservan como instantáneas JSON ordenadas, con UUID y decimales serializados como texto; los importes de factura usan campos decimales. Las identificaciones y los e-NCF tienen restricciones únicas, y cada borrador puede vincularse a una sola factura. La pantalla usa las mismas entidades y plantillas que antes.

La persistencia actual vive en los modelos de `frontend_data/models.py`; los modelos fiscales iniciales de `comprobantes/` y `emisores/` se conservan, sin duplicar allí los datos demo. Su integración con el circuito fiscal corresponde a la etapa siguiente. El repositorio en memoria se mantiene exclusivamente como alternativa explícita para pruebas unitarias (`FRONTEND_DATA_BACKEND="memory"`); la aplicación usa `sqlite` por defecto.

Los datos iniciales incluyen 44 clientes (42 activos) y 128 comprobantes (119 aprobados y 9 rechazados). Estos estados proceden de los registros de demostración.

### Comportamiento de emisión local

1. El servidor exige totales confirmados y una huella del borrador vigente; vuelve a comprobar conceptos, condiciones e importes y que el receptor esté activo.
2. La primera emisión valida el borrador, reserva una secuencia local E31/E32 y guarda una factura en estado `generado` junto con una operación única. No se aprueba automáticamente ni se transmite información a la DGII.
3. Un doble clic, reintento o solicitud simultánea del mismo borrador devuelve la misma factura, sin consumir otra secuencia. El borrador emitido no admite modificaciones.
4. La relación borrador-factura se guarda en SQLite con una restricción única. Las escrituras usan transacciones IMMEDIATE y un tiempo de espera de 20 segundos para serializar cambios en esta instalación local, también entre procesos. La emisión repetida recupera la factura guardada después de reiniciar. Los contadores locales se guardan en `SecuenciaLocal`; los rangos fiscales autorizados y el circuito externo siguen pendientes.
5. XML y PDF son representaciones de demostración, sin validez fiscal. El XML se construye con ElementTree para escapar nombres, direcciones y conceptos que contengan `&`, `<` o `>`. No se incluyen firmas ni certificados ficticios. La vista previa del borrador no asigna un e-NCF.

### Comportamiento esperado de una integración real

La emisión deberá guardar un comprobante persistente e inmutable a partir del borrador validado, reservar una secuencia de forma atómica, generar y validar el XML contra el esquema aplicable y firmarlo con el certificado del emisor. Después deberá transmitirlo al servicio correspondiente, guardar la respuesta e identificador de seguimiento y consultar su resultado cuando corresponda.

El estado debe reflejar el resultado efectivo de cada etapa: generado, firmado, enviado, aceptado o rechazado. Un tiempo de espera debe conservar la identidad de la operación para consultar o reintentar sin duplicar el comprobante; no equivale a una aceptación. Las descargas deberán corresponder al documento guardado de esa emisión. La bitácora deberá registrar las operaciones reales.

Estas etapas externas, la validación XSD, el certificado, las reglas fiscales definitivas, el control de secuencias autorizado y la configuración de producción siguen pendientes. Los textos de simulación no acreditan una emisión fiscal.

## Desarrollo local (PowerShell)

Requiere Python 3.12 o superior. Dependencias en `requirements.txt`.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate --noinput
.\.venv\Scripts\python.exe manage.py runserver
```

Abrir http://127.0.0.1:8000/acceso/iniciar-sesion/ con `user` / `1234`.
El acceso local está definido en `usuarios/frontend_auth.py`, requiere `DEBUG=True` y `FRONTEND_AUTH_ENABLED=True` y utiliza cookies firmadas sin usuarios ni sesiones SQL. Al desactivarlo se utiliza la autenticación habitual de Django.

## Rutas principales

- `/inicio/`: indicadores y comprobantes recientes.
- `/clientes/`, `/clientes/nuevo/`, `/clientes/<pk>/`, `/clientes/<pk>/editar/`: gestión de clientes.
- `/facturas/nueva/tipo/`: selección E31/E32.
- `/facturas/borradores/<uuid>/cliente/`, `datos/`, `items/`, `totales/`, `revision/`: pasos del borrador.
- `/facturas/borradores/<uuid>/emitir/`: emisión local mediante POST con protección CSRF.
- `/facturas/`: historial con búsqueda, filtros y paginación.
- `/facturas/<pk>/`: detalle; sufijos `procesamiento/`, `resultado/`, `xml/`, `pdf/` para las pantallas posteriores.
- `/facturas/<pk>/xml/descargar/` y `/facturas/<pk>/pdf/descargar/`: descargas autenticadas.

Consultar los archivos `bitacora/urls.py` y `core/urls.py` para bitácora y marco legal. El mapa histórico de pantallas está en `docs/estructura-ui.md`; las rutas actuales y este README describen el alcance vigente.

## Comprobaciones

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test --noinput
```

La suite general crea y destruye una base SQLite de pruebas; no usa la base de negocio. Los módulos de interfaz basados en `SimpleTestCase` usan repositorios en memoria. Las pruebas cubren acceso, validación, cálculos, navegación, emisión, documentos y controles de concurrencia.

## Organización y próximos pasos

- `core/`, `templates/`, `static/`: estructura común, navegación, estilos y comportamiento del navegador.
- `clientes/`, `comprobantes/`, `bitacora/`: formularios, vistas y pruebas de cada módulo.
- `frontend_data/`: modelos y repositorio SQLite, carga inicial versionada, entidades y alternativa en memoria para pruebas.
- `usuarios/`, `emisores/`, `dgii_mock/`: acceso y estructura de backend existente; el módulo mock no representa una conexión real.

Paso 1 completado: almacenamiento SQLite con los datos originales y la interfaz actual. Paso 2 completado: operaciones locales, reserva de secuencias y recuperación. Próximos pasos: entidad local HTTP, validación XSD, certificados de desarrollo, recuperación de envíos y empaquetado Windows .exe. Las emisiones nuevas quedan pendientes de integración; este paso no implementa todavía las decisiones de la entidad fiscal. Al conectar SQL, trasladar búsqueda y paginación al ORM, conservar la validación del servidor y añadir restricciones de unicidad. `static/` contiene fuentes; `staticfiles/` se reserva para `collectstatic`. La configuración incluida es de desarrollo.


## Conservación de datos

La base `db.sqlite3` está excluida de Git. En otra computadora se crean las tablas y los datos iniciales con `manage.py migrate --noinput`. No se ejecutan migraciones ni se cargan fixtures durante una petición HTTP o al importar un módulo.

Para respaldar esta etapa, cerrar el servidor y copiar `db.sqlite3` a una ubicación segura. No borrar el archivo para actualizar el código. La limpieza de la demostración se hará posteriormente de forma explícita; este cambio no incluye ninguna limpieza automática. El ejecutable y la ubicación definitiva de los datos por instalación corresponden a una etapa posterior.

Las pruebas SQL de `frontend_data.tests_sqlite` comprueban carga única, conservación entre instancias y procesos, concurrencia de emisión, integridad de importes y UUID, restricciones y pantallas/descargas sin sustituir el repositorio. La autenticación local de desarrollo continúa como antes, con cookie firmada; la gestión definitiva de usuarios queda fuera de este paso.


Los clientes, comprobantes y eventos ya no se generan desde listas Python: el único conjunto inicial está en `frontend_data/migrations/demo_v1.json`, utilizado para la primera migración y las pruebas. En ejecución se consulta SQLite. Los datos de la empresa emisora también se almacenan en `ConfiguracionEmisor` y se consultan desde las vistas; `emisor_v1.json` sólo inicializa instalaciones nuevas. Se eliminaron los casos especiales por importe de factura que reemplazaban los valores calculados por ejemplos fijos.


## Paso 2: operaciones, secuencias y recuperación

Cada emisión nueva crea, en una sola transacción SQLite IMMEDIATE, una factura, una operación con UUID, una reserva por tipo E31/E32 y un evento de bitácora. Las restricciones únicas vinculan el borrador, la factura y la reserva. La secuencia siguiente se inicializa una sola vez a partir del mayor e-NCF existente; después avanza por contador persistente, sin recalcularse por el número de facturas. No se reutilizan reservas al reiniciar ni al repetir una solicitud. Un fallo dentro de la transacción inicial revierte todo. Una operación ya confirmada conserva su número aunque falle la preparación posterior.

`SecuenciaLocal` permite desactivar un contador, indicar un límite o un vencimiento. El servicio rechaza reservas agotadas, vencidas, desactivadas o que colisionen con el historial. Estos contadores son de desarrollo y no equivalen a rangos autorizados por DGII. No hay pantalla de administración de rangos en esta etapa.

La operación conserva una instantánea de emisor, receptor, conceptos e importes. El XML local se prepara desde esa instantánea, se guarda con su SHA-256 y se reutiliza en las descargas. Las modificaciones posteriores del cliente o de la configuración no cambian el XML reservado.

Estados actuales de operación:

- `pendiente`: en cola para preparar el documento local.
- `procesando`: un trabajador dispone de un token y un bloqueo temporal de 60 segundos.
- `preparada`: XML representativo guardado; pendientes XSD, firma y entidad local.
- `consultar`: hay una marca de envío con resultado incierto; no se retransmite automáticamente.

Al arrancar `manage.py runserver`, se recuperan bloqueos vencidos y se inicia un trabajador local que revisa la cola cada 2 segundos. Un bloqueo vigente se respeta, incluso si otro proceso arranca. Un trabajador cuyo token haya vencido no puede guardar su resultado encima del de otro. Los errores de preparación se guardan con un próximo intento y espera creciente, hasta 30 minutos. Cerrar y abrir el navegador no crea otra operación.

El mismo procesamiento está disponible con `manage.py procesar_emisiones` (una pasada) o `manage.py procesar_emisiones --continuo`. Otros despliegues, incluido el futuro ejecutable, deberán iniciar este trabajador junto con el servidor; no se hacen consultas SQL en `AppConfig.ready`.

La pantalla `/facturas/<pk>/procesamiento/` muestra el estado real de la operación y consulta su estado sin modificar registros. El reintento local requiere POST y CSRF. Los parámetros de simulación no fuerzan una aceptación para las operaciones nuevas. La pantalla de resultado redirige al seguimiento mientras no existe una respuesta externa.

La recuperación de un trabajo local interrumpido lo devuelve a la cola. Si hay una marca persistente de envío, lo mueve a `consultar`: la próxima integración deberá consultar a la entidad antes de decidir un reenvío del mismo documento. En este paso no hay llamadas de red, certificado, firma, validación XSD ni aceptación/rechazo externos. El historial de demostración anterior permanece intacto.


## Paso 3: entidad local E31/E32

El arranque de facturación inicia una entidad HTTP independiente en `http://127.0.0.1:8001/entidad/`, con base `entidad.sqlite3` y credenciales administrativas propias. La primera visita permite crear ese administrador, sin contraseña predeterminada. El menú de facturación incluye el enlace al panel. No requiere hosting, DNS ni conexión a DGII. Los esquemas se conservan localmente para funcionamiento sin internet.

La entidad incluye padrón independiente, asignación de rangos, recepción con TrackId, procesamiento automático o manual, auditoría, escenarios de indisponibilidad/demora/respuesta perdida y detalle de cada comprobación. Se validan contenido XML contra XSD E31/E32, identificaciones, padrón, rangos, importes y duplicados. Un duplicado idéntico recupera su recepción; un documento diferente con el mismo e-NCF genera conflicto.

Se corrigieron las identificaciones conocidas del conjunto de demostración y el RNC del emisor para las comprobaciones locales, preservando vínculos y registros modificados por el usuario. Los números estructuralmente válidos no acreditan registro real.

La entrega local confirma su intención antes de hacer HTTP y consulta la recepción después de un timeout o reinicio. Sólo una confirmación de «No recibido» habilita reenviar los mismos bytes y secuencia. Los datos de facturación y los de la entidad no se sincronizan automáticamente.

La firma sigue siendo la siguiente etapa: un documento sin errores se marca `validado_sin_firma`, nunca `aprobado`. Se distingue la validación de contenido previo a firma de la validación completa del XSD; el esquema exige la sección de firma. El circuito RFCE de E32 de bajo monto también queda documentado como extensión pendiente. Las políticas locales se distinguen expresamente de las reglas oficiales.

Fuentes, versiones, normalización del esquema publicado, catálogo de reglas, contrato HTTP, perfil soportado y limitaciones: [docs/entidad-local.md](docs/entidad-local.md).

Las rutas opcionales `FACTURACION_DB`, `ENTIDAD_DB`, `LOCAL_ENTITY_URL` y `LOCAL_ENTITY_TOKEN_FILE` permiten pruebas aisladas y el futuro empaquetado. No hace falta configurarlas para el arranque local normal. La credencial de integración y los registros operativos de la entidad se guardan bajo `.local/`, excluido de Git. No publiques esa carpeta ni las bases.

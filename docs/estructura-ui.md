# Estructura de interfaz

## Alcance

Esta etapa organiza la base de Django según la especificación funcional y las
referencias visuales de `ESPECIFICACIÓN FUNCIONAL UI_UX.pdf` y `Pantallas.pdf`.
Los documentos son referencias de estructura y diseño; la solicitud del usuario
determina el alcance de implementación y los textos finales.

UI-01 ya está implementada con acceso local de frontend y UI-02 muestra
el inicio con datos de negocio definidos en código. UI-03 implementa el directorio
de clientes sobre la misma fuente y UI-04 permite registrar clientes en memoria; las demás pantallas
se desarrollarán una por una sobre esta navegación. No se
incorporan inventario, contabilidad, nómina, registro público ni anulación de
facturas. UI-20 corresponde a estados de componentes y respuestas de error;
no necesita un módulo adicional en el menú.

## Responsabilidades y carpetas

```text
facturacion_ecf/                 Configuración e inclusión de rutas por módulo
core/                           Base de interfaz y metadatos de navegación
  navigation.py                 Menú, títulos, secciones e identificación UI
  context_processors.py         Contexto común de las plantillas
  views.py                      Inicio, vistas temporales y respuestas de error
  urls.py                       Entrada principal e Inicio
  tests.py                      Contratos de navegación, acceso y métodos HTTP
  tests_dashboard.py            Pruebas de Inicio sin acceso a la BD
frontend_data/                  Fuente local compartida durante el frontend
  entities.py                   Registros de clientes, facturas y resúmenes
  fixtures.py                   Valores de ejemplo deterministas
  repository.py                 Consulta y resumen en memoria
  tests.py                      Coherencia de registros sin acceso a la BD
usuarios/
  urls.py                       Entrada y salida de sesión
  forms.py                      Validación y textos del inicio de sesión
  views.py                      LoginView con redirección segura
  templates/usuarios/           Pantalla UI-01 implementada
clientes/
  urls.py                       Directorio, alta, detalle, edición y estado
  views.py                      Directorio y cambio de estado en memoria
  tests.py                      Pruebas del directorio sin acceso a la BD
  templates/clientes/           UI-03 y UI-04 implementadas; futuras UI-05 a UI-06
comprobantes/
  urls.py                       Asistente, historial y documentos
  templates/comprobantes/       Futuras pantallas UI-07 a UI-18
bitacora/
  urls.py                       Consulta de eventos
  templates/bitacora/           Futura pantalla UI-19
emisores/                       Datos y certificados del emisor existentes
dgii_mock/                      Integración y registros técnicos existentes
templates/
  base.html                     HTML, carga única de CSS/JS y bloques de extensión
  layouts/app.html              Layout privado con menú y encabezado
  layouts/public.html           Layout de acceso y errores
  includes/                     Fragmentos compartidos
  core/pending.html             Única plantilla de las pantallas pendientes
  core/inicio.html              Pantalla UI-02 implementada
  errors/                       Respuestas 400, 403, 404 y 500
static/
  css/global.css                Tokens y componentes compartidos
  css/pages/                    Excepciones de estilo por módulo, si hacen falta
  js/app.js                     Navegación móvil compartida
  js/pages/                     Comportamientos específicos de cada módulo
  img/                          Recursos gráficos locales
```

`clientes` y `bitacora` organizan la interfaz, sin crear modelos duplicados.
`Receptor` continúa en `comprobantes.models` y `LogTransaccion` continúa en
`dgii_mock.models`. Los servicios de negocio deben quedar en sus módulos, no en
`core` ni en las plantillas. Al implementar un módulo, añadir sus `views.py`,
`forms.py` y servicios cuando la funcionalidad lo necesite.

## Mapa de rutas

Todas las rutas tienen nombres y namespaces para usar `reverse()` o `{% url %}`.
Las URLs con `/` final evitan variantes innecesarias.

```text
/                                        core:index -> /inicio/
/inicio/                                 core:inicio                  UI-02
/acceso/iniciar-sesion/                   usuarios:login               UI-01
/acceso/cerrar-sesion/                    usuarios:logout              POST

/clientes/                               clientes:listado             UI-03
/clientes/nuevo/                         clientes:crear               UI-04
/clientes/<pk>/                          clientes:detalle             UI-05
/clientes/<pk>/editar/                   clientes:editar              UI-06
/clientes/<pk>/estado/                   clientes:cambiar_estado      POST

/facturas/                               comprobantes:historial       UI-18
/facturas/nueva/                         comprobantes:nueva -> tipo
/facturas/nueva/tipo/                    comprobantes:tipo            UI-07
/facturas/borradores/<uuid>/cliente/      comprobantes:cliente         UI-08
/facturas/borradores/<uuid>/datos/        comprobantes:datos           UI-09
/facturas/borradores/<uuid>/items/        comprobantes:items           UI-10
/facturas/borradores/<uuid>/totales/      comprobantes:totales         UI-11
/facturas/borradores/<uuid>/revision/     comprobantes:revision        UI-12
/facturas/borradores/<uuid>/emitir/       comprobantes:emitir          POST
/facturas/<pk>/procesamiento/            comprobantes:procesamiento   UI-13
/facturas/<pk>/resultado/                comprobantes:resultado       UI-14
/facturas/<pk>/                          comprobantes:detalle         UI-15
/facturas/<pk>/xml/                      comprobantes:xml             UI-16
/facturas/<pk>/pdf/                      comprobantes:pdf             UI-17
/facturas/<pk>/xml/descargar/             comprobantes:descargar_xml
/facturas/<pk>/pdf/descargar/             comprobantes:descargar_pdf

/bitacora/                               bitacora:listado             UI-19
/bitacora/<pk>/                          bitacora:detalle             UI-19
/admin/                                  Administración Django existente
```

En Python, los argumentos dinámicos son `pk` y `borrador_id`. `pk` es un entero
interno: el e-NCF se presenta como dato del comprobante, sin convertirse en
identificador de las rutas.

El asistente reserva un UUID para cada futuro borrador. Esto permitirá conservar
datos al retroceder y distinguir varias facturas abiertas simultáneamente. La
persistencia del borrador **todavía no está implementada**. Al desarrollar UI-07,
la selección del tipo creará o recuperará el borrador y abrirá UI-08 con su UUID.
Las etapas posteriores comprobarán propiedad y requisitos antes de habilitar
avances; el indicador compartido no concede acceso ni valida el flujo.

Tras emitir, el proceso utilizará el ID del comprobante. La consulta de
procesamiento no deberá ejecutar la emisión mediante GET. Un reintento deberá
usar la misma operación, sin asignar otro e-NCF.

## Plantillas y estilos

Una pantalla privada extenderá `layouts/app.html`; el inicio de sesión extiende
`layouts/public.html`, ajustando su composición con los bloques `public_brand`,
`public_shell_class`, `public_content_class` y `public_footer`.
Cada plantilla específica vive dentro de la aplicación
que la implementa. No se crean veinte copias del layout.

Ejemplo de estructura para una pantalla de clientes:

```django
{% extends 'layouts/app.html' %}
{% block page_description %}
  <p class="text-muted">Consulta y administra tus clientes.</p>
{% endblock %}
{% block page_actions %}
  <a class="btn btn-primary" href="{% url 'clientes:crear' %}">Nuevo cliente</a>
{% endblock %}
{% block content %}
  {# Aquí se implementarán la búsqueda, los filtros y el directorio. #}
{% endblock %}
```

Los bloques disponibles son `title`, `extra_css`, `extra_js`, `page_header`,
`page_title`, `page_description`, `page_actions`, `before_content` y `content`.
La navegación activa, el título y las migas se resuelven desde `SCREENS`, según
el nombre de la ruta. El identificador UI permanece en el código, sin mostrarse
como texto técnico al usuario.

`global.css` se carga una sola vez y organiza sus reglas en capas:

1. `tokens`: colores, tipografía, espacios, radios, sombras y dimensiones.
2. `base`: normalización, tipografía, foco visible y movimiento reducido.
3. `layouts`: estructura privada/pública y adaptación móvil.
4. `components`: botones, tarjetas, campos, tablas, estados, alertas, pasos y diálogos.
5. `utilities`: clases pequeñas para texto, distribución y accesibilidad.

Cambiar las variables de `:root` actualiza todas las pantallas. Usar
`.btn-primary`, `.card`, `.form-control`, `.data-table`, `.badge-*` y `.alert-*`
evita estilos repetidos. Los estados siempre deben incluir texto; el color no
es su único indicador. Los componentes definidos son una base de estilos, no
funcionalidades de formularios, tablas o diálogos ya terminadas.

Si una pantalla necesita reglas propias, cargarlas desde `extra_css` y
declararlas en `@layer components` con un selector de módulo. Evitar estilos
inline y colores aislados. El JavaScript del módulo se carga desde `extra_js`.
No se requieren un framework frontend ni recursos de una CDN.

## Acceso y comportamiento pendiente

- UI-01 admite `user` / `1234` durante el desarrollo con `DEBUG=True` y
  `FRONTEND_AUTH_ENABLED=True`. Las credenciales viven en `usuarios/frontend_auth.py`;
  la identidad se reconstruye en memoria y la sesión usa una cookie firmada.
  No crea registros de usuario ni actualiza `last_login` o sesiones en SQLite.
  Al desactivar este modo se utiliza el backend habitual de Django.
  Conserva el usuario ante errores, nunca vuelve a mostrar la contraseña y
  utiliza el mismo mensaje para credenciales incorrectas o cuentas inactivas.
  La sesión existente evita repetir el login. El parámetro `next` sólo admite
  destinos permitidos por Django; por defecto se redirige a `core:inicio`.
  El formulario funciona sin JavaScript. El script añade visibilidad de
  contraseña, foco de errores e indicación durante el envío real.
- Las secciones operativas requieren una sesión de Django.
- Cerrar sesión usa POST y CSRF; nunca un enlace que modifique la sesión por GET.
- El cambio de estado de clientes usa POST y CSRF, y actualiza sólo la fuente en memoria.
- Las acciones de emisión reservan POST, con respuesta 501.
- Las descargas pendientes responden 501, sin generar archivos ficticios.
- Los logs sólo reservan consultas, sin edición ni eliminación.
- Los permisos por rol y la pertenencia de cada registro se implementarán en
  las vistas reales, antes de consultar o modificar datos.
- Los errores comparten textos y estilos. Los handlers 400/404/500 de Django
  se muestran con `DEBUG=False`; el modo de depuración conserva sus páginas técnicas.

La plantilla temporal sólo demuestra que la ruta y el layout existen. No busca
registros por los IDs recibidos ni afirma que una factura o un cliente exista.
Las futuras vistas harán esa búsqueda y devolverán 404 cuando corresponda.

## Criterios de texto

La interfaz trata al sistema como una aplicación de facturación real: nombres
claros de operaciones, estados explícitos y mensajes accionables. No se copian
etiquetas académicas, controles de evaluación ni barras para fabricar estados
desde las referencias visuales.

Las referencias a una simulación sólo proceden si describen una integración que
realmente sea simulada. El nombre técnico `dgii_mock` se conserva internamente;
esta etapa no presenta ninguna emisión ni aceptación como si hubiese ocurrido
ante la DGII. Cuando se implemente la comunicación, su entorno real deberá
identificarse con precisión, sin inventar una conexión de producción.

## Desarrollo gradual

UI-10 añade `comprobantes/views_items.py` y `comprobantes/items.py` para gestionar
las líneas del borrador en memoria. El formulario valida cantidades, precios y
descuentos; el servidor calcula importes con `Decimal` y redondeo a centavos.
La vista previa usa la misma plantilla y cálculo que las líneas guardadas;
previsualizar no modifica el borrador. Los POST de alta, edición y eliminación
usan CSRF y una revisión de líneas para detectar cambios desde otra pestaña.
El paso incluye un máximo de 100 conceptos e ITBIS fijo del 18% según el alcance
actual. No asigna e-NCF ni emite documentos.

UI-11 (`views_totales.py` y `totales.py`) recalcula el resumen con las mismas
reglas de UI-10 y valida las condiciones generales. El guardado conserva una
copia de los totales y una huella de las líneas y condiciones en memoria. Un
cambio posterior o una diferencia aritmética bloquea el avance hasta recalcular
con POST y CSRF. Cada acción compara también la huella recibida con el borrador
actual bajo el bloqueo del repositorio. GET sólo consulta. El detalle funciona
como sección sin JavaScript y como diálogo con JavaScript. UI-12 sigue reservada.

Para implementar una pantalla:

1. Añadir su plantilla, extendiendo el layout correspondiente.
2. Crear su vista y, si corresponde, el formulario y servicio de negocio.
3. Reemplazar únicamente su vista temporal en el `urls.py` del módulo.
4. Conservar su nombre de ruta y actualizar los metadatos cuando sea necesario.
5. Probar permisos, datos y acciones reales; sustituir la expectativa 501 de
   esa pantalla en las pruebas de estructura por su comportamiento definitivo.

UI-01 (acceso), UI-02 (inicio), UI-03 (directorio) y UI-04 (alta) están terminadas. Orden sugerido para continuar: UI-05 a UI-06 (clientes), UI-07 a
UI-12 (asistente), UI-13 a UI-17 (emisión y documentos), UI-18 (historial) y UI-19
(logs). Los estados de UI-20 se incorporarán durante cada implementación.

Durante la construcción del frontend, las pantallas usarán `frontend_data.get_repository()`
como fuente de datos de negocio. No se añaden modelos, migraciones ni cargas de
datos a SQLite. Los registros son objetos inmutables en código; las próximas
pantallas podrán consultar las mismas identificaciones de cliente y factura.
Los formularios se desarrollarán sobre esta fuente, sin activar persistencia en
la BD hasta que se solicite la conexión al backend.

UI-03 busca por nombre o identificación, ignorando tildes y separadores; muestra
seis registros por página y conserva búsqueda y estado en la URL. Los contadores
de filtros corresponden a la búsqueda actual. La navegación funciona con GET;
JavaScript añade actualización parcial, búsqueda al escribir y esqueletos mientras
hay una petición real, sin retardos artificiales ni controles para fabricar estados.
El cambio de estado pide confirmación y reemplaza el registro en memoria; se
refleja también en Inicio y se reinicia al reiniciar el proceso. Esta fuente es
temporal y local a cada proceso, sin persistencia ni sincronización entre servidores.

UI-04 valida en Python identificación, nombre y contactos opcionales. Normaliza
guiones y espacios y busca duplicados con un índice en memoria por identificación.
El repositorio protege el alta simultánea y asigna IDs; los clientes nuevos nacen
activos y se muestran en el directorio. No existe conexión al padrón DGII ni se
certifica la validez fiscal: sólo se comprueba el formato y la unicidad local.
El formulario funciona sin JavaScript; éste ajusta etiquetas y evita doble envío.

Al conectar el backend, conservar búsqueda, filtros, paginación y validación en
el servidor. Sustituir el repositorio por consultas SQL con índices y restricción
de unicidad según los campos y consultas reales; revisar planes de ejecución,
conteos y consultas repetidas con volúmenes representativos. No descargar el
directorio completo para filtrarlo en el navegador. Esta optimización y los
cambios de BD se implementarán después de completar el frontend.

Los campos RNC, cédula y teléfono admiten entrada numérica con guiones automáticos;
el servidor vuelve a validar tipo, longitud y caracteres. El teléfono se normaliza
a `809-555-1044` (10 dígitos). El alta devuelve al directorio sin filtros.
Los textos tienen límites, normalización de espacios y rechazo de caracteres de
control; Django escapa su salida HTML. Conservar apóstrofes y otros caracteres
legítimos: la defensa contra inyección SQL debe ser el ORM o consultas
parametrizadas, nunca interpolar entradas en SQL ni confiar en quitar comillas.

Inicio calcula sus tarjetas a partir de todos los registros y obtiene las cinco
facturas más recientes por fecha. Los enlaces al detalle usan el ID del mismo
registro que posteriormente consultará la pantalla de factura. El formato de
importes RD$ es compartido en `core.templatetags.ui_format`, y las fechas se
muestran en el horario de República Dominicana.

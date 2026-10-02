# Facturación Electrónica

Aplicación Django para la gestión de clientes y comprobantes electrónicos.

## Estado de esta etapa

Se ha preparado la **estructura de la interfaz**, con rutas, navegación, layouts
y estilos compartidos. **UI-01 (inicio de sesión) está implementada** con
autenticación de Django, validación de campos, errores de credenciales y
redirección al inicio o a la sección solicitada.

**UI-02 (Inicio) también está implementada**, con saludo del usuario, cuatro
tarjetas de resumen y las cinco facturas más recientes. Los datos de negocio
provienen de `frontend_data/`, un conjunto de registros en código que no consulta
ni modifica SQLite. En desarrollo está habilitado el acceso local `user` / `1234`,
definido en `usuarios/frontend_auth.py`, con una sesión en cookie firmada.

**UI-03 (Directorio de clientes) está implementada** con búsqueda por nombre o
identificación, filtros, paginación y cambio de estado con confirmación. Incluye
estados de carga, directorio vacío y búsqueda sin resultados.

**UI-04 (Crear cliente) está implementada** en `/clientes/nuevo/`: RNC o cédula,
campos obligatorios, datos de contacto opcionales y detección de duplicados incluso
para clientes inactivos. El alta se guarda en memoria y aparece en el directorio.
Se comprueba el formato de la identificación, sin consultas ni certificación DGII.

**UI-05 (Detalle de cliente)** muestra la información del contribuyente, sus
facturas recientes y las acciones de inactivar/reactivar con confirmación.

**UI-06 (Editar cliente)** permite actualizar datos, detectar cambios pendientes
y validar duplicados. Al guardar vuelve al detalle del cliente.

**UI-07 (Tipo de comprobante)** permite seleccionar E31 o E32 y crea un borrador
con UUID en memoria. Admite un cliente preseleccionado desde su detalle.

**UI-08 (Selección de cliente)** incluye búsqueda, paginación, tarjetas de
receptores, resumen del seleccionado y restricciones según tipo y estado.
Permite registrar un cliente mediante un modal dentro del flujo.

**UI-09 (Datos generales)** recoge fecha de emisión, tipo de ingreso, condiciones
de pago, vencimiento para crédito y forma de pago. Guarda estos datos en el
borrador antes de avanzar al paso de ítems.

**UI-10 (Bienes y servicios)** permite agregar, editar y quitar conceptos del
borrador, con cantidad, unidad, precio y descuento por línea. La vista previa se
actualiza al editar y distingue los cambios sin guardar. Los cálculos usan
`Decimal` en el servidor: importe redondeado a centavos, descuento antes de
impuestos e ITBIS fijo del 18% para este paso. Incluye validación, confirmación
de eliminación y control de versiones para evitar sobrescrituras entre pestañas.
Las líneas se conservan al navegar y recargar mientras siga vivo el proceso.

**UI-11 (Totales y condiciones)** muestra el subtotal bruto, descuentos, base
imponible, ITBIS y total, junto a las condiciones comerciales del borrador.
Incluye desglose por concepto, ventana de detalle y guardado en memoria con fecha.
Si las líneas o condiciones cambian después de guardar el resumen, se bloquea
el avance hasta recalcular. Los POST vuelven a validar y calcular en el servidor;
no aceptan importes enviados por el navegador y detectan cambios entre pestañas.

**UI-12 a UI-19 siguen pendientes:** revisión, emisión,
resultados, documentos, historial y logs. Conservan sus direcciones reservadas
y usan una plantilla temporal. Continuar desde UI-11 abre la ruta reservada de
revisión; todavía no emite una factura ni asigna un e-NCF.

Las vistas pendientes responden con HTTP 501 y muestran «Sección en preparación».
Las rutas privadas requieren una sesión; las acciones reservadas no modifican
registros. Los modelos y las migraciones existentes se conservan.

El mapa completo y las convenciones para desarrollar cada pantalla están en
[docs/estructura-ui.md](docs/estructura-ui.md). Ese documento conserva algunas
descripciones de etapas anteriores; para el alcance actual, usar este README
y las rutas implementadas en cada módulo.

Las referencias visuales a padrón, DGII, secuencia e-NCF o timbrado no acreditan
consultas ni emisiones reales desde estas pantallas. La integración definitiva
y la verificación de reglas fiscales corresponden a la etapa de backend.

## Desarrollo local (PowerShell)

Requiere Python 3.12 o superior. Esta base se verificó con Django 6.0.8.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py runserver
```

Abre [Inicio de sesión](http://127.0.0.1:8000/acceso/iniciar-sesion/) con el
usuario **user** y la contraseña **1234**.
Este acceso está definido en código y no necesita migraciones ni crear usuarios
en SQLite. Está habilitado con `DEBUG=True` y `FRONTEND_AUTH_ENABLED=True`;
al desactivar este modo se vuelve a la autenticación habitual de Django.
Al iniciar sesión verás `/inicio/` con el resumen y las facturas recientes.
El usuario local tiene rol Emisor y no tiene permisos de administración.

## Datos de interfaz

`frontend_data/entities.py` define clientes, facturas, resúmenes y borradores;
`fixtures.py` contiene los registros iniciales. `repository.py` ofrece la misma
fuente para Inicio, Clientes y el asistente de facturación.
Los 128 comprobantes, 119 aprobados,
9 rechazados y 42 clientes activos se calculan a partir de los registros, sin
mantener contadores independientes en el HTML.

El conjunto inicial contiene 44 clientes: 42 activos y 2 inactivos. Altas,
ediciones, cambios de estado y borradores se guardan exclusivamente en memoria.
Los cambios se pierden al reiniciar el proceso, incluida la recarga por cambios
de código, y no se sincronizan entre procesos. Un enlace a un borrador anterior
puede dejar de existir después de reiniciar. No se modifica SQLite.

«Nueva factura» abre la selección de tipo. Al continuar se crea el borrador;
la selección del cliente y los datos generales actualizan ese mismo registro.
«Crear factura» desde un cliente conserva su identificador al entrar al asistente.

```text
/clientes/<pk>/                          UI-05 — Detalle
/clientes/<pk>/editar/                   UI-06 — Edición
/facturas/nueva/tipo/                    UI-07 — Tipo
/facturas/borradores/<uuid>/cliente/      UI-08 — Cliente
/facturas/borradores/<uuid>/datos/        UI-09 — Datos generales
/facturas/borradores/<uuid>/items/        UI-10 — Bienes y servicios
/facturas/borradores/<uuid>/totales/      UI-11 — Totales y condiciones
/facturas/borradores/<uuid>/revision/     UI-12 — Pendiente
```

Esta etapa trabaja con datos locales en código. No se deben ejecutar cargas,
migraciones ni modificaciones de modelos para implementar las siguientes
pantallas. Los siguientes módulos usan `SimpleTestCase` y repositorios en
memoria, sin crear una base de datos de pruebas:

```powershell
.\.venv\Scripts\python.exe manage.py test frontend_data.tests core.tests_dashboard
.\.venv\Scripts\python.exe manage.py test usuarios.tests_frontend_auth
.\.venv\Scripts\python.exe manage.py test clientes.tests clientes.tests_crear clientes.tests_detalle clientes.tests_editar
.\.venv\Scripts\python.exe manage.py test comprobantes.tests_tipo comprobantes.tests_cliente comprobantes.tests_datos
.\.venv\Scripts\python.exe manage.py test comprobantes.tests_items
.\.venv\Scripts\python.exe manage.py test comprobantes.tests_totales
```

## Criterios para las próximas pantallas

- Reutilizar el layout privado, la navegación, los iconos SVG y los componentes
  de `static/css/global.css`.
- Mantener azul marino, fondos claros, tarjetas blancas, bordes suaves,
  tipografía compacta y acciones principales destacadas. Continuar con tarjetas
  de contexto, secciones numeradas y adaptación a móvil.
- Declarar ajustes específicos en `static/css/pages/`, dentro de la capa
  `components`, y el comportamiento de cada pantalla en `static/js/pages/`.
- Mantener textos propios de una aplicación real, sin etiquetas académicas ni
  controles de prueba copiados de las referencias visuales.
- Validar en el servidor aunque haya máscaras en el navegador. Conservar el
  formato automático de RNC, cédula y teléfono, el escape HTML y los caracteres
  legítimos de los textos, como apóstrofes.
- Resolver búsqueda, filtros y paginación en el servidor. Al conectar la BD,
  trasladarlos a consultas SQL eficientes con índices y restricciones de
  unicidad; revisar planes de ejecución y evitar consultas repetidas por registro.
  No descargar todo el directorio para filtrarlo en el navegador.
- Usar el ORM o consultas parametrizadas al incorporar SQL. Eliminar comillas
  o sanitizar textos no sustituye esa protección.

## Comprobaciones

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py findstatic css/global.css js/app.js
```

El comando general `manage.py test` también descubre pruebas de otros módulos
que pueden necesitar una base de datos de pruebas. Para esta etapa, utilizar
los módulos indicados arriba.

`static/` contiene los archivos fuente. `staticfiles/` se reserva para la salida
de `collectstatic`. La configuración actual conserva el entorno local del
proyecto; el despliegue se configurará por separado.

# Guía de personalización de ckanext-gobar-theme

Todo lo personalizable del theme se configura por **variables de entorno o
claves del `ckan.ini`**, nunca editando templates ni código para un nodo
puntual. Así se cumple el invariante de "redistribuible con mínima config" de
Portal Andino V2: para adaptar un portal alcanza con tocar el `.env`.

Las variables de entorno siguen la convención de `envvars`, el plugin que CKAN
ya usa en este stack:

- una clave `ckanext.gobar_theme.mi_clave` se configura como
  `CKANEXT__GOBAR_THEME__MI_CLAVE=valor`;
- una clave nativa de CKAN como `ckan.site_logo` se configura como
  `CKAN__SITE_LOGO=valor`.

Los cambios del `.env` se aplican al **recrear** el contenedor
(`docker compose up -d ckan`); un restart no alcanza.

> ⚠️ En el `.env`, un valor que empieza con `#` (los colores) va sin comillas y
> sin comentario en la misma línea. Además, el archivo tiene que terminar con un
> salto de línea: si no, la próxima línea que se agregue al final queda pegada a
> la anterior.

---

## 1. El perfil (`ckanext.gobar_theme.profile`) — obligatorio

Define la identidad del portal. **No tiene valor por defecto**: si falta o no es
uno de estos dos, CKAN no arranca y muestra el error en el log. No distingue
mayúsculas (`APN` = `apn`).

| Perfil | Para quién | Identidad |
|---|---|---|
| `datosgobar` | El portal nacional, datos.gob.ar | Dirección de Datos Abiertos: navy, índigo y violeta, Montserrat, logo de datos.gob.ar, sección Recursos, contacto y "Reportar un problema" hacia el formulario de Datos Abiertos |
| `apn` | Portales de organismos de la Administración Pública Nacional | Poncho (argentina.gob.ar): navy `#232D4F`, enlace `#0767A7` y celeste `#039BE5`, Lora en títulos. Sin índigo ni violeta en ningún elemento. Logo, textos, colores y contacto del organismo |

```
CKANEXT__GOBAR_THEME__PROFILE=apn
```

**Migración.** Hasta octubre de 2026 el perfil tenía default `nacional` y
admitía `base`/`subnacional`. Ahora:

- `nacional` pasa a llamarse **`datosgobar`**;
- `base` y `subnacional` ya no existen.

Antes de desplegar esta versión hay que configurar el perfil en el `.env` de
cada portal, **incluido el de producción**.

### Qué cambia según el perfil

| Elemento | `datosgobar` | `apn` (sin configurar nada más) |
|---|---|---|
| Logo del header | datos.gob.ar | Título del portal como texto (o `ckan.site_logo`) |
| Logo del footer | datos.gob.ar | Ninguno (o `ckan.site_logo`); el título no se repite como texto |
| Texto del footer | "Portal de datos abiertos de la República Argentina…" | Ninguno (o `ckan.site_description`) |
| Home: título y bajada | "Datos Abiertos Argentina" y su texto | `ckan.site_title` + `subtitle` opcional |
| Sección y menú Recursos | Sí | No (`show_recursos`) |
| Columna "Recursos" del footer (Georef, Series…) | Sí | No |
| Sección y menú Series (`series_explorer`) | Si el plugin está cargado | Nunca; además conviene sacar `series_explorer` de `CKAN__PLUGINS` |
| Dirección, teléfono y correo en el footer | No (o `contact_*`) | No (o `contact_*`) |
| Link institucional del footer | Dirección de Datos Abiertos | Ninguno (o `institutional_name`/`_url`) |
| Logo de la Secretaría en el footer | Sí | No (o `footer_logo_path`) |
| "Contacto" en el footer | Formulario de Datos Abiertos | No se muestra (o `contact_url`) |
| Aviso "Reportar un problema" | Formulario de Datos Abiertos | No se muestra (o `report_url`) |
| Página "Acerca" | Texto de la Dirección de Datos Abiertos | Texto genérico de Portal Andino (o `ckan.site_about`) |
| Colores y tipografía | Preset Datos Abiertos | Preset Poncho (o `color_*`) |

---

## 2. Identidad del portal (claves nativas de CKAN)

El theme usa la configuración nativa de CKAN en vez de inventar claves propias.

| Variable | Efecto | Default |
|---|---|---|
| `CKAN__SITE_TITLE` | Título del portal: `<title>`, h1 de la home en `apn` (la última palabra va en el color de acento) y texto del logo cuando no hay imagen | — |
| `CKAN__SITE_LOGO` | Logo del header y del footer. Puede ser una URL absoluta (`https://…`) o una ruta servida por el portal (`/images/mi-logo.png`, dentro de `public/` del theme). Va sobre el color de marca, así que conviene una versión **blanca o clara** | datosgobar: logo de datos.gob.ar; apn: título como texto |
| `CKAN__SITE_DESCRIPTION` | Texto de marca del footer, debajo del logo | datosgobar: texto de datos.gob.ar; apn: vacío |
| `CKAN__SITE_ABOUT` | Texto de la página "Acerca" en `apn` (markdown, **en una sola línea**: un salto de línea `\n` dentro del valor rompe el `ckan.ini` que genera el entrypoint). El bloque "Sobre CKAN" se agrega abajo igual | apn: texto genérico de Portal Andino |
| `CKAN__FAVICON` | Favicon: URL absoluta o ruta servida por el portal | El de argentina.gob.ar |
| `CKANEXT__GOBAR_THEME__SUBTITLE` | Frase debajo del título de la home (`apn`) | vacío (no se muestra) |
| `CKANEXT__GOBAR_THEME__HERO_BACKGROUND_IMAGE` | Imagen de fondo del hero de la home, con un overlay claro automático para que el texto se lea | vacío |

```
CKAN__SITE_TITLE=Datos Agro
CKAN__SITE_LOGO=https://www.magyp.gob.ar/logos/datos-blanco.svg
CKAN__SITE_DESCRIPTION=Portal de datos abiertos del Ministerio de Agricultura, Ganadería y Pesca.
CKANEXT__GOBAR_THEME__SUBTITLE=En este portal podrás obtener datos numéricos y estadísticos del sector agropecuario y sus temas relacionados.
```

---

## 3. Colores

### El modelo: 4 colores de entrada

El perfil define cuatro colores. Todos los demás (tonos claros de fondo,
bordes, foco, hovers, títulos) **se calculan a partir de ellos**. Para que un
organismo tenga su paleta en todos los elementos alcanza con configurar estos
cuatro:

| Variable | Token CSS | Dónde se ve | `datosgobar` | `apn` |
|---|---|---|---|---|
| `CKANEXT__GOBAR_THEME__COLOR_BRAND` | `--gobar-brand` | Header, botón sólido ("Ir al recurso", "Buscar"), paginación activa, ícono genérico de organismo | `#393793` | `#232D4F` |
| `CKANEXT__GOBAR_THEME__COLOR_BRAND_DARK` | `--gobar-brand-dark` | Footer, franja "Para desarrolladores", hover del botón sólido | `#2D2B73` | `#1A2039` |
| `CKANEXT__GOBAR_THEME__COLOR_INTERACTIVE` | `--gobar-interactive` | Links, pestaña activa, "Explorar", "URL ▾", facetas, hovers, foco | `#393793` | `#0767A7` |
| `CKANEXT__GOBAR_THEME__COLOR_ACCENT` | `--gobar-accent` | Detalles: filete del footer, bandera del aviso, rótulos chicos | `#B369ED` | `#039BE5` |

- Si se configura `COLOR_BRAND` y no `COLOR_INTERACTIVE`, los links y botones
  **siguen a la marca**. Un organismo que pone solo su color institucional no
  queda con links del preset.
- `COLOR_PRIMARY` y `COLOR_PRIMARY_DARK` (nombres anteriores) siguen funcionando
  como alias de `COLOR_BRAND` y `COLOR_BRAND_DARK`.
- Formato: hex `#rgb` o `#rrggbb`. Un valor inválido se ignora y se avisa en el
  log.
- Los colores de estado (verde, amarillo, rojo) y los grises no cambian: son
  los de Poncho en los dos perfiles.

```
# Ejemplo: organismo con verde institucional
CKANEXT__GOBAR_THEME__COLOR_BRAND=#00703C
CKANEXT__GOBAR_THEME__COLOR_BRAND_DARK=#004D29
CKANEXT__GOBAR_THEME__COLOR_ACCENT=#F2A900
```

### Contraste (accesibilidad)

Al arrancar, el theme calcula el contraste WCAG de los colores configurados y
**avisa en el log** (no corta el arranque) si no llegan a AA 4.5:1:

- `brand` y `brand_dark` contra el blanco, porque el texto del header, del
  footer y de los botones es blanco;
- `interactive` contra el blanco, porque los links van sobre fondo blanco.

```
WARNING [ckanext.gobar_theme.plugin] gobar_theme: --gobar-brand #039BE5 tiene contraste 3.08:1 con el blanco (texto blanco sobre el header y los botones); WCAG AA pide 4.5:1.
```

Regla práctica: la marca tiene que ser un color **oscuro**. El celeste
`#039BE5` sirve como acento, no como marca ni como color de links.

### Referencia: paleta Poncho

Fuente: `argob/poncho` v2, `_poncho-colors.scss`.

| Rol | Hex |
|---|---|
| Primario (`arg-azul`) | `#232D4F` |
| Secundario | `#3E5A7E` |
| Enlace (normal / oscuro / claro) | `#0767A7` / `#084E87` / `#0581C6` |
| Celeste (acento) | `#039BE5` |
| Celeste Argentina | `#68C3EF` |
| Éxito / Advertencia / Peligro / Info | `#2E7D33` / `#E7BA61` / `#C62828` / `#5A7290` |
| Grises (texto, intermedio, borde, fondo) | `#141414`, `#555555`, `#DEE2E6`, `#F2F2F2` |

### Cómo funciona (para desarrolladores)

Está en `assets/css/gobar-base.css`, bloque "VARIABLES":

- Los presets son `body.theme-profile-datosgobar` y `body.theme-profile-apn`.
- Los tonos derivados se calculan con `color-mix()` en la regla `body` (no en
  `:root`), para que vean los overrides del `.env`, que van como `style` inline
  en el `<body>` (`helpers.gobar_color_overrides_style`).
- El preset `datosgobar` fija sus derivados con los valores exactos de la
  identidad Datos Abiertos.
- **Regla:** ningún color de marca se escribe fijo en el CSS. Siempre se usa un
  token (`--gobar-brand`, `--gobar-interactive`, `--gobar-surface-tint`,
  `--gobar-border-soft`, `--gobar-focus-ring`, `--gobar-heading`…). Así el
  perfil `apn` no hereda índigo ni violeta.
- Las imágenes con color (el edificio genérico de organismo, también el
  placeholder de CKAN) se pintan con `mask-image` y el color de marca.

---

## 4. Contacto y "Reportar un problema"

| Variable | Efecto | Default |
|---|---|---|
| `CKANEXT__GOBAR_THEME__CONTACT_URL` | Link "Contacto" del footer. Puede ser una URL o un `mailto:` | datosgobar: formulario de Datos Abiertos; apn: no se muestra |
| `CKANEXT__GOBAR_THEME__REPORT_URL` | Formulario del aviso "Reportar un problema" en las páginas de dataset y recurso. Tiene que aceptar el parámetro `?referencia=<url>`, que el theme agrega con la URL del dataset o recurso | datosgobar: formulario de Datos Abiertos; apn: el aviso no se muestra |

| `CKANEXT__GOBAR_THEME__CONTACT_ADDRESS` | Dirección postal, en el footer debajo del texto de marca | vacío (no se muestra) |
| `CKANEXT__GOBAR_THEME__CONTACT_PHONE` | Teléfono, como link `tel:` | vacío (no se muestra) |
| `CKANEXT__GOBAR_THEME__CONTACT_EMAIL` | Correo, como link `mailto:` | vacío (no se muestra) |

```
CKANEXT__GOBAR_THEME__CONTACT_URL=mailto:datospublicos@magyp.gob.ar
CKANEXT__GOBAR_THEME__REPORT_URL=https://www.magyp.gob.ar/contacto
CKANEXT__GOBAR_THEME__CONTACT_ADDRESS=Av. Ejemplo 1234, CABA
CKANEXT__GOBAR_THEME__CONTACT_PHONE=+54 11 0000-0000
CKANEXT__GOBAR_THEME__CONTACT_EMAIL=datospublicos@magyp.gob.ar
```

---

## 5. Footer: sección Institucional y logo inferior

| Variable | Default | Efecto |
|---|---|---|
| `institutional_name` | vacío (en datosgobar, "Dirección de Datos Abiertos") | Texto del link institucional |
| `institutional_url` | vacío (en datosgobar, argentina.gob.ar/datos-abiertos) | URL de ese link |
| `show_secretariat_logo` | `auto` (`true`\|`false`\|`auto`) | Logo de la esquina inferior derecha. En `auto` se oculta en `apn`, salvo que se configure `footer_logo_path` |
| `footer_logo_path` | vacío (logo de la Secretaría de Innovación) | Escudo o logo propio del organismo: URL absoluta o ruta dentro de `public/` del theme. Va sobre el fondo oscuro del footer |
| `secretariat_logo_alt` | `Secretaría de Innovación, Ciencia y Tecnología` | Texto alternativo de ese logo |

```
CKANEXT__GOBAR_THEME__INSTITUTIONAL_NAME=Ministerio de Agricultura, Ganadería y Pesca
CKANEXT__GOBAR_THEME__INSTITUTIONAL_URL=https://www.magyp.gob.ar
CKANEXT__GOBAR_THEME__FOOTER_LOGO_PATH=https://www.magyp.gob.ar/logos/ministerio-blanco.png
CKANEXT__GOBAR_THEME__SECRETARIAT_LOGO_ALT=Ministerio de Agricultura, Ganadería y Pesca
```

---

## 6. Otras opciones

| Variable | Default | Efecto |
|---|---|---|
| `organizations_label` | `Organismos` | Nombre de "Organismos" en el menú, el footer, la home y la faceta (por ejemplo "Dependencias") |
| `show_recursos` | `auto` | Sección /recursos (productos de la Dirección de Datos Abiertos). `auto` la muestra solo en datosgobar; `true`/`false` fuerzan |
| `featured_datasets_limit` | `6` | Cantidad de datasets en "Actualizados recientemente" de la home (ordenados por última modificación) |

---

## 7. `.env` mínimo para un organismo (perfil `apn`)

```
CKANEXT__GOBAR_THEME__PROFILE=apn
CKAN__SITE_TITLE=Datos Agro
CKAN__SITE_LOGO=https://www.magyp.gob.ar/logos/datos-blanco.svg
CKAN__SITE_DESCRIPTION=Portal de datos abiertos del Ministerio de Agricultura, Ganadería y Pesca.
CKAN__SITE_ABOUT=Este portal reúne los datos abiertos del **Ministerio de Agricultura, Ganadería y Pesca**.
CKANEXT__GOBAR_THEME__SUBTITLE=Datos del sector agropecuario y sus temas relacionados.
CKANEXT__GOBAR_THEME__CONTACT_URL=mailto:datospublicos@magyp.gob.ar
CKANEXT__GOBAR_THEME__INSTITUTIONAL_NAME=Ministerio de Agricultura, Ganadería y Pesca
CKANEXT__GOBAR_THEME__INSTITUTIONAL_URL=https://www.magyp.gob.ar
CKANEXT__GOBAR_THEME__CONTACT_ADDRESS=Av. Ejemplo 1234, CABA
CKANEXT__GOBAR_THEME__CONTACT_PHONE=+54 11 0000-0000
CKANEXT__GOBAR_THEME__FOOTER_LOGO_PATH=https://www.magyp.gob.ar/logos/escudo-blanco.png
# Opcional: colores propios (si no, Poncho)
# CKANEXT__GOBAR_THEME__COLOR_BRAND=#00703C
```

---

## 8. Del Andino viejo (`/configurar`) a V2

El theme viejo (`portal-andino-theme`) se configuraba desde un panel
`/configurar` y lo guardaba en un JSON aparte. En V2 todo va por `.env`:

| Panel `/configurar` del Andino viejo | En V2 |
|---|---|
| Título y descripción del portal | `CKAN__SITE_TITLE`, `SUBTITLE`, `CKAN__SITE_DESCRIPTION` |
| Organismo responsable | `INSTITUTIONAL_NAME` / `_URL` |
| Imagen de fondo de la portada | `HERO_BACKGROUND_IMAGE` |
| Logo del encabezado | `CKAN__SITE_LOGO` |
| Logo del pie | `FOOTER_LOGO_PATH` (el logo no es link) |
| Mail de contacto | `CONTACT_URL` (`mailto:`) o `CONTACT_EMAIL`; también `CONTACT_ADDRESS` y `CONTACT_PHONE` |
| Acerca (título y descripción) | `CKAN__SITE_ABOUT` |
| Google Analytics / Tag Manager | `CKAN___GOOGLEANALYTICS__ID` (ckanext-googleanalytics) |
| Licencias | `CKAN___LICENSES_GROUP_URL` (nativo; triple `_` porque la clave no lleva prefijo `ckan.`) |
| Colores | No existían en el panel viejo. En V2: `COLOR_*` |
| Formato de la portada (4 plantillas), temas con/sin íconos | No existe: layout único |
| Redes sociales | **Pendiente**, no existe |
| Acerca con secciones HTML propias | **Pendiente**. Hoy hay un solo texto (`site_about`) |
| Open Graph / Twitter cards | **Pendiente** |
| Metadatos del catálogo (`data.json`) | Los maneja `ckanext-dcat` y scheming, no el theme |

---

## 9. Limitaciones conocidas y pendientes

- **Redes sociales** del organismo en el footer: no hay variables. Agregarlas
  solo si un organismo las pide.
- **Link en el logo del footer** (`footer_logo_path`): la imagen no es link.
- **Imágenes de los temas (superThemes):** los íconos de las categorías de la
  home se guardan en la base de datos de cada grupo (`image_url`) como PNG
  índigo, así que no cambian con el perfil. Un portal `apn` tiene que cargar
  imágenes propias o neutras en cada tema.
- **Plugins por perfil:** un portal `apn` no lleva series (el theme oculta
  la sección aunque el plugin esté cargado) y en general tampoco harvest, pero
  tiene que sacar `series_explorer` (y los harvesters) de `CKAN__PLUGINS` a
  mano en el `.env`; no hay un preset por perfil en el stack.
- `public/vendor/poncho/` está vendorizado y no se usa (el theme toma de
  Poncho solo los valores de color y tipografía).

---

## Cómo agregar una nueva variable personalizable

1. Antes de crear una clave propia, revisar si CKAN ya tiene una nativa
   (`ckan.site_*`).
2. Declararla en `plugin.py` → `declare_config_options`, con un default que
   preserve el comportamiento actual de los dos perfiles.
3. Exponer un helper con nombre propio en `helpers.py` (por ejemplo
   `gobar_mi_cosa()`), con la lógica por perfil adentro, y registrarlo en
   `get_helpers()`.
4. Usarlo desde los templates que correspondan.
5. Agregar un test en `tests/test_helpers.py` y documentarla acá.

# ckanext-gobar-theme

Theme e identidad visual de los portales de datos abiertos de Datos
Argentina, sobre CKAN 2.11. Es la extensión de presentación de
[portal-andino-v2](https://github.com/datosgobar/portal-andino-v2): un mismo
theme sirve para datos.gob.ar y para los nodos que redistribuyen el stack,
personalizable por configuración sin tocar templates ni código.

Funcionalidades:

* Home propia: hero con buscador, categorías, datasets actualizados
  recientemente, organizaciones y franja de la API.
* Header y footer institucionales con navegación fija
  (Datasets, Organismos, Temas, Recursos, Series, Acerca).
* Dos perfiles, **obligatorios** vía `ckanext.gobar_theme.profile`:
  `datosgobar` (portal nacional, identidad Datos Abiertos) y `apn`
  (organismos de la Administración Pública Nacional, Poncho + la identidad
  del organismo: logo, textos, colores y contacto propios).
* Modelo de color de 4 tokens (marca, marca oscura, interactivo, acento)
  personalizable por `.env`, con los tonos derivados calculados y aviso de
  contraste WCAG al arrancar.
* Página `Acerca` propia (override de `/about` de CKAN) con texto
  distinto según el perfil (`ckan.site_about` en `apn`).
* Sección `/recursos` opcional y nombre configurable para la sección de
  organizaciones (por ejemplo "Organismos").
* Faceta de Provincia (a partir de la cobertura espacial de los datasets) y
  overrides de traducción sobre CKAN core (por ejemplo "Grupos" → "Temas").

La página `/series` no vive acá: la registra
[ckanext-series-explorer](https://github.com/datosgobar/ckanext-series-explorer).

## Instalación

```
pip install -e 'git+https://github.com/datosgobar/ckanext-gobar-theme.git@main#egg=ckanext-gobar_theme'
pip install -r requirements.txt
```

Agregá `gobar_theme` a `ckan.plugins` en tu archivo de configuración y
reiniciá CKAN:

```
ckan.plugins = gobar_theme
```

## Configuración

Ver [`docs/personalizacion.md`](docs/personalizacion.md): perfil
(obligatorio: `datosgobar` | `apn`), logo y textos del portal, colores,
contacto y "Reportar un problema", sección Institucional y logo del footer,
sección /recursos — todo configurable por `.env`/`ckan.ini`, sin tocar
templates ni código. Incluye un `.env` mínimo para organismos y la
equivalencia con el panel `/configurar` del Andino viejo.

```
ckanext.gobar_theme.profile = datosgobar
```

## Tests

Dentro de un entorno con CKAN instalado (por ejemplo el contenedor dev de
portal-andino-v2):

```
pytest --ckan-ini=/srv/app/src/ckan/test-core.ini ckanext/gobar_theme/tests
```

## Licencia

[AGPL](https://www.gnu.org/licenses/agpl-3.0.en.html)

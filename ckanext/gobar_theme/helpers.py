# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any
from urllib.parse import quote

import ckan.plugins.toolkit as toolkit
import ckan.model as model

log = logging.getLogger(__name__)


# ── Gobar theme helpers ──

def gobar_dataset_count() -> int:
    try:
        result = toolkit.get_action("package_search")(
            {"ignore_auth": True}, {"rows": 0, "include_private": False}
        )
        return result.get("count", 0)
    except Exception:
        return 0


def gobar_organization_count() -> int:
    try:
        return len(toolkit.get_action("organization_list")(
            {"ignore_auth": True}, {}
        ))
    except Exception:
        return 0


def gobar_group_count() -> int:
    try:
        return len(toolkit.get_action("group_list")(
            {"ignore_auth": True}, {}
        ))
    except Exception:
        return 0


def gobar_groups_with_details() -> list[dict[str, Any]]:
    try:
        return toolkit.get_action("group_list")(
            {"ignore_auth": True},
            {"all_fields": True, "include_extras": True, "limit": 20},
        )
    except Exception:
        return []


def gobar_organizations_with_details(limit: int = 20) -> list[dict[str, Any]]:
    """Retorna organizaciones con detalle para el carrusel."""
    try:
        return toolkit.get_action("organization_list")(
            {"ignore_auth": True},
            {"all_fields": True, "include_extras": True, "limit": limit},
        )
    except Exception:
        return []


def gobar_org_details_by_name() -> dict[str, dict[str, Any]]:
    """Mapa nombre → org (logo, package_count) para el árbol de /organization.

    ponytail: all_fields está capado por
    ckan.group_and_organization_list_all_fields_max (default core 25, el
    theme lo sube a 200 en plugin.py update_config); con más organismos que
    eso, los excedentes se muestran sin logo/count — subir ese valor en la
    config si hiciera falta más.
    """
    try:
        orgs = toolkit.get_action("organization_list")(
            {"ignore_auth": True}, {"all_fields": True}
        )
        return {o["name"]: o for o in orgs}
    except Exception:
        return {}


def gobar_org_tree_with_counts(top_nodes: list[dict]) -> list[dict]:
    """Anota cada nodo de ``h.group_tree()`` con ``subtree_package_count``:
    el ``package_count`` propio + el de todos sus descendientes (colapsado).

    El count individual de cada organismo se resuelve por nombre con
    ``gobar_org_details_by_name()`` (una sola llamada; no llamar por nodo).
    Muta los dicts de ``group_tree`` in-place y los devuelve, así el snippet
    del árbol lee ``node.subtree_package_count`` directamente.
    """
    details = gobar_org_details_by_name()

    def annotate(node: dict) -> int:
        own = (details.get(node.get("name")) or {}).get("package_count", 0) or 0
        total = own + sum(annotate(c) for c in node.get("children") or [])
        node["subtree_package_count"] = total
        return total

    for node in top_nodes:
        annotate(node)
    return top_nodes


def gobar_dedupe_top_nodes(top_nodes: list[dict]) -> list[dict]:
    """Filtra del listado top-level cualquier organismo que también aparezca
    anidado como hijo de otro nodo del árbol.

    # ponytail: parche de RENDER. El duplicado real (un organismo que sale
    # anidado bajo un ministerio Y a la vez suelto en el top-level del listado
    # paginado de /organization) nace de las relaciones ``member`` en los datos
    # y de cómo ckanext-hierarchy arma el árbol — ambos externos a este repo
    # (I1, no tocables). Para resolverlo de raíz hay que auditar las relaciones
    # ``member`` de esos organismos; acá solo evitamos el duplicado visual.
    # Solo para el listado top-level (organization_list.html): el render de
    # hijos dentro del árbol expandido no pasa por acá.

    ``top_nodes`` puede venir recortado a un subconjunto de organismos (el
    snippet lo usan ``/dashboard/organizations`` y el perfil de usuario, que
    pasan solo los del usuario), así que un hijo cuyo padre quedó fuera de esa
    lista se ve "top-level" aunque no lo sea. Por eso el set de "es hijo de
    algo" se arma contra el árbol GLOBAL, no contra ``top_nodes``.

    ``/organization`` NO pasa por acá: pagina por raíces del árbol global con
    ``gobar_org_root_page()``, donde por construcción no hay duplicados.
    """
    full_tree = toolkit.h.group_tree(type_="organization")
    child_names: set = set()

    def collect(nodes: list[dict]) -> None:
        for node in nodes:
            children = node.get("children") or []
            for child in children:
                child_names.add(child.get("name"))
            collect(children)

    collect(full_tree)
    return [n for n in top_nodes if n.get("name") not in child_names]


def gobar_org_root_page(q: str | None = None):
    """Página del árbol de organismos, paginada por RAÍCES.

    CKAN pagina la lista PLANA de organismos, pero ``/organization`` renderiza
    un árbol donde solo las raíces son filas de primer nivel: los hijos se ven
    anidados bajo su padre. Con la paginación de core, los hijos ocupaban lugar
    en la página aunque no se mostraran ahí, y las páginas 2+ quedaban con uno o
    dos ítems. Acá se pagina la lista de raíces, que es lo que efectivamente se
    lista.

    Devuelve un ``Page`` de core (mismo pager que el resto del sitio) con las
    raíces de la página en ``.items``, ya anotadas con ``subtree_package_count``.
    """
    from ckan.lib.helpers import Page

    top_nodes = gobar_org_tree_with_counts(
        toolkit.h.group_tree(type_="organization")
    )
    if q:
        # Marca las coincidencias sobre el árbol completo (no sobre la página
        # de core, que solo traía las primeras N).
        matches = toolkit.get_action("organization_list")(
            {"ignore_auth": True}, {"q": q}
        )
        toolkit.h.group_tree_highlight([{"name": n} for n in matches], top_nodes)

    return Page(
        collection=top_nodes,
        page=toolkit.h.get_page_number(toolkit.request.args),
        url=toolkit.h.pager_url,
        items_per_page=toolkit.config.get("ckan.datasets_per_page"),
    )


# ── Contenido de /recursos, perfil y personalización ──

def gobar_productos_list() -> list[dict[str, str]]:
    """Retorna la lista de productos de la Dirección de Datos Abiertos."""
    return [
        {
            "title": "datos.gob.ar",
            "description": "Portal Nacional de Datos Abiertos de la República Argentina.",
            "logo": "images/Logo_datos-gob-ar_Color.png",
            "url": "https://datos.gob.ar",
        },
        {
            "title": "Portal Andino",
            "description": "Plataforma de publicación de datos abiertos para organismos del Estado.",
            "logo": "images/Logo_Andino_Color.png",
            "url": "https://www.argentina.gob.ar/portal-andino",
        },
        {
            "title": "Georef",
            "description": "Servicio de normalización y codificación de datos geográficos de Argentina.",
            "logo": "images/Logo_Georef_Color.png",
            "url": "https://www.argentina.gob.ar/georef",
        },
        {
            "title": "Paquete de Apertura de Datos",
            "description": "Herramientas y guías para publicar datos abiertos de calidad.",
            "logo": "images/Logo_Paqueta-Apertura-Datos_Color.png",
            "url": "https://www.argentina.gob.ar/paquete-de-apertura",
        },
        {
            "title": "Series de Tiempo",
            "description": "API para acceder y explorar series de tiempo de datos económicos y estadísticos.",
            "logo": "images/Logo_Series_de_Tiempo.png",
            "url": "https://www.argentina.gob.ar/datos-abiertos/api-series-de-tiempo",
        },
    ]


def gobar_comunidad_list() -> list[dict[str, str]]:
    """Retorna la sección "Documentación y otros" de la página Recursos."""
    return [
        {
            "title": "GitHub datosgobar",
            "description": "Repositorios públicos con código, estándares y documentación técnica.",
            "icon": "fa-brands fa-github",
            "url": "https://github.com/datosgobar",
        },
        {
            "title": "Perfil de Metadatos",
            "description": "Especificación del perfil de metadatos para catálogos de datos abiertos de Argentina.",
            "icon": "fa fa-book",
            "url": "https://datosgobar.github.io/paquete-apertura-datos/perfil-metadatos/",
        },
        {
            "title": "Vocabularios & Codelists",
            "description": "Vocabularios controlados y listas de códigos de referencia para publicar datos.",
            "icon": "fa fa-tags",
            "url": "https://infra.datos.gob.ar/vocabulario/",
        },
        {
            "title": "Contacto",
            "description": "Escribinos con tus consultas, sugerencias o para sumarte a la comunidad.",
            "icon": "fa fa-envelope",
            "url": "https://www.argentina.gob.ar/datos-abiertos/contacto",
        },
    ]


def gobar_get_config(key: str, default: str = "") -> str:
    return toolkit.config.get(key, default)


# Perfiles válidos de ckanext.gobar_theme.profile (obligatorio, sin default:
# plugin.configure() corta el arranque si falta o no es uno de estos).
#   datosgobar - portal nacional datos.gob.ar (identidad Datos Abiertos)
#   apn        - portal de un organismo de la Administración Pública
#                Nacional (Poncho + identidad del organismo)
PROFILES = ("datosgobar", "apn")


def gobar_validate_profile(value: Any) -> str:
    """Normaliza el perfil (sin espacios, minúsculas: "APN" == "apn") y
    falla con un mensaje explícito si no es uno de PROFILES."""
    profile = str(value or "").strip().lower()
    if profile not in PROFILES:
        raise ValueError(
            "ckanext.gobar_theme.profile es obligatorio y debe ser "
            f"{' o '.join(PROFILES)} (recibido: {value!r}). Configurarlo en el "
            ".env con CKANEXT__GOBAR_THEME__PROFILE=datosgobar|apn."
        )
    return profile


def gobar_theme_profile() -> str:
    return str(
        toolkit.config.get("ckanext.gobar_theme.profile", "") or ""
    ).strip().lower()


def gobar_is_apn() -> bool:
    """Único lugar que compara contra el literal "apn": todo lo demás
    (templates y helpers) llama a esta función en vez de repetir la
    comparación de string."""
    return gobar_theme_profile() == "apn"


def gobar_is_datosgobar() -> bool:
    return gobar_theme_profile() == "datosgobar"


def gobar_show_recursos() -> bool:
    raw = str(
        toolkit.config.get("ckanext.gobar_theme.show_recursos", "auto")
    ).strip().lower()
    if raw == "auto":
        return not gobar_is_apn()
    return raw in ("true", "1", "yes", "on")


def gobar_institutional_name() -> str:
    configured = toolkit.config.get("ckanext.gobar_theme.institutional_name", "")
    if configured:
        return configured
    return "" if gobar_is_apn() else "Dirección de Datos Abiertos"


def gobar_institutional_url() -> str:
    configured = toolkit.config.get("ckanext.gobar_theme.institutional_url", "")
    if configured:
        return configured
    return "" if gobar_is_apn() else "https://www.argentina.gob.ar/datos-abiertos"


def gobar_organizations_label() -> str:
    return toolkit.config.get(
        "ckanext.gobar_theme.organizations_label", "Organismos"
    )


def gobar_show_secretariat_logo() -> bool:
    raw = str(
        toolkit.config.get("ckanext.gobar_theme.show_secretariat_logo", "auto")
    ).strip().lower()
    if raw == "auto":
        # Un organismo apn no tiene por qué llevar el logo de la Secretaría
        # de Innovación del portal nacional. Si configura su propio logo
        # (footer_logo_path), mostrarlo igual — el "auto" solo esconde
        # el DEFAULT ajeno, no un logo propio ya configurado.
        return (not gobar_is_apn()) or bool(
            toolkit.config.get("ckanext.gobar_theme.footer_logo_path", "")
        )
    return raw in ("true", "1", "yes", "on")


def gobar_footer_logo_path() -> str:
    return toolkit.config.get("ckanext.gobar_theme.footer_logo_path", "")


def gobar_secretariat_logo_alt() -> str:
    return toolkit.config.get(
        "ckanext.gobar_theme.secretariat_logo_alt",
        "Secretaría de Innovación, Ciencia y Tecnología",
    )


_HEX_COLOR = re.compile(r"^#(?:[0-9a-fA-F]{3}){1,2}$")

# Token CSS → (clave nueva, alias viejo). Ver el modelo de color en
# assets/css/gobar-base.css ("VARIABLES").
COLOR_TOKENS = {
    "--gobar-brand": ("color_brand", "color_primary"),
    "--gobar-brand-dark": ("color_brand_dark", "color_primary_dark"),
    "--gobar-interactive": ("color_interactive", None),
    "--gobar-accent": ("color_accent", None),
}


def gobar_color_config() -> dict[str, str]:
    """Colores configurados por .ini/.env, ya validados.

    Devuelve solo los válidos (#rgb o #rrggbb); los inválidos se ignoran (y
    plugin.configure() los avisa en el log). Si se configura la marca pero
    no el color interactivo, los links/botones siguen a la marca: un
    organismo que pone solo su color institucional no queda con links del
    preset."""
    def get(key: str | None) -> str:
        if not key:
            return ""
        return str(
            toolkit.config.get(f"ckanext.gobar_theme.{key}", "") or ""
        ).strip()

    colors = {}
    for token, (key, alias) in COLOR_TOKENS.items():
        value = get(key) or get(alias)
        if value and _HEX_COLOR.match(value):
            colors[token] = value
    if "--gobar-interactive" not in colors and "--gobar-brand" in colors:
        colors["--gobar-interactive"] = colors["--gobar-brand"]
    return colors


def gobar_color_overrides_style() -> str:
    """Atributo style="..." del <body> (base.html) con los colores
    configurados. Va inline en el body porque le gana en especificidad al
    preset body.theme-profile-* sin !important; los tonos derivados
    (gobar-base.css, regla "body") se recalculan solos a partir de estos."""
    return " ".join(
        f"{token}: {value};" for token, value in gobar_color_config().items()
    )


def _luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    channels = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = channels
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def gobar_contrast_ratio(color_a: str, color_b: str) -> float:
    """Contraste WCAG 2.x entre dos colores hex (1 a 21)."""
    la, lb = sorted((_luminance(color_a), _luminance(color_b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def gobar_check_colors() -> list[str]:
    """Advertencias sobre los colores configurados: formato inválido y
    contraste insuficiente (WCAG AA 4.5:1) contra el blanco, que es el color
    del texto sobre la marca (header, footer, botones) y el fondo de los
    links. No corta el arranque: el organismo decide."""
    warnings = []
    for token, (key, alias) in COLOR_TOKENS.items():
        for k in filter(None, (key, alias)):
            raw = str(toolkit.config.get(f"ckanext.gobar_theme.{k}", "") or "").strip()
            if raw and not _HEX_COLOR.match(raw):
                warnings.append(
                    f"ckanext.gobar_theme.{k}={raw!r} no es un color hex "
                    "(#rgb o #rrggbb): se ignora."
                )
    colors = gobar_color_config()
    for token, uso in (
        ("--gobar-brand", "texto blanco sobre el header y los botones"),
        ("--gobar-brand-dark", "texto blanco sobre el footer"),
        ("--gobar-interactive", "links sobre fondo blanco"),
    ):
        value = colors.get(token)
        if value:
            ratio = gobar_contrast_ratio(value, "#FFFFFF")
            if ratio < 4.5:
                warnings.append(
                    f"{token} {value} tiene contraste {ratio:.2f}:1 con el "
                    f"blanco ({uso}); WCAG AA pide 4.5:1."
                )
    return warnings


# ── Marca, contacto y "Acerca" por perfil ──
# datosgobar trae sus defaults fijos (datos.gob.ar); apn arranca vacío y usa
# la config nativa de CKAN (ckan.site_logo, ckan.site_description,
# ckan.site_about) o las claves contact_url/report_url del theme.

CKAN_DEFAULT_LOGO = "/base/images/ckan-logo.png"
DATOSGOBAR_LOGO = "images/Logo_datos-gob-ar_Blanco.png"
DATOSGOBAR_CONTACT_URL = "https://www.argentina.gob.ar/datos-abiertos/contacto"
DATOSGOBAR_DESCRIPTION = (
    "Portal de datos abiertos de la República Argentina. Los datos "
    "publicados acá son públicos y se pueden reutilizar libremente citando "
    "la fuente."
)


def gobar_site_logo() -> str:
    """URL del logo del header y del footer, o "" si no hay (apn sin
    ckan.site_logo: se muestra el título del portal como texto)."""
    configured = str(toolkit.config.get("ckan.site_logo", "") or "").strip()
    if configured == CKAN_DEFAULT_LOGO:
        configured = ""
    if not configured:
        if gobar_is_apn():
            return ""
        configured = DATOSGOBAR_LOGO
    if configured.startswith(("http://", "https://", "//")):
        return configured
    return toolkit.h.url_for_static(configured)


def gobar_site_description() -> str:
    """Texto de marca del footer: el de datos.gob.ar o ckan.site_description."""
    configured = str(toolkit.config.get("ckan.site_description", "") or "").strip()
    if configured:
        return configured
    return "" if gobar_is_apn() else DATOSGOBAR_DESCRIPTION


def gobar_contact_url() -> str:
    """Link "Contacto" del footer; vacío en apn salvo que se configure."""
    configured = str(
        toolkit.config.get("ckanext.gobar_theme.contact_url", "") or ""
    ).strip()
    if configured:
        return configured
    return "" if gobar_is_apn() else DATOSGOBAR_CONTACT_URL


def gobar_footer_contact() -> dict[str, str]:
    """Dirección, teléfono y correo del organismo para el footer; vacíos
    por defecto en los dos perfiles."""
    return {
        field: str(
            toolkit.config.get(f"ckanext.gobar_theme.contact_{field}", "") or ""
        ).strip()
        for field in ("address", "phone", "email")
    }


def gobar_report_url(ref: str) -> str:
    """URL del aviso "Reportar un problema" con ``ref`` (URL del dataset o
    recurso) en el parámetro ``referencia``, o "" si no hay formulario
    configurado (apn por defecto: el aviso no se muestra). La URL de
    report_url tiene que aceptar ?referencia=, como el formulario de Datos
    Abiertos (que corta ese campo en 128 caracteres)."""
    base = str(
        toolkit.config.get("ckanext.gobar_theme.report_url", "") or ""
    ).strip()
    if not base:
        if gobar_is_apn():
            return ""
        base = DATOSGOBAR_CONTACT_URL
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}referencia={quote(ref, safe='')}"


def gobar_site_about() -> str:
    """Texto de "Acerca" del organismo (ckan.site_about, markdown) o ""."""
    return str(toolkit.config.get("ckan.site_about", "") or "").strip()


def gobar_hero_background_style() -> str:
    image_url = toolkit.config.get("ckanext.gobar_theme.hero_background_image", "")
    if not image_url:
        return ""
    return (
        "background-image: linear-gradient(180deg, rgba(247,247,250,.88), "
        f"rgba(255,255,255,.92)), url('{image_url}'); "
        "background-size: cover; background-position: center;"
    )


def gobar_is_spatial_enabled() -> bool:
    plugins_str: str = toolkit.config.get("ckan.plugins", "")
    return any(
        p in plugins_str
        for p in ["spatial_metadata", "spatial_query", "spatial_widget_ar"]
    )


def gobar_featured_datasets(limit: int | None = None) -> list[dict[str, Any]]:
    if limit is None:
        limit = toolkit.config.get(
            "ckanext.gobar_theme.featured_datasets_limit", 6
        )
    try:
        result = toolkit.get_action("package_search")(
            {"ignore_auth": True},
            {"rows": limit, "sort": "metadata_modified desc",
             "include_private": False},
        )
        return result.get("results", [])
    except Exception:
        return []


def gobar_format_date(date_str: str | None, fmt: str = "%d-%m-%Y") -> str:
    if not date_str:
        return ""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime(fmt)
    except (ValueError, AttributeError):
        return str(date_str)


def gobar_facet_label(facet_name: str, value: str) -> str:
    """Devuelve la etiqueta legible de un valor de faceta.

    Las facetas ``extras_dataset_status`` y ``extras_dataset_accrualPeriodicity``
    guardan URIs como valor. Esta función busca el ``label`` correspondiente en
    las ``choices`` del schema de scheming. Si no lo encuentra (o el campo no es
    de scheming), devuelve el valor sin modificar.
    """
    if not value:
        return value
    field_name = facet_name
    for prefix in ("vocab_", "extras_"):
        if field_name.startswith(prefix):
            field_name = field_name[len(prefix):]
            break
    try:
        schema = toolkit.h.scheming_get_dataset_schema("dataset")
    except Exception:
        return value
    if not schema:
        return value
    for field in schema.get("dataset_fields", []):
        if field.get("field_name") != field_name:
            continue
        for choice in field.get("choices") or []:
            if choice.get("value") == value:
                label = choice.get("label")
                if isinstance(label, dict):
                    try:
                        return toolkit.h.scheming_language_text(label)
                    except Exception:
                        return label.get("es") or label.get("en") or value
                return label or value
    return value


# ── Registry ──

def get_helpers() -> dict[str, Any]:
    return {
        # Gobar home
        "gobar_dataset_count": gobar_dataset_count,
        "gobar_organization_count": gobar_organization_count,
        "gobar_group_count": gobar_group_count,
        "gobar_groups_with_details": gobar_groups_with_details,
        "gobar_organizations_with_details": gobar_organizations_with_details,
        "gobar_org_details_by_name": gobar_org_details_by_name,
        "gobar_org_tree_with_counts": gobar_org_tree_with_counts,
        "gobar_dedupe_top_nodes": gobar_dedupe_top_nodes,
        "gobar_org_root_page": gobar_org_root_page,
        # Perfil y personalización
        "gobar_get_config": gobar_get_config,
        "gobar_theme_profile": gobar_theme_profile,
        "gobar_is_apn": gobar_is_apn,
        "gobar_is_datosgobar": gobar_is_datosgobar,
        "gobar_site_logo": gobar_site_logo,
        "gobar_site_description": gobar_site_description,
        "gobar_contact_url": gobar_contact_url,
        "gobar_footer_contact": gobar_footer_contact,
        "gobar_report_url": gobar_report_url,
        "gobar_site_about": gobar_site_about,
        "gobar_show_recursos": gobar_show_recursos,
        "gobar_institutional_name": gobar_institutional_name,
        "gobar_institutional_url": gobar_institutional_url,
        "gobar_organizations_label": gobar_organizations_label,
        "gobar_show_secretariat_logo": gobar_show_secretariat_logo,
        "gobar_footer_logo_path": gobar_footer_logo_path,
        "gobar_secretariat_logo_alt": gobar_secretariat_logo_alt,
        "gobar_color_overrides_style": gobar_color_overrides_style,
        "gobar_hero_background_style": gobar_hero_background_style,
        "gobar_is_spatial_enabled": gobar_is_spatial_enabled,
        "gobar_featured_datasets": gobar_featured_datasets,
        "gobar_format_date": gobar_format_date,
        "gobar_productos_list": gobar_productos_list,
        "gobar_comunidad_list": gobar_comunidad_list,
        # Facetas
        "gobar_facet_label": gobar_facet_label,
    }

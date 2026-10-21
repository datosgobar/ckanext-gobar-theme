"""Tests unitarios de la lógica no trivial de helpers.py.

Cubren el agregado recursivo del árbol de organismos y el dedupe del listado
top-level (sobre dicts sintéticos de ``h.group_tree()``, sin fixtures de
CKAN) y el formateo de fechas que usan la tarjeta de dataset y el listado
de recursos.
"""

import pytest

import ckanext.gobar_theme.helpers as helpers


def _node(name, children=None):
    return {"name": name, "title": name.title(), "children": children or []}


def _tree():
    # economia
    #   ├─ super_seguros
    #   └─ afip
    #        └─ aduana
    # salud
    aduana = _node("aduana")
    afip = _node("afip", [aduana])
    super_seguros = _node("super_seguros")
    economia = _node("economia", [super_seguros, afip])
    salud = _node("salud")
    return [economia, salud], {
        "economia": economia,
        "super_seguros": super_seguros,
        "afip": afip,
        "aduana": aduana,
        "salud": salud,
    }


def test_org_tree_with_counts_sums_descendants(monkeypatch):
    top_nodes, by_name = _tree()
    counts = {
        "economia": 5, "super_seguros": 3, "afip": 10, "aduana": 2, "salud": 7,
    }
    monkeypatch.setattr(
        helpers, "gobar_org_details_by_name",
        lambda: {n: {"package_count": c} for n, c in counts.items()},
    )

    helpers.gobar_org_tree_with_counts(top_nodes)

    assert by_name["aduana"]["subtree_package_count"] == 2
    assert by_name["afip"]["subtree_package_count"] == 12   # 10 + 2
    assert by_name["economia"]["subtree_package_count"] == 20  # 5 + 3 + 10 + 2
    assert by_name["salud"]["subtree_package_count"] == 7


def test_org_tree_with_counts_missing_details_default_zero(monkeypatch):
    top_nodes, by_name = _tree()
    monkeypatch.setattr(helpers, "gobar_org_details_by_name", lambda: {})
    helpers.gobar_org_tree_with_counts(top_nodes)
    assert by_name["economia"]["subtree_package_count"] == 0


def test_dedupe_top_nodes_removes_nested_duplicate(monkeypatch):
    top_nodes, by_name = _tree()
    monkeypatch.setattr(
        helpers.toolkit.h, "group_tree", lambda type_: top_nodes, raising=False
    )
    # super_seguros aparece anidado bajo economia Y suelto en el top-level.
    top_nodes.append(by_name["super_seguros"])

    result = helpers.gobar_dedupe_top_nodes(top_nodes)

    names = [n["name"] for n in result]
    assert names == ["economia", "salud"]  # duplicado top-level filtrado


def test_dedupe_top_nodes_noop_without_duplicates(monkeypatch):
    top_nodes, _ = _tree()
    monkeypatch.setattr(
        helpers.toolkit.h, "group_tree", lambda type_: top_nodes, raising=False
    )
    assert helpers.gobar_dedupe_top_nodes(top_nodes) == top_nodes


def test_dedupe_top_nodes_usa_arbol_global_no_la_pagina(monkeypatch):
    # El bug real: /organization pagina y pasa solo esa página a group_tree(),
    # así que un hijo cuyo padre cayó en OTRA página se ve "top-level" en la
    # suya. El dedupe debe chequear contra el árbol GLOBAL, no contra
    # top_nodes (que acá simula una página que ni siquiera contiene al padre).
    full_top_nodes, by_name = _tree()
    monkeypatch.setattr(
        helpers.toolkit.h, "group_tree", lambda type_: full_top_nodes,
        raising=False,
    )
    # "Página 2": solo trae super_seguros suelto (su padre economia quedó en
    # la página 1 y no está en esta lista).
    page_2_top_nodes = [by_name["super_seguros"], by_name["salud"]]

    result = helpers.gobar_dedupe_top_nodes(page_2_top_nodes)

    names = [n["name"] for n in result]
    assert names == ["salud"]  # super_seguros se filtra aunque su padre no esté en esta página


# ── gobar_format_date ──
# Es la función que renderiza la fecha en la tarjeta de dataset
# (package.metadata_modified) y en el listado de recursos
# (resource.last_modified). Los casos son los formatos que efectivamente
# emite CKAN, más la basura que puede llegar de un harvest.

@pytest.mark.parametrize("valor,esperado", [
    ("2024-03-15T10:23:45.123456", "15-03-2024"),  # metadata_modified
    ("2024-03-15T10:23:45", "15-03-2024"),         # resource.last_modified
    ("2024-03-15T10:23:45Z", "15-03-2024"),        # sufijo Z
    ("2024-03-15T10:23:45+00:00", "15-03-2024"),   # con offset
    ("2024-12-01T00:00:00", "01-12-2024"),         # cero-padding de día y mes
])
def test_format_date_formatos_de_ckan(valor, esperado):
    assert helpers.gobar_format_date(valor) == esperado


@pytest.mark.parametrize("vacio", [None, ""])
def test_format_date_vacio_no_renderiza_nada(vacio):
    # El template hace {% if %} sobre el valor crudo, pero si igual llegara
    # acá tiene que devolver "" y no reventar.
    assert helpers.gobar_format_date(vacio) == ""


def test_format_date_invalida_devuelve_el_valor_original():
    assert helpers.gobar_format_date("no-es-fecha") == "no-es-fecha"


# ── Perfil, colores, marca y contacto ──

def _config(monkeypatch, **values):
    conf = {f"ckanext.gobar_theme.{k}" if "." not in k else k: v for k, v in values.items()}
    monkeypatch.setattr(helpers.toolkit, "config", conf)


@pytest.mark.parametrize("raw,esperado", [
    ("datosgobar", "datosgobar"), ("APN", "apn"), ("  DatosGobAr ", "datosgobar"),
])
def test_validate_profile_normaliza(raw, esperado):
    assert helpers.gobar_validate_profile(raw) == esperado


@pytest.mark.parametrize("raw", [None, "", "nacional", "base", "subnacional", "apn2"])
def test_validate_profile_rechaza_vacio_y_desconocidos(raw):
    with pytest.raises(ValueError, match="obligatorio"):
        helpers.gobar_validate_profile(raw)


def test_color_config_valida_y_aplica_alias(monkeypatch):
    _config(monkeypatch, color_primary="#00703C", color_brand_dark="#003",
            color_accent="rojo")
    colores = helpers.gobar_color_config()
    # alias viejo -> brand; interactive sigue a brand si no se configura;
    # "rojo" no es hex y se ignora.
    assert colores == {"--gobar-brand": "#00703C", "--gobar-brand-dark": "#003",
                       "--gobar-interactive": "#00703C"}
    assert helpers.gobar_color_overrides_style() == (
        "--gobar-brand: #00703C; --gobar-brand-dark: #003; "
        "--gobar-interactive: #00703C;")


def test_color_config_vacio_no_genera_style(monkeypatch):
    _config(monkeypatch)
    assert helpers.gobar_color_overrides_style() == ""


def test_contraste_wcag():
    assert round(helpers.gobar_contrast_ratio("#000000", "#FFFFFF"), 1) == 21.0
    assert round(helpers.gobar_contrast_ratio("#0767A7", "#FFFFFF"), 2) == 5.99
    assert round(helpers.gobar_contrast_ratio("#039BE5", "#FFFFFF"), 2) == 3.08


def test_check_colors_avisa_formato_y_contraste(monkeypatch):
    _config(monkeypatch, color_brand="#039BE5", color_accent="azul")
    avisos = helpers.gobar_check_colors()
    assert any("color_accent='azul'" in a for a in avisos)
    assert any("--gobar-brand #039BE5" in a and "3.08" in a for a in avisos)
    _config(monkeypatch, color_brand="#232D4F", color_interactive="#0767A7")
    assert helpers.gobar_check_colors() == []


def test_report_url_por_perfil(monkeypatch):
    ref = "https://datos.gob.ar/dataset/x/resource/y?a=1&b=2#frag"
    _config(monkeypatch, profile="datosgobar")
    url = helpers.gobar_report_url(ref)
    from urllib.parse import parse_qs, urlparse
    assert url.startswith(helpers.DATOSGOBAR_CONTACT_URL + "?referencia=")
    assert parse_qs(urlparse(url).query) == {"referencia": [ref]}
    _config(monkeypatch, profile="apn")
    assert helpers.gobar_report_url(ref) == ""
    _config(monkeypatch, profile="apn", report_url="https://org.gob.ar/form?x=1")
    assert helpers.gobar_report_url("r").startswith("https://org.gob.ar/form?x=1&referencia=")


def test_contacto_y_descripcion_por_perfil(monkeypatch):
    _config(monkeypatch, profile="datosgobar")
    assert helpers.gobar_contact_url() == helpers.DATOSGOBAR_CONTACT_URL
    assert helpers.gobar_site_description() == helpers.DATOSGOBAR_DESCRIPTION
    _config(monkeypatch, profile="apn")
    assert helpers.gobar_contact_url() == ""
    assert helpers.gobar_site_description() == ""
    _config(monkeypatch, **{"profile": "apn", "contact_url": "mailto:datos@org.gob.ar",
                            "ckan.site_description": "Portal del organismo"})
    assert helpers.gobar_contact_url() == "mailto:datos@org.gob.ar"
    assert helpers.gobar_site_description() == "Portal del organismo"


def test_footer_contact_vacio_por_defecto(monkeypatch):
    _config(monkeypatch, profile="apn")
    assert helpers.gobar_footer_contact() == {"address": "", "phone": "", "email": ""}
    _config(monkeypatch, **{"profile": "apn", "contact_email": " datos@org.gob.ar "})
    assert helpers.gobar_footer_contact()["email"] == "datos@org.gob.ar"


def test_site_logo_por_perfil(monkeypatch):
    monkeypatch.setattr(helpers.toolkit.h, "url_for_static", lambda p: "/static/" + p.lstrip("/"), raising=False)
    _config(monkeypatch, **{"profile": "datosgobar", "ckan.site_logo": helpers.CKAN_DEFAULT_LOGO})
    assert helpers.gobar_site_logo() == "/static/" + helpers.DATOSGOBAR_LOGO
    _config(monkeypatch, **{"profile": "apn", "ckan.site_logo": helpers.CKAN_DEFAULT_LOGO})
    assert helpers.gobar_site_logo() == ""
    _config(monkeypatch, **{"profile": "apn", "ckan.site_logo": "https://org.gob.ar/logo.svg"})
    assert helpers.gobar_site_logo() == "https://org.gob.ar/logo.svg"

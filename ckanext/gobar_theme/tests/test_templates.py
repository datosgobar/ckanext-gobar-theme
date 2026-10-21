# -*- coding: utf-8 -*-
"""Chequeos estáticos de los templates del theme: no dependen de CKAN."""
import os
import re

import jinja2
import pytest

TEMPLATES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')

# Tags propias de CKAN que Jinja a secas no conoce.
CKAN_TAGS = re.compile(
    r'\{%-?\s*(ckan_extends|link_for|snippet|asset|url_for)\b.*?-?%\}',
    re.DOTALL)

# Los nombres del estándar datgobar son largos: truncarlos deja "..." en el
# título. Ver templates/package/{base,resource_read,resource_edit_base}.html.
TRUNCA_NOMBRES = re.compile(
    r'(resource_display_name|dataset_display_name)\s*\([^)]*\)\s*\|\s*truncate')


# Las mismas extensiones que registra CKAN (ckan/lib/jinja_extensions.py).
JINJA_EXT = ['jinja2.ext.do', 'jinja2.ext.loopcontrols']


def _templates():
    for root, _dirs, files in os.walk(TEMPLATES_DIR):
        for name in files:
            if name.endswith('.html'):
                yield os.path.join(root, name)


@pytest.mark.parametrize('path', sorted(_templates()))
def test_jinja_syntax(path):
    with open(path, encoding='utf-8') as f:
        source = CKAN_TAGS.sub('', f.read())
    jinja2.Environment(extensions=JINJA_EXT).parse(source)


@pytest.mark.parametrize('path', sorted(_templates()))
def test_no_trunca_titulos(path):
    with open(path, encoding='utf-8') as f:
        assert not TRUNCA_NOMBRES.search(f.read()), \
            'el override volvió a cortar el nombre con truncate'


def test_reportar_problema_usa_url_del_helper_y_se_oculta_sin_ella():
    """El aviso toma la URL de h.gobar_report_url (que arma ?referencia=
    codificada, ver test_helpers) y no se renderiza si no hay formulario
    (perfil apn sin report_url)."""
    from types import SimpleNamespace
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    env.globals['_'] = lambda s: s
    tpl = env.get_template('snippets/reportar_problema.html')
    url = 'https://form.example/?referencia=https%3A%2F%2Fx%3Fa%3D1%26b%3D2'
    html = tpl.render(ref='x', h=SimpleNamespace(gobar_report_url=lambda ref: url))
    href = re.search(r'href="([^"]+)"', html).group(1).replace('&amp;', '&')
    assert href == url
    sin = tpl.render(ref='x', h=SimpleNamespace(gobar_report_url=lambda ref: ''))
    assert 'gobar-reportar' not in sin


def test_metadatos_oculta_vacios_y_pliega_mas():
    """La ficha de metadatos no muestra filas vacías (scheming renderiza
    todos los campos del schema aunque no tengan valor) y deja las filas
    de "Mostrar más" dentro de un <details> plegado."""
    from markupsafe import Markup
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(TEMPLATES_DIR), autoescape=True,
        extensions=JINJA_EXT)
    env.globals['_'] = lambda s: s
    html = env.get_template('snippets/gobar_metadatos.html').render(
        rows=[('Formato', 'CSV'), ('Escala', Markup('\n  <span></span> ')),
              ('Fuente', None), ('Licencia', Markup('<a href="#">CC-BY</a>'))],
        mas=[('Id', 'abc')])
    assert re.findall(r'<dt>(.*?)</dt>', html) == ['Formato', 'Licencia', 'Id']
    principal, _, plegado = html.partition('<details')
    assert 'Id' not in principal and '<dt>Id</dt>' in plegado
    assert ' open' not in plegado.split('>')[0]


def test_footer_contacto_muestra_solo_lo_configurado():
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    tpl = env.get_template('snippets/footer_contacto.html')
    vacio = {'address': '', 'phone': '', 'email': ''}
    assert '<address' not in tpl.render(contacto=vacio)
    html = tpl.render(contacto=dict(vacio, phone='+54 11 4000-0000', email='datos@org.gob.ar'))
    assert 'href="tel:+54114000-0000"' in html
    assert 'href="mailto:datos@org.gob.ar"' in html
    assert '<span>' not in html

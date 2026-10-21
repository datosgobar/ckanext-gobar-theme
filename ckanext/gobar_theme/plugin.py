# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import logging
from collections import OrderedDict
from typing import Any

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.common import CKANConfig
from ckan.config.declaration import Declaration, Key
from ckan.exceptions import CkanConfigurationException
from ckan.lib.plugins import DefaultTranslation

from ckanext.gobar_theme.views import get_blueprints
from ckanext.gobar_theme import helpers as gobar_helpers

log = logging.getLogger(__name__)

# Campos select de scheming (valores URI) que se exponen como facetas. Se
# indexan con prefijo ``vocab_`` porque en el schema Solr de CKAN ese campo
# dinámico es ``string`` (sin tokenizar) y por lo tanto faceteable de forma
# exacta, a diferencia de ``extras_*`` que es texto analizado. Ver
# before_dataset_index y dataset_facets.
SCHEMING_FACET_FIELDS = ("dataset_status", "dataset_accrualPeriodicity")


def provincias_from_index(pkg_dict: dict[str, Any]) -> list[str]:
    """Nombres de provincia para facetar, desde spatial_coverage/spatial_uri.

    Al indexar, los campos multivalor de scheming llegan como string JSON.
    Solo se toman las entradas de nivel ``Provincia`` del vocabulario
    territorio-argentina (infra.datos.gob.ar); país, departamentos, etc. se
    ignoran. Se prefiere ``spatial_coverage[].text`` (nombre con tildes) y se
    cae al slug de la URI si no está.
    """

    def loads(value: Any) -> list:
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError:
                return [value]
        if isinstance(value, list):
            return value
        return [value] if value else []

    provincias = []
    for item in loads(pkg_dict.get("spatial_coverage")):
        if isinstance(item, dict) and "/Provincia/" in (item.get("uri") or ""):
            text = item.get("text") or item["uri"].rsplit("/", 1)[1].replace("-", " ")
            provincias.append(text)
    if not provincias:
        for uri in loads(pkg_dict.get("spatial_uri")):
            if isinstance(uri, str) and "/Provincia/" in uri:
                provincias.append(uri.rsplit("/", 1)[1].replace("-", " "))
    return provincias


class GobarThemePlugin(plugins.SingletonPlugin, DefaultTranslation):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IConfigurable)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IConfigDeclaration)
    plugins.implements(plugins.IFacets)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.ITranslation)

    # ── IConfigurer ──
    def update_config(self, config_: CKANConfig) -> None:
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        # CORREGIDO: apunta a 'assets' donde está webassets.yml
        toolkit.add_resource("assets", "gobar_theme")
        # Favicon oficial de argentina.gob.ar (servido desde el public/ del
        # theme) salvo que el portal configure el suyo: solo se reemplaza
        # el default de core. CKAN__FAVICON del .env se aplica después
        # (envvars corre último) y gana igual.
        if config_.get("ckan.favicon") in (None, "", "/base/images/ckan.ico"):
            config_["ckan.favicon"] = "/images/favicon.ico"
        # ponytail: default de core es 25 y el ckan.ini del portal ya lo fija
        # explícito en ese valor, así que setdefault() no alcanza (update_config
        # corre después del ini y necesita pisarlo). Con más organismos que
        # esto, gobar_org_details_by_name() pierde logo/count de los
        # excedentes (ver helpers.py). Si algún perfil necesitara otro valor,
        # cambiarlo acá (no hay caso de uso hoy para que sea por-perfil).
        config_["ckan.group_and_organization_list_all_fields_max"] = 200

    # ── IConfigurable ──
    def configure(self, config_: CKANConfig) -> None:
        # Corre después de todos los update_config, incluido el de envvars:
        # acá ya está el valor final del .env. Sin perfil válido el portal
        # no arranca (no hay default: cada instalación elige el suyo).
        try:
            gobar_helpers.gobar_validate_profile(
                config_.get("ckanext.gobar_theme.profile")
            )
        except ValueError as error:
            raise CkanConfigurationException(str(error)) from error
        for warning in gobar_helpers.gobar_check_colors():
            log.warning("gobar_theme: %s", warning)

    # ── IBlueprint ──
    def get_blueprint(self) -> list:
        return get_blueprints()

    # ── ITemplateHelpers ──
    def get_helpers(self) -> dict[str, Any]:
        return gobar_helpers.get_helpers()

    # ── IConfigDeclaration (CKAN 2.11 strict mode) ──
    def declare_config_options(
        self, declaration: Declaration, key: Key
    ) -> None:
        # datosgobar|apn (sin distinguir mayúsculas). OBLIGATORIO y sin
        # default: configure() corta el arranque si falta o es otro valor.
        #   datosgobar - portal nacional datos.gob.ar (identidad Datos Abiertos)
        #   apn        - organismo de la Administración Pública Nacional
        declaration.declare(key.ckanext.gobar_theme.profile).required()
        # Nombre/link institucional del footer ("Institucional"): vacío por
        # defecto (todos los perfiles salvo "apn" usan el default fijo de
        # helpers.gobar_institutional_name/url, "Dirección de Datos
        # Abiertos"; en "apn" no se muestra el link salvo que se configure
        # por .env, porque cada organismo APN tiene el suyo propio).
        declaration.declare(key.ckanext.gobar_theme.institutional_name, "")
        declaration.declare(key.ckanext.gobar_theme.institutional_url, "")
        # true|false|auto. "auto" (default) = ocultar solo en el perfil
        # "apn" (la sección /recursos son productos de la Dirección de
        # Datos Abiertos, no aplican a un organismo APN individual);
        # true/false fuerza el valor sin importar el perfil.
        declaration.declare(key.ckanext.gobar_theme.show_recursos, "auto")
        # Nombre de "Organizaciones" en nav/footer/home/faceta: algunos
        # organismos APN son subdependencias de un ministerio y prefieren
        # otro término (p. ej. "Organismos", "Dependencias"). Opcional: el
        # default preserva el texto actual en todos los perfiles.
        declaration.declare(
            key.ckanext.gobar_theme.organizations_label, "Organismos"
        )
        # Subtítulo opcional del hero de la home (perfil apn, que no trae uno
        # propio): vacío = no se muestra. Ej. MAGyP: "En este portal podrás
        # obtener datos numéricos y estadísticos del sector agropecuario..."
        declaration.declare(key.ckanext.gobar_theme.subtitle, "")
        # Colores (hex #rgb/#rrggbb) por encima del preset del perfil; vacíos
        # = usar el preset. Ver el modelo en gobar-base.css ("VARIABLES") y
        # docs/personalizacion.md. color_primary/color_primary_dark quedan
        # como alias de color_brand/color_brand_dark (nombres anteriores).
        declaration.declare(key.ckanext.gobar_theme.color_brand, "")
        declaration.declare(key.ckanext.gobar_theme.color_brand_dark, "")
        declaration.declare(key.ckanext.gobar_theme.color_interactive, "")
        declaration.declare(key.ckanext.gobar_theme.color_accent, "")
        declaration.declare(key.ckanext.gobar_theme.color_primary, "")
        declaration.declare(key.ckanext.gobar_theme.color_primary_dark, "")
        # Link "Contacto" del footer y formulario del aviso "Reportar un
        # problema" (tiene que aceptar ?referencia=<url>). Vacíos: en
        # datosgobar usan el formulario de Datos Abiertos; en apn no se
        # muestran.
        declaration.declare(key.ckanext.gobar_theme.contact_url, "")
        declaration.declare(key.ckanext.gobar_theme.report_url, "")
        # Datos de contacto del organismo en el footer, debajo del texto de
        # marca. Vacíos: no se muestran.
        declaration.declare(key.ckanext.gobar_theme.contact_address, "")
        declaration.declare(key.ckanext.gobar_theme.contact_phone, "")
        declaration.declare(key.ckanext.gobar_theme.contact_email, "")
        declaration.declare(key.ckanext.gobar_theme.hero_background_image, "")
        # Logo institucional del pie: vacío = usa el logo de la Secretaría
        # de Innovación (el del portal nacional). true|false|auto (default):
        # en "auto" se oculta en el perfil apn salvo que el organismo
        # configure el suyo propio en footer_logo_path — no necesariamente
        # una URL, puede ser un archivo local servido por el theme (un
        # organismo APN no tiene por qué llevar el logo de la Secretaría de
        # Innovación, pero si quiere mostrar el suyo en ese lugar, puede).
        declaration.declare(key.ckanext.gobar_theme.show_secretariat_logo, "auto")
        declaration.declare(key.ckanext.gobar_theme.footer_logo_path, "")
        declaration.declare(
            key.ckanext.gobar_theme.secretariat_logo_alt,
            "Secretaría de Innovación, Ciencia y Tecnología",
        )
        declaration.declare_int(
            key.ckanext.gobar_theme.featured_datasets_limit, 6
        )

    # ── IFacets ──
    def dataset_facets(
        self, facets_dict: "OrderedDict[str, Any]", package_type: str
    ) -> "OrderedDict[str, Any]":
        # Para harvest u otros tipos, no tocar las facetas heredadas.
        if package_type and package_type != "dataset":
            return facets_dict
        facets = OrderedDict()
        facets["organization"] = gobar_helpers.gobar_organizations_label()
        facets["groups"] = "Temas"
        facets["res_format"] = toolkit._("Formato")
        facets["vocab_dataset_status"] = toolkit._("Estado")
        facets["vocab_dataset_accrualPeriodicity"] = toolkit._(
            "Frecuencia de actualización"
        )
        facets["vocab_provincias"] = toolkit._("Provincia")
        facets["tags"] = toolkit._("Etiquetas")
        return facets

    # IFacets exige también estos dos: CKAN los invoca en las páginas de
    # grupo/organización y sin ellos esas vistas dan 500 (AttributeError).
    # Además de no romper, pisan los labels default de CKAN core
    # ("Organizations"/"Groups" traducidos) con los mismos que usa
    # dataset_facets, para que la faceta del sidebar diga lo mismo que el
    # resto del sitio (Organismos/Temas) en vez de quedar inconsistente.
    def group_facets(
        self,
        facets_dict: "OrderedDict[str, Any]",
        group_type: str,
        package_type: str | None,
    ) -> "OrderedDict[str, Any]":
        return self._relabel_facets(facets_dict)

    def organization_facets(
        self,
        facets_dict: "OrderedDict[str, Any]",
        organization_type: str,
        package_type: str | None,
    ) -> "OrderedDict[str, Any]":
        return self._relabel_facets(facets_dict)

    @staticmethod
    def _relabel_facets(
        facets_dict: "OrderedDict[str, Any]",
    ) -> "OrderedDict[str, Any]":
        if "organization" in facets_dict:
            facets_dict["organization"] = gobar_helpers.gobar_organizations_label()
        if "groups" in facets_dict:
            facets_dict["groups"] = "Temas"
        return facets_dict

    # ── IPackageController ──
    def before_dataset_index(
        self, pkg_dict: dict[str, Any]
    ) -> dict[str, Any]:
        # Expone los campos select de scheming (extras con valor URI) como
        # campos ``vocab_*`` (string en Solr) para poder facetar de forma
        # exacta. Se indexa la ETIQUETA legible (p. ej. "actualizado") en lugar
        # de la URI, de modo que la faceta y el filtro muestren texto claro.
        for field in SCHEMING_FACET_FIELDS:
            value = pkg_dict.get(field)
            if value:
                pkg_dict["vocab_" + field] = gobar_helpers.gobar_facet_label(
                    field, value
                )
        # Provincias de la cobertura geográfica (vocab_* es string multivalor
        # en el schema Solr de CKAN, faceteable de forma exacta).
        provincias = provincias_from_index(pkg_dict)
        if provincias:
            pkg_dict["vocab_provincias"] = provincias
        return pkg_dict

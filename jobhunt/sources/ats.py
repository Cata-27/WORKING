"""Bolsas de empleo públicas de Greenhouse, Lever y Ashby para las empresas de config/empresas.yaml."""

from __future__ import annotations

import logging

from ..models import Job, fecha_desde, html_a_texto

log = logging.getLogger(__name__)

URLS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true",
    "lever": "https://api.lever.co/v0/postings/{slug}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{slug}",
}


def buscar(config, http) -> list[Job]:
    ofertas: list[Job] = []
    for empresa in config.empresas:
        ats = (empresa.get("ats") or "").lower()
        slug = empresa.get("slug")
        if ats not in URLS or not slug:
            log.warning("Empresa mal configurada en empresas.yaml: %s", empresa)
            continue
        try:
            r = http.get(URLS[ats].format(slug=slug), timeout=30)
            if r.status_code == 404:
                log.warning("%s/%s no existe (revisa el slug en empresas.yaml)", ats, slug)
                continue
            r.raise_for_status()
            datos = r.json()
        except Exception as e:
            log.warning("No se pudo leer %s/%s: %s", ats, slug, e)
            continue
        parser = PARSERS[ats]
        for job in parser(datos, empresa):
            job.es_startup = bool(empresa.get("startup"))
            ofertas.append(job)
    return ofertas


def _modalidad(texto: str, workplace: str = "") -> str:
    w = (workplace or "").lower()
    if w in ("remote", "remoto"):
        return "remoto"
    if w in ("hybrid", "hibrido", "híbrido"):
        return "hibrido"
    if w in ("onsite", "on-site", "in office", "presencial"):
        return "presencial"
    t = texto.lower()
    if "remote" in t or "remoto" in t:
        return "remoto"
    if "hybrid" in t or "híbrido" in t or "hibrido" in t:
        return "hibrido"
    return ""


def parsear_greenhouse(datos: dict, empresa: dict) -> list[Job]:
    res = []
    for j in datos.get("jobs", []):
        ubic = ((j.get("location") or {}).get("name")) or ""
        res.append(Job(
            fuente="greenhouse",
            id_fuente=f"{empresa['slug']}-{j.get('id')}",
            titulo=(j.get("title") or "").strip(),
            empresa=empresa.get("nombre") or empresa["slug"],
            url=j.get("absolute_url") or "",
            descripcion=html_a_texto(j.get("content")),
            ubicacion=ubic,
            modalidad=_modalidad(ubic),
            publicada=fecha_desde(j.get("updated_at")),
        ))
    return res


def parsear_lever(datos: list, empresa: dict) -> list[Job]:
    res = []
    for j in datos or []:
        cat = j.get("categories") or {}
        ubic = cat.get("location") or ", ".join(cat.get("allLocations") or [])
        res.append(Job(
            fuente="lever",
            id_fuente=f"{empresa['slug']}-{j.get('id')}",
            titulo=(j.get("text") or "").strip(),
            empresa=empresa.get("nombre") or empresa["slug"],
            url=j.get("hostedUrl") or j.get("applyUrl") or "",
            descripcion="\n\n".join(filter(None, [
                j.get("descriptionPlain"),
                *[f"{l.get('text', '')}\n{html_a_texto(l.get('content'))}" for l in j.get("lists") or []],
                j.get("additionalPlain"),
            ])),
            ubicacion=ubic,
            modalidad=_modalidad(ubic, j.get("workplaceType") or ""),
            publicada=fecha_desde(j.get("createdAt")),
            extra={"compromiso": cat.get("commitment") or ""},
        ))
    return res


def parsear_ashby(datos: dict, empresa: dict) -> list[Job]:
    res = []
    for j in datos.get("jobs", []):
        if j.get("isListed") is False:
            continue
        ubic = j.get("location") or ""
        workplace = j.get("workplaceType") or ("Remote" if j.get("isRemote") else "")
        res.append(Job(
            fuente="ashby",
            id_fuente=f"{empresa['slug']}-{j.get('id')}",
            titulo=(j.get("title") or "").strip(),
            empresa=empresa.get("nombre") or empresa["slug"],
            url=j.get("jobUrl") or j.get("applyUrl") or "",
            descripcion=j.get("descriptionPlain") or html_a_texto(j.get("descriptionHtml")),
            ubicacion=ubic,
            modalidad=_modalidad(ubic, workplace),
            publicada=fecha_desde(j.get("publishedAt")),
        ))
    return res


PARSERS = {"greenhouse": parsear_greenhouse, "lever": parsear_lever, "ashby": parsear_ashby}

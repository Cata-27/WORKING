"""Get on Board (getonbrd.com): portal LATAM en español con muchas startups. API pública v0."""

from __future__ import annotations

import json
import logging

from ..models import Job, fecha_desde, html_a_texto

log = logging.getLogger(__name__)

URL = "https://www.getonbrd.com/api/v0/search/jobs"
PAGINAS_POR_CONSULTA = 2
POR_PAGINA = 50

MODALIDADES = {
    "fully_remote": "remoto",
    "remote_local": "remoto",
    "temporarily_remote": "remoto",
    "hybrid": "hibrido",
    "no_remote": "presencial",
}

# ids de seniority de Get on Board
SENIORITY = {1: "sin experiencia", 2: "junior", 3: "semi senior", 4: "senior", 5: "experto"}


def buscar(config, http) -> list[Job]:
    ofertas: dict[str, Job] = {}
    for consulta in config.busqueda.get("consultas", []):
        for pagina in range(1, PAGINAS_POR_CONSULTA + 1):
            r = http.get(URL, params={
                "query": consulta,
                "per_page": POR_PAGINA,
                "page": pagina,
                "expand": json.dumps(["company"]),
            }, timeout=30)
            r.raise_for_status()
            cuerpo = r.json()
            for item in cuerpo.get("data", []):
                job = parsear(item)
                if job:
                    ofertas[job.id] = job
            total = (cuerpo.get("meta") or {}).get("total_pages") or 1
            if pagina >= total:
                break
    return list(ofertas.values())


def parsear(item: dict) -> Job | None:
    a = item.get("attributes") or {}
    titulo = a.get("title")
    if not item.get("id") or not titulo:
        return None

    compania = ((a.get("company") or {}).get("data") or {})
    empresa = (compania.get("attributes") or {}).get("name") or "Empresa (ver en Get on Board)"

    seniority_id = ((a.get("seniority") or {}).get("data") or {}).get("id")
    try:
        seniority_id = int(seniority_id) if seniority_id is not None else None
    except (TypeError, ValueError):
        seniority_id = None

    partes = [a.get("description"), a.get("functions"), a.get("desirable"), a.get("benefits")]
    descripcion = "\n\n".join(html_a_texto(p) for p in partes if p)

    paises = a.get("countries") or []
    modalidad = MODALIDADES.get(a.get("remote_modality") or "", "remoto" if a.get("remote") else "")

    return Job(
        fuente="getonbrd",
        id_fuente=str(item["id"]),
        titulo=titulo.strip(),
        empresa=empresa.strip(),
        url=(item.get("links") or {}).get("public_url") or f"https://www.getonbrd.com/jobs/{item['id']}",
        descripcion=descripcion,
        ubicacion=", ".join(str(p) for p in paises),
        modalidad=modalidad,
        publicada=fecha_desde(a.get("published_at")),
        aplicantes=a.get("applications_count"),
        extra={
            "seniority": SENIORITY.get(seniority_id, ""),
            "seniority_id": seniority_id,
            "salario_min": a.get("min_salary"),
            "salario_max": a.get("max_salary"),
            "idioma": a.get("lang") or "",
            "paises": paises,
        },
    )

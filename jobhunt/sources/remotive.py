"""Remotive (remotive.com): empleos remotos. La mayoría están en inglés; el filtro de idioma los descarta."""

from __future__ import annotations

from ..models import Job, fecha_desde, html_a_texto

URL = "https://remotive.com/api/remote-jobs"


def buscar(config, http) -> list[Job]:
    ofertas: dict[str, Job] = {}
    # Remotive pide no consultar demasiado: una llamada por categoría es suficiente.
    r = http.get(URL, params={"category": "software-dev", "limit": 300}, timeout=30)
    r.raise_for_status()
    for item in r.json().get("jobs", []):
        job = parsear(item)
        if job:
            ofertas[job.id] = job
    return list(ofertas.values())


def parsear(item: dict) -> Job | None:
    if not item.get("id") or not item.get("title"):
        return None
    return Job(
        fuente="remotive",
        id_fuente=str(item["id"]),
        titulo=item["title"].strip(),
        empresa=(item.get("company_name") or "").strip(),
        url=item.get("url") or "",
        descripcion=html_a_texto(item.get("description")),
        ubicacion=item.get("candidate_required_location") or "",
        modalidad="remoto",
        publicada=fecha_desde(item.get("publication_date")),
        extra={"tipo": item.get("job_type") or "", "salario": item.get("salary") or ""},
    )

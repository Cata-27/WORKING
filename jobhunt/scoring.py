"""Pre-puntaje por reglas (0-100) para decidir qué ofertas vale la pena evaluar con Claude."""

from __future__ import annotations

from .filters import contiene
from .models import Job, normalizar

PALABRAS_JUNIOR = [
    "junior", "jr", "trainee", "practicante", "practica", "pasante", "pasantia",
    "aprendiz", "sin experiencia", "entry level", "estudiante", "recien egresado",
]


def es_startup(job: Job, busqueda: dict) -> bool:
    return job.es_startup or bool(contiene(normalizar(job.texto_completo()), busqueda.get("senales_startup", [])))


def prepuntaje(job: Job, busqueda: dict) -> int:
    b = busqueda.get("bonificaciones", {})
    texto = normalizar(job.texto_completo())
    titulo = normalizar(job.titulo)
    puntos = 30

    if es_startup(job, busqueda):
        puntos += b.get("startup", 15)
    if contiene(titulo, PALABRAS_JUNIOR) or job.extra.get("seniority_id") in (1, 2):
        puntos += b.get("junior_o_practica", 20)
    if job.aplicantes is not None and job.aplicantes < 30:
        puntos += b.get("pocos_aplicantes", 10)
    if f" {normalizar(busqueda.get('ciudad', 'Barranquilla'))} " in f" {texto} ":
        puntos += b.get("barranquilla", 15)

    techs = sum(1 for t in busqueda.get("tecnologias_perfil", []) if contiene(texto, [t]))
    puntos += min(techs * b.get("por_tecnologia", 4), b.get("max_por_tecnologia", 20))
    return max(0, min(100, puntos))


def priorizar(ofertas: list[Job], busqueda: dict, limite: int) -> list[Job]:
    for job in ofertas:
        job.extra["prepuntaje"] = prepuntaje(job, busqueda)
        job.es_startup = es_startup(job, busqueda)
    ordenadas = sorted(ofertas, key=lambda j: j.extra["prepuntaje"], reverse=True)
    return ordenadas[:limite]

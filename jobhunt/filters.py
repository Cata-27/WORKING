"""Filtros por reglas: gratuitos y rápidos. Se ejecutan antes de gastar en Claude."""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timedelta, timezone

from .lang import es_espanol, exige_ingles
from .models import Job, normalizar


def contiene(texto_normalizado: str, palabras) -> str | None:
    """Devuelve la primera palabra/frase (normalizada) presente como palabra completa."""
    t = f" {texto_normalizado} "
    for p in palabras:
        n = normalizar(p)
        if n and f" {n} " in t:
            return p
    return None


_ANIOS = re.compile(
    r"(?:(?:al\s+menos|m[ií]nimo|minimum|at\s+least)\s+)?(\d{1,2})\s*\+?\s*(?:-|a|to)?\s*\d{0,2}\s*\+?\s*"
    r"(?:a[nñ]os|years?)\s+(?:de\s+|of\s+)?(?:experiencia|experience)"
    r"|experiencia\s+(?:m[ií]nima\s+)?(?:de\s+)?(\d{1,2})\s*\+?\s*a[nñ]os",
    re.I,
)


def anios_requeridos(texto: str) -> int | None:
    valores = [int(a or b) for a, b in _ANIOS.findall(texto)]
    return min(valores) if valores else None


class Filtro:
    def __init__(self, busqueda: dict, ahora: datetime | None = None):
        self.b = busqueda
        self.ahora = ahora or datetime.now(timezone.utc)
        self.ciudad = normalizar(busqueda.get("ciudad", "Barranquilla"))
        self.regiones_ok = list(busqueda.get("remoto_regiones_ok", [])) + ["colombia", "remote", "americas"]

    # Cada regla devuelve None si pasa, o el motivo del rechazo.
    def titulo(self, job: Job) -> str | None:
        t = normalizar(job.titulo)
        if excl := contiene(t, self.b.get("titulos_excluir", [])):
            return f"título excluido ({excl})"
        if not contiene(t, self.b.get("roles_incluir", [])):
            return "no es un rol de desarrollo"
        return None

    def nivel(self, job: Job) -> str | None:
        sid = job.extra.get("seniority_id")
        if isinstance(sid, int) and sid >= 3:
            return f"nivel {job.extra.get('seniority')}"
        anios = anios_requeridos(job.descripcion)
        if anios is not None and anios > self.b.get("max_anios_experiencia", 2):
            return f"pide {anios} años de experiencia"
        return None

    def idioma(self, job: Job) -> str | None:
        if job.extra.get("idioma") == "en":
            return "oferta en inglés"
        if not es_espanol(job.titulo + "\n" + job.descripcion):
            return "oferta en inglés"
        if exige_ingles(job.descripcion):
            return "exige inglés avanzado"
        return None

    def ubicacion(self, job: Job) -> str | None:
        ubic = normalizar(job.ubicacion)
        todo = normalizar(job.texto_completo())
        en_ciudad = f" {self.ciudad} " in f" {todo} "
        paises = [normalizar(str(p)) for p in job.extra.get("paises") or []]

        if job.modalidad == "remoto":
            if paises and not any(contiene(p, self.regiones_ok) for p in paises):
                return f"remoto solo para {', '.join(job.extra.get('paises'))}"
            if not paises and ubic and not contiene(ubic, self.regiones_ok):
                return f"remoto restringido a {job.ubicacion}"
            return None
        if job.modalidad in ("hibrido", "presencial"):
            return None if en_ciudad else f"{job.modalidad} fuera de {self.b.get('ciudad')}"
        # Modalidad desconocida: aceptamos si menciona la ciudad o una región remota válida.
        if en_ciudad or (ubic and contiene(ubic, self.regiones_ok)):
            return None
        if contiene(todo, ["remoto", "remote", "teletrabajo", "100 remoto"]):
            return None
        return "ubicación no compatible"

    def antiguedad(self, job: Job) -> str | None:
        if job.publicada is None:
            return None
        dias = (self.ahora - job.publicada).days
        if dias > self.b.get("max_dias_publicacion", 21):
            return f"publicada hace {dias} días"
        return None

    REGLAS = ("titulo", "antiguedad", "nivel", "ubicacion", "idioma")

    def motivo_rechazo(self, job: Job) -> str | None:
        for regla in self.REGLAS:
            if motivo := getattr(self, regla)(job):
                return motivo
        return None

    def aplicar(self, ofertas: list[Job]) -> tuple[list[Job], Counter]:
        aceptadas, motivos = [], Counter()
        for job in ofertas:
            motivo = self.motivo_rechazo(job)
            if motivo:
                motivos[motivo.split(" (")[0]] += 1
            else:
                aceptadas.append(job)
        return aceptadas, motivos


def deduplicar(ofertas: list[Job], vistos: set[str] = frozenset()) -> list[Job]:
    """Quita las ofertas ya vistas y las repetidas entre fuentes (misma empresa + título)."""
    salida, claves = [], set()
    for job in ofertas:
        if job.id in vistos or job.clave_duplicado in claves:
            continue
        claves.add(job.clave_duplicado)
        salida.append(job)
    return salida

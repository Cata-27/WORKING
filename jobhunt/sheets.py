"""Salida: Google Sheets vía webhook de Apps Script, con CSV local como respaldo."""

from __future__ import annotations

import csv
import json
import logging
from datetime import datetime
from pathlib import Path

import requests

from .config import RAIZ
from .models import Job

log = logging.getLogger(__name__)

COLUMNAS = [
    "Fecha", "Puntaje", "Recomendación", "Empresa", "Puesto", "Modalidad", "Ubicación",
    "¿Startup?", "Fuente", "Enlace", "Resumen", "Por qué encaja", "Riesgos",
    "Puntos a destacar", "Carta de presentación", "Mensaje corto", "Asunto del correo",
    "Preguntas probables", "Estado", "Fecha aplicación", "Notas", "ID",
]

VISTOS_LOCAL = RAIZ / "data" / "vistos.json"


def _viñetas(items) -> str:
    return "\n".join(f"• {i}" for i in items or [])


def fila(job: Job, ev: dict, contacto: str, hoy: str) -> dict:
    carta = ev.get("carta", "")
    if carta and contacto:
        carta = f"{carta.rstrip()}\n{contacto}"
    preguntas = "\n\n".join(
        f"P: {p.get('pregunta')}\nR: {p.get('respuesta_sugerida')}" for p in ev.get("preguntas_probables") or []
    )
    valores = [
        hoy, ev.get("encaje", 0), ev.get("recomendacion", ""), job.empresa, job.titulo,
        job.modalidad, job.ubicacion, "Sí" if (ev.get("es_startup") or job.es_startup) else "No",
        job.fuente, job.url, ev.get("resumen_oferta", ""), _viñetas(ev.get("razones")),
        _viñetas(ev.get("riesgos")), _viñetas(ev.get("puntos_a_destacar")), carta,
        ev.get("mensaje_corto", ""), ev.get("asunto_correo", ""), preguntas,
        "Nueva", "", "", job.id,
    ]
    return dict(zip(COLUMNAS, valores))


class Salida:
    def __init__(self, url: str = "", token: str = "", http: requests.Session | None = None,
                 carpeta: Path = RAIZ / "salida"):
        self.url, self.token = url, token
        self.http = http or requests.Session()
        self.carpeta = carpeta

    @property
    def usa_sheets(self) -> bool:
        return bool(self.url and self.token)

    # --- IDs ya evaluados -------------------------------------------------
    def vistos(self) -> set[str]:
        ids: set[str] = set()
        if VISTOS_LOCAL.exists():
            ids |= set(json.loads(VISTOS_LOCAL.read_text(encoding="utf-8")))
        if self.usa_sheets:
            try:
                r = self.http.get(self.url, params={"token": self.token, "accion": "vistos"}, timeout=60)
                r.raise_for_status()
                ids |= set(r.json().get("ids", []))
            except Exception as e:
                log.warning("No se pudieron leer los vistos de la hoja: %s", type(e).__name__)
        return ids

    def aplicadas(self) -> list[dict]:
        """Filas con estado Aplicada o Entrevista (para el skill /seguimiento)."""
        if not self.usa_sheets:
            return []
        r = self.http.get(self.url, params={"token": self.token, "accion": "aplicadas"}, timeout=60)
        r.raise_for_status()
        return r.json().get("filas", [])

    def _guardar_vistos_local(self, nuevos: list[str]) -> None:
        actuales = set()
        if VISTOS_LOCAL.exists():
            actuales = set(json.loads(VISTOS_LOCAL.read_text(encoding="utf-8")))
        VISTOS_LOCAL.parent.mkdir(parents=True, exist_ok=True)
        VISTOS_LOCAL.write_text(json.dumps(sorted(actuales | set(nuevos)), indent=0), encoding="utf-8")

    # --- Escritura -------------------------------------------------------
    def publicar(self, filas: list[dict], vistos_nuevos: list[str], enlaces: list[dict]) -> str:
        """Envía a Sheets (o CSV). Devuelve una descripción de dónde quedó."""
        self._guardar_vistos_local(vistos_nuevos)
        if self.usa_sheets:
            # Apps Script responde a POST con un redirect 302 a googleusercontent; requests lo sigue.
            r = self.http.post(self.url, data=json.dumps({
                "token": self.token,
                "columnas": COLUMNAS,
                "filas": filas,
                "vistos": vistos_nuevos,
                "enlaces": enlaces,
            }), headers={"Content-Type": "text/plain;charset=utf-8"}, timeout=120)
            r.raise_for_status()
            try:
                resultado = r.json()
            except ValueError:
                raise RuntimeError("El webhook no devolvió JSON: ¿la implementación es 'Cualquier persona'?")
            if not resultado.get("ok"):
                raise RuntimeError(f"El webhook rechazó los datos: {resultado.get('error')}")
            return f"Google Sheets ({resultado.get('agregadas', len(filas))} filas nuevas)"
        return self._csv(filas)

    def _csv(self, filas: list[dict]) -> str:
        self.carpeta.mkdir(parents=True, exist_ok=True)
        ruta = self.carpeta / f"ofertas-{datetime.now():%Y-%m-%d}.csv"
        nuevo = not ruta.exists()
        with ruta.open("a", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNAS)
            if nuevo:
                w.writeheader()
            w.writerows(filas)
        return f"CSV local {ruta.relative_to(RAIZ) if ruta.is_relative_to(RAIZ) else ruta}"

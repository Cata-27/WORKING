"""Fuentes de ofertas. Cada una expone `buscar(config, http) -> list[Job]`."""

from __future__ import annotations

import logging

import requests

from ..config import Config
from ..models import Job
from . import ats, getonbrd, remotive

log = logging.getLogger(__name__)

FUENTES = {
    "getonbrd": getonbrd.buscar,
    "remotive": remotive.buscar,
    "ats": ats.buscar,
}

USER_AGENT = "jobhunt-personal/1.0 (+https://github.com/Cata-27/WORKING)"


def nueva_sesion() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    s.headers["Accept"] = "application/json"
    return s


def recolectar(config: Config, http: requests.Session | None = None) -> list[Job]:
    http = http or nueva_sesion()
    ofertas: list[Job] = []
    for nombre, funcion in FUENTES.items():
        if not config.fuente_activa(nombre):
            continue
        try:
            encontradas = funcion(config, http)
        except Exception as e:  # una fuente caída no debe tumbar la corrida
            log.warning("Fuente %s falló: %s", nombre, e)
            continue
        log.info("Fuente %s: %d ofertas", nombre, len(encontradas))
        ofertas.extend(encontradas)
    return ofertas

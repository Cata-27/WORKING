"""Carga de configuración (YAML + perfil + variables de entorno)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
CONFIG = RAIZ / "config"


@dataclass
class Config:
    busqueda: dict
    empresas: list[dict]
    perfil: str
    contacto: str
    sheets_url: str
    sheets_token: str

    @property
    def claude(self) -> dict:
        return self.busqueda.get("claude", {})

    def fuente_activa(self, nombre: str) -> bool:
        return bool(self.busqueda.get("fuentes", {}).get(nombre, False))


def _cargar_env_local() -> None:
    """Lee un `.env` en la raíz si existe (solo para uso local; no pisa variables ya definidas)."""
    ruta = RAIZ / ".env"
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


def cargar(directorio: Path = CONFIG) -> Config:
    _cargar_env_local()
    busqueda = yaml.safe_load((directorio / "busqueda.yaml").read_text(encoding="utf-8")) or {}
    empresas_yaml = directorio / "empresas.yaml"
    empresas = []
    if empresas_yaml.exists():
        empresas = (yaml.safe_load(empresas_yaml.read_text(encoding="utf-8")) or {}).get("empresas") or []
    return Config(
        busqueda=busqueda,
        empresas=empresas,
        perfil=(directorio / "perfil.md").read_text(encoding="utf-8"),
        contacto=os.environ.get("DATOS_CONTACTO", "").strip(),
        sheets_url=os.environ.get("SHEETS_WEBHOOK_URL", "").strip(),
        sheets_token=os.environ.get("SHEETS_TOKEN", "").strip(),
    )

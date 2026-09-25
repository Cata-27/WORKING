"""Modelo común de oferta: todas las fuentes se normalizan a `Job`."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Job:
    fuente: str                 # "getonbrd", "remotive", "lever", ...
    id_fuente: str              # id dentro de la fuente
    titulo: str
    empresa: str
    url: str
    descripcion: str = ""       # texto plano
    ubicacion: str = ""         # texto libre ("Barranquilla", "Remoto LATAM", ...)
    modalidad: str = ""         # "remoto" | "hibrido" | "presencial" | ""
    publicada: datetime | None = None
    aplicantes: int | None = None
    es_startup: bool = False
    extra: dict = field(default_factory=dict)

    @property
    def id(self) -> str:
        return f"{self.fuente}:{self.id_fuente}"

    @property
    def clave_duplicado(self) -> str:
        """Misma oferta publicada en dos fuentes -> misma clave."""
        return f"{normalizar(self.empresa)}|{normalizar(self.titulo)}"

    def texto_completo(self) -> str:
        return f"{self.titulo}\n{self.ubicacion}\n{self.descripcion}"


_TAG = re.compile(r"<[^>]+>")
_BLOQUE = re.compile(r"</?(p|br|li|ul|ol|div|h\d)[^>]*>", re.I)
_ESPACIOS = re.compile(r"[ \t\r\f\v]+")
_SALTOS = re.compile(r"\n{3,}")


def html_a_texto(s: str | None) -> str:
    if not s:
        return ""
    s = html.unescape(s)            # Greenhouse entrega el HTML escapado
    s = _BLOQUE.sub("\n", s)
    s = _TAG.sub("", s)
    s = html.unescape(s)
    s = _ESPACIOS.sub(" ", s)
    return _SALTOS.sub("\n\n", s).strip()


_ACENTOS = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunAEIOUUN")


def normalizar(s: str) -> str:
    s = s.translate(_ACENTOS).lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def fecha_desde(valor) -> datetime | None:
    """Acepta epoch (s o ms), ISO 8601 o None."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, (int, float)):
        seg = valor / 1000 if valor > 10**11 else valor
        return datetime.fromtimestamp(seg, tz=timezone.utc)
    try:
        d = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)

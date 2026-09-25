"""Detección simple de idioma y de requisito de inglés (sin dependencias externas)."""

from __future__ import annotations

import re

_ES = set("""
de la que el en y los del se las por un para con no una su al lo como más pero sus le ya o
este sí porque esta entre cuando muy sin sobre también me hasta hay donde quien desde todo
nos durante todos uno les ni contra otros ese eso ante ellos e esto mí antes algunos qué
unos yo otro otras otra él tanto esa estos mucho quienes nada muchos cual poco ella estar
estas algunas algo nosotros experiencia conocimientos trabajo buscamos equipo empresa
requisitos funciones ofrecemos desarrollo años somos serás tendrás deseable
""".split())

_EN = set("""
the and of to in a is for with you we our on are be as your will this that at or by from
an have it experience team work looking skills who about us what can join years strong
knowledge ability must responsibilities requirements benefits
""".split())

_PALABRA = re.compile(r"[a-záéíóúüñ]+", re.I)


def proporcion_espanol(texto: str) -> float:
    """Fracción de palabras funcionales en español frente a inglés (0 = inglés, 1 = español)."""
    es = en = 0
    for p in _PALABRA.findall(texto.lower()):
        if p in _ES:
            es += 1
        elif p in _EN:
            en += 1
    if es + en == 0:
        return 0.5
    return es / (es + en)


def es_espanol(texto: str, umbral: float = 0.55) -> bool:
    return proporcion_espanol(texto) >= umbral


# Frases que indican que el inglés es obligatorio a nivel alto.
_INGLES_REQUERIDO = re.compile(
    r"""(
        ingl[eé]s\s*(avanzado|fluido|intermedio[\s-]*alto|conversacional|profesional|nativo|c1|c2|b2\+?)
      | (avanzado|fluido|excelente|buen|alto)\s+(nivel\s+de\s+)?ingl[eé]s
      | nivel\s+(de\s+)?ingl[eé]s\s*(b2|c1|c2|avanzado|alto)
      | ingl[eé]s\s*(\(|:|-)?\s*(b2|c1|c2)
      | biling[uü]e
      | (fluent|advanced|proficient|excellent|strong|professional)\s+(in\s+)?english
      | english\s*(\(|:|-)?\s*(b2|c1|c2|fluent|advanced|proficiency|required)
      | english[\s-]speaking
      | c1\s+english|b2\+?\s+english
    )""",
    re.I | re.X,
)

# Menciones de inglés "deseable" o básico, que no son bloqueantes.
_INGLES_OPCIONAL = re.compile(
    r"deseable|es\s+un\s+plus|un\s+plus|valorable|no\s+excluyente|opcional|nice\s+to\s+have|b[aá]sico",
    re.I,
)


def exige_ingles(texto: str) -> bool:
    """True si la oferta exige inglés a nivel intermedio-alto o superior."""
    if not texto:
        return False
    for m in _INGLES_REQUERIDO.finditer(texto):
        # Si la misma frase dice que es "deseable", no lo contamos como obligatorio.
        contexto = texto[max(0, m.start() - 40): m.end() + 40]
        if not _INGLES_OPCIONAL.search(contexto):
            return True
    return False

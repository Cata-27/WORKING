"""Evaluación de encaje y redacción de la aplicación con Claude (salida JSON estructurada)."""

from __future__ import annotations

import json
import logging

import anthropic

from .models import Job

log = logging.getLogger(__name__)

SISTEMA = """Eres la asesora de carrera de Ana Catalina, desarrolladora junior en Barranquilla (Colombia).
Recibes UNA oferta de empleo y su perfil. Haces dos cosas:

1. EVALUAR el encaje con honestidad (0-100). Criterios, en orden de peso:
   - Nivel: práctica, trainee o junior encaja; semi-senior o senior no (puntaje < 40).
   - Idioma: ella solo habla español. Si la oferta exige inglés intermedio-alto o superior, marca
     exige_ingles=true y recomienda "descartar".
   - Modalidad: debe ser remota abierta a Colombia/LATAM, o híbrida/presencial en Barranquilla.
   - Stack: coincidencia con Java, Python, JavaScript, HTML/CSS, MySQL, Flutter/React Native, Docker, IA.
     Tecnologías que no conoce no descartan si la oferta es junior y dice que enseñan.
   - Startups y empresas pequeñas son una ventaja (más fácil entrar y aprender), pero no un requisito.
   recomendacion: "aplicar" (encaje >= 70), "quizas" (50-69) o "descartar".

2. REDACTAR la aplicación (solo si la recomendación no es "descartar"; si lo es, deja carta,
   mensaje_corto y asunto_correo vacíos y preguntas_probables como lista vacía):
   - carta: carta de presentación en español, 180-250 palabras, tono cercano y profesional, sin
     clichés ("me apasiona desde niña", "soy la candidata ideal"). Conecta 2-3 requisitos concretos
     de la oferta con experiencia REAL del perfil (TikTime en producción, Hyre con IA, etc.).
     Menciona la empresa por su nombre. Termina con "Ana Catalina Torres Oñate" (sin datos de contacto;
     se agregan después).
   - mensaje_corto: 300-450 caracteres para LinkedIn o un formulario, en primera persona.
   - asunto_correo: asunto para enviar el CV por correo.
   - puntos_a_destacar: 3-5 viñetas de qué resaltar del CV para ESTA oferta.
   - preguntas_probables: 3 preguntas que probablemente harán en el formulario o la entrevista, con
     una respuesta sugerida breve basada en el perfil. Si preguntan salario, sugiere investigar el
     rango del mercado; no inventes cifras.

Reglas duras: nunca inventes experiencia, tecnologías, años ni certificaciones que no estén en el
perfil. No afirmes que habla inglés. Si falta información en la oferta, dilo en "riesgos".

PERFIL DE LA CANDIDATA:
"""

ESQUEMA = {
    "type": "object",
    "properties": {
        "encaje": {"type": "integer", "description": "0 a 100"},
        "recomendacion": {"type": "string", "enum": ["aplicar", "quizas", "descartar"]},
        "nivel_detectado": {"type": "string", "enum": ["practica", "junior", "semi_senior", "senior", "no_claro"]},
        "exige_ingles": {"type": "boolean"},
        "modalidad_compatible": {"type": "boolean"},
        "es_startup": {"type": "boolean"},
        "resumen_oferta": {"type": "string", "description": "Una línea: qué harías y con qué stack"},
        "razones": {"type": "array", "items": {"type": "string"}},
        "riesgos": {"type": "array", "items": {"type": "string"}},
        "puntos_a_destacar": {"type": "array", "items": {"type": "string"}},
        "carta": {"type": "string"},
        "mensaje_corto": {"type": "string"},
        "asunto_correo": {"type": "string"},
        "preguntas_probables": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "pregunta": {"type": "string"},
                    "respuesta_sugerida": {"type": "string"},
                },
                "required": ["pregunta", "respuesta_sugerida"],
                "additionalProperties": False,
            },
        },
    },
    "required": [
        "encaje", "recomendacion", "nivel_detectado", "exige_ingles", "modalidad_compatible",
        "es_startup", "resumen_oferta", "razones", "riesgos", "puntos_a_destacar", "carta",
        "mensaje_corto", "asunto_correo", "preguntas_probables",
    ],
    "additionalProperties": False,
}

BETA_FALLBACK = "server-side-fallback-2026-07-01"


class ErrorFatal(Exception):
    """Error que invalida toda la corrida (p. ej., API key inválida)."""


def describir_oferta(job: Job) -> str:
    lineas = [
        f"Empresa: {job.empresa}",
        f"Título: {job.titulo}",
        f"Ubicación: {job.ubicacion or 'no indicada'}",
        f"Modalidad: {job.modalidad or 'no indicada'}",
        f"Fuente: {job.fuente}",
    ]
    if job.extra.get("seniority"):
        lineas.append(f"Nivel según el portal: {job.extra['seniority']}")
    if job.extra.get("salario_min") or job.extra.get("salario_max"):
        lineas.append(f"Salario (USD/mes): {job.extra.get('salario_min')} - {job.extra.get('salario_max')}")
    if job.es_startup:
        lineas.append("Señal: parece startup o empresa pequeña")
    lineas.append("\nDescripción:\n" + (job.descripcion or "(sin descripción)"))
    return "\n".join(lineas)


class Evaluador:
    def __init__(self, perfil: str, claude_cfg: dict, cliente: anthropic.Anthropic | None = None):
        self.cliente = cliente or anthropic.Anthropic(max_retries=4)
        self.modelo = claude_cfg.get("modelo", "claude-opus-5")
        self.esfuerzo = claude_cfg.get("esfuerzo", "medium")
        self.sistema = SISTEMA + perfil

    def evaluar(self, job: Job) -> dict | None:
        try:
            respuesta = self.cliente.beta.messages.create(
                model=self.modelo,
                max_tokens=16000,
                betas=[BETA_FALLBACK],
                fallbacks="default",
                cache_control={"type": "ephemeral"},
                system=self.sistema,
                output_config={
                    "effort": self.esfuerzo,
                    "format": {"type": "json_schema", "schema": ESQUEMA},
                },
                messages=[{"role": "user", "content": describir_oferta(job)}],
            )
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as e:
            raise ErrorFatal(f"Revisa ANTHROPIC_API_KEY: {e}") from e
        except anthropic.NotFoundError as e:
            raise ErrorFatal(f"Modelo '{self.modelo}' no disponible; cámbialo en config/busqueda.yaml") from e
        except anthropic.RateLimitError:
            log.warning("Límite de uso de Claude alcanzado; se omite %s", job.id)
            return None
        except anthropic.APIStatusError as e:
            log.warning("Error de API (%s) evaluando %s", e.status_code, job.id)
            return None
        except anthropic.APIConnectionError:
            log.warning("Sin conexión con Claude evaluando %s", job.id)
            return None

        if respuesta.stop_reason == "refusal":
            log.warning("Claude declinó evaluar %s", job.id)
            return None
        if respuesta.stop_reason == "max_tokens":
            log.warning("Respuesta truncada para %s", job.id)
            return None
        texto = next((b.text for b in respuesta.content if b.type == "text"), None)
        if not texto:
            return None
        try:
            datos = json.loads(texto)
        except json.JSONDecodeError:
            log.warning("JSON inválido para %s", job.id)
            return None
        datos["encaje"] = max(0, min(100, int(datos.get("encaje", 0))))
        return datos

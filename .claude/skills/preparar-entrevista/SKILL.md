---
name: preparar-entrevista
description: Prepara una entrevista con una empresa concreta usando el agente coach-entrevistas (investigación de la empresa, pitch, respuestas STAR, preguntas técnicas junior, mini-reto y preguntas para el entrevistador). Úsalo con "/preparar-entrevista <empresa> [url de la oferta]".
argument-hint: <empresa> [url de la oferta]
---

# Preparar entrevista

Entrada: `$ARGUMENTS`. Si falta la empresa, pregúntala. Si hay una URL de la oferta, léela primero.

1. Lanza el agente `coach-entrevistas` con la empresa, la oferta (si la hay) y el tipo de entrevista (RR. HH., técnica o prueba técnica; pregúntalo si no lo sabes).
2. Muestra a Ana un resumen de 10 líneas y la ruta del archivo completo (`salida/entrevistas/<empresa>.md`).
3. Ofrece hacer un **simulacro**: tú haces de entrevistadora, una pregunta a la vez, y das retroalimentación breve después de cada respuesta.

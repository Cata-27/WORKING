---
name: preparar-aplicacion
description: Prepara el paquete de aplicación para UNA oferta concreta (URL o texto). Evalúa el encaje con evaluador-ofertas y, si vale la pena, redacta la carta, el mensaje corto, el asunto y las respuestas con redactor-aplicaciones. Úsalo con "/preparar-aplicacion <url>" o "ayúdame a aplicar a esta oferta".
argument-hint: <url o texto de la oferta>
---

# Preparar aplicación

Entrada: `$ARGUMENTS` (URL o texto de la oferta). Si está vacío, pide la URL.

1. Si es una URL, léela con WebFetch. Si la página requiere iniciar sesión (p. ej., LinkedIn), pide a Ana que pegue el texto de la oferta.
2. Lanza el agente `evaluador-ofertas` con el texto de la oferta.
3. Si la recomendación es **descartar**, explica por qué en 3 líneas y pregunta si igual quiere la carta.
4. Si es **aplicar** o **quizás**, lanza `redactor-aplicaciones` con la oferta y el resumen de la evaluación.
5. Entrega:
   - Puntaje y veredicto (1 línea).
   - Carta lista para copiar (en un bloque).
   - Mensaje corto, asunto y respuestas sugeridas.
   - Checklist de envío: ☐ CV actualizado en PDF ☐ carta adaptada ☐ enlace de GitHub ☐ registrar en la hoja como "Aplicada" con fecha.
6. Si hay hoja configurada, ofrece registrarla creando un JSON de una oferta y ejecutando
   `python -m jobhunt importar <archivo> --sin-filtros`.

No envíes nada por ella.

---
name: buscar-empleo
description: Corrida completa de búsqueda de empleo para Ana Catalina. Ejecuta el pipeline automático (APIs → filtros → Claude → Google Sheets), amplía la búsqueda en la web con el agente cazador-ofertas, evalúa lo encontrado y entrega un resumen con las mejores ofertas y los enlaces manuales del día. Úsalo cuando pida "busca trabajo", "busca ofertas" o "/buscar-empleo".
---

# Búsqueda de empleo completa

Sigue estos pasos en orden y reporta el avance en una línea por paso.

1. **Preparación**
   - `pip install -q -r requirements.txt` si hace falta.
   - Verifica si existen `ANTHROPIC_API_KEY`, `SHEETS_WEBHOOK_URL` y `SHEETS_TOKEN` (en el entorno o en `.env`). Si falta la hoja, avisa que el resultado irá a `salida/*.csv`.

2. **Pipeline automático**
   - `python -m jobhunt buscar` (o `--prueba` si no hay API key).
   - Si todas las fuentes fallan por red, dilo y continúa con el paso 3.

3. **Búsqueda web ampliada** (lo que las APIs no cubren)
   - Lanza el agente `cazador-ofertas` con la instrucción: "Busca ofertas nuevas de desarrollo junior o práctica, remoto Colombia/LATAM o híbrido en Barranquilla, priorizando startups. Guárdalas en data/bandeja.json."
   - En paralelo, si el usuario lo pide o `config/empresas.yaml` tiene menos de 10 empresas, lanza `investigador-startups`.

4. **Evaluar lo encontrado en la web**
   - `python -m jobhunt importar data/bandeja.json`. Esto usa los mismos filtros y Claude, y lo envía a la hoja sin duplicar.

5. **Resumen final para Ana** (corto, en español):
   - Top 5 del día: puntaje, empresa, puesto, modalidad, 🚀 si es startup y el enlace.
   - Cuántas quedaron en la hoja y dónde verlas.
   - Los enlaces de `python -m jobhunt enlaces` más útiles (LinkedIn 24 h, Computrabajo Barranquilla).
   - Recordatorio: **ella envía** cada aplicación y luego cambia el Estado a "Aplicada".

Nunca envíes aplicaciones ni formularios en nombre de Ana (opción B: ella aprueba y envía).

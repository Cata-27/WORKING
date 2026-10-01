# CLAUDE.md

Automatización de búsqueda de empleo para **Ana Catalina Torres Oñate**, desarrolladora junior en Barranquilla (solo español). Modo **B**: el sistema encuentra ofertas y prepara la aplicación; **Ana envía** cada una desde su cuenta. Nunca envíes formularios ni correos en su nombre.

## Estructura

- `jobhunt/`: pipeline en Python (`python -m jobhunt buscar | importar | enlaces | aplicadas`).
  - `sources/`: Get on Board, Remotive y Greenhouse/Lever/Ashby. Todo se normaliza a `models.Job`.
  - `filters.py` (reglas gratuitas) → `scoring.py` (pre-puntaje) → `llm.py` (Claude, JSON estructurado) → `sheets.py` (Apps Script o CSV).
- `config/perfil.md`: perfil de la candidata, **fuente de verdad** para evaluar y redactar. No inventes experiencia.
- `config/busqueda.yaml`: preferencias (roles, exclusiones, ubicación, modelo de Claude y límites).
- `config/empresas.yaml`: bolsas de empleo de startups (slugs verificados).
- `apps_script/Code.gs`: webhook de Google Sheets (pestañas Ofertas, Enlaces del día y Vistos, más un correo diario).
- `.claude/agents/` y `.claude/skills/`: asistentes interactivos (ver `docs/PLAN.md`).

## Ramas

- `main` (estable; de aquí corre la búsqueda diaria) ← PR desde `dev` ← PR desde ramas de trabajo.
- Nunca hagas push directo a `main` ni a `dev`: siempre por PR. Detalles en `docs/FLUJO_RAMAS.md`.

## Reglas

- Repositorio **público**: nunca escribas teléfono, correo, URLs del webhook ni tokens en archivos del repo. Los datos de contacto van en el secreto `DATOS_CONTACTO`.
- No imprimas cartas ni datos personales en los logs (los logs de Actions son públicos).
- Todo el texto dirigido a Ana va en español.
- Antes de hacer commit: `python -m pytest -q`.

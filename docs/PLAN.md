# Plan: automatización de búsqueda de empleo

## Objetivo

Encontrar cada día ofertas de desarrollo de software **junior o de práctica** que encajen con Ana Catalina, y dejar lista la aplicación de cada una (carta, mensaje corto y puntos a destacar) en Google Sheets. Ella revisa y pulsa "Enviar" (**opción B**: nada se envía sin su aprobación).

## Criterios de búsqueda

| Criterio | Valor |
|---|---|
| Rol | Desarrolladora fullstack, frontend, backend o mobile (Flutter, React Native, Java, Python, JavaScript) |
| Nivel | Práctica profesional, pasantía, trainee o junior. Se descartan senior, lead y semi-senior con 3 o más años |
| Modalidad | Remoto (abierto a Colombia o LATAM) **o** híbrido o presencial en **Barranquilla** |
| Idioma | Solo ofertas en español que **no exijan inglés** avanzado (B2 o más, fluido, bilingüe) |
| Empresas | Prioridad a **startups y empresas pequeñas** (bonificación en el puntaje), sin excluir las demás |
| Extra | Ventaja a ofertas con **pocos aplicantes** y a las publicadas hace poco |

Todo esto se cambia en `config/busqueda.yaml` sin tocar código.

## Arquitectura

```
                 ┌───────────────── GitHub Actions (lun-vie, 7:00 a. m. Bogotá) ────────────────┐
 Fuentes         │  1. Recolectar     2. Filtrar (reglas)    3. Evaluar + redactar   4. Guardar   │
 ─────────       │  ──────────────    ──────────────────     ───────────────────     ──────────   │
 Get on Board ──▶│  jobhunt.sources ─▶ jobhunt.filters     ─▶ jobhunt.llm (Claude) ─▶ Apps Script │──▶ Google Sheets
 Remotive     ──▶│  (normaliza a Job)  idioma, nivel,         puntaje 0-100,          webhook     │     + correo resumen
 Greenhouse   ──▶│                     modalidad, rol,        carta, mensaje,                     │
 Lever/Ashby  ──▶│                     antigüedad             puntos a destacar                   │
 (startups)      └─────────────────────────────────────────────────────────────────────────────────┘

 Claude Code (cuando Ana abre una sesión): skills y agentes que amplían la búsqueda con la web
 (LinkedIn, Computrabajo o empresas de Barranquilla), preparan aplicaciones a pedido,
 hacen seguimiento y preparan entrevistas.
```

### Por qué dos capas

1. **Pipeline automático (Python + GitHub Actions)**: barato y constante. Usa fuentes con API pública, que no violan términos de uso ni ponen en riesgo cuentas.
2. **Asistente interactivo (Claude Code: agentes y skills)**: para lo que no tiene API, como LinkedIn, Computrabajo, elempleo, Magneto o páginas de empresas locales. Claude busca en la web, pero **Ana envía** la aplicación desde su cuenta. Así no hay bots en LinkedIn ni riesgo de bloqueo.

## Componentes

### Código (`jobhunt/`)

| Módulo | Qué hace |
|---|---|
| `sources/getonbrd.py` | Get on Board: portal LATAM en español, con muchas startups. **Fuente principal** |
| `sources/remotive.py` | Remotive: remoto global; el filtro de idioma deja solo las ofertas en español |
| `sources/ats.py` | Greenhouse, Lever y Ashby: bolsas de empleo de startups de `config/empresas.yaml` |
| `filters.py` | Reglas gratuitas (sin IA) que descartan el 80-90 % del ruido antes de gastar en Claude |
| `lang.py` | Detecta si el texto está en español y si exige inglés |
| `scoring.py` | Pre-puntaje por reglas: startup, junior, stack, pocos aplicantes, Barranquilla |
| `llm.py` | Claude evalúa el encaje y redacta la carta y el mensaje (salida JSON estructurada) |
| `sheets.py` | Envía filas al webhook de Apps Script y, si no está configurado, guarda un CSV local |
| `links.py` | Genera cada día enlaces de búsqueda manual (LinkedIn, Computrabajo, etc.) ya filtrados |
| `cli.py` | `python -m jobhunt buscar / importar / enlaces` |

### Google Sheets (`apps_script/Code.gs`)

- Pestaña **Ofertas**: una fila por oferta, con puntaje, carta y la columna **Estado** con lista desplegable: Nueva → Aplicada → Entrevista → Oferta / Rechazada / Descartada.
- Pestaña **Enlaces del día**: búsquedas manuales ya filtradas.
- Pestaña **Vistos** (oculta): IDs ya evaluados, para no pagar dos veces por la misma oferta.
- **Correo diario** con las mejores ofertas del día.

### Agentes (`.claude/agents/`)

| Agente | Rol |
|---|---|
| `cazador-ofertas` | Busca en la web ofertas que las APIs no cubren y las deja en `data/bandeja.json` |
| `evaluador-ofertas` | Juzga una oferta contra el perfil con criterio estricto: nivel, inglés, modalidad |
| `redactor-aplicaciones` | Escribe carta, mensaje corto y respuestas a preguntas típicas, sin inventar experiencia |
| `investigador-startups` | Descubre startups colombianas y LATAM, y verifica su bolsa de empleo (Greenhouse, Lever o Ashby) |
| `coach-entrevistas` | Investiga la empresa y prepara la entrevista: preguntas técnicas junior y respuestas STAR |

### Skills (`.claude/skills/`)

| Skill | Cuándo usarlo |
|---|---|
| `/buscar-empleo` | Corrida completa: pipeline, búsqueda web extra, evaluación y Sheets |
| `/preparar-aplicacion <url>` | Paquete de aplicación para una oferta concreta |
| `/seguimiento` | Revisa lo aplicado hace 7 días o más y redacta mensajes de seguimiento |
| `/preparar-entrevista <empresa>` | Guía de entrevista personalizada |
| `/actualizar-perfil` | Actualiza `config/perfil.md` cuando cambie el CV |

## Seguridad y privacidad

- El repositorio es **público**: el teléfono y el correo **no** están en el código. Van en el secreto `DATOS_CONTACTO`.
- Las cartas **no** se imprimen en los logs de Actions (que son públicos) ni se suben como artefactos. Solo van a Sheets.
- El webhook de Sheets exige un token secreto (`SHEETS_TOKEN`).
- Recomendación: pasar el repositorio a **privado** (Settings → General → Danger zone → Change visibility).

## Costos estimados

- GitHub Actions: gratis.
- Claude: se evalúan como máximo `max_evaluaciones_por_dia` ofertas (25 por defecto), porque los filtros gratuitos van primero. Cuesta del orden de unos centavos de dólar por oferta, según el modelo y la longitud de la oferta. El modelo y el esfuerzo se ajustan en `config/busqueda.yaml`.

## Hoja de ruta

1. **Fase 1 (hecho en este PR)**: pipeline, Sheets, agentes, skills y Action diaria.
2. **Fase 2**: Ana configura los secretos y la hoja. El agente `investigador-startups` verifica y amplía `config/empresas.yaml`.
3. **Fase 3**: ajustar los pesos del puntaje según qué ofertas marca Ana como "Descartada" y cuáles como "Aplicada".
4. **Fase 4 (opcional)**: generar un CV adaptado por oferta en `.docx`.

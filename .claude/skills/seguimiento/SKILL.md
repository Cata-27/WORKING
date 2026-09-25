---
name: seguimiento
description: Revisa las aplicaciones enviadas (estado Aplicada o Entrevista en Google Sheets) y redacta mensajes de seguimiento para las que llevan 7 días o más sin respuesta, además de un resumen del embudo. Úsalo con "/seguimiento" o "¿a quién debo escribirle?".
---

# Seguimiento de aplicaciones

1. Obtén las aplicaciones con `python -m jobhunt aplicadas` (requiere `SHEETS_WEBHOOK_URL` y `SHEETS_TOKEN`). Si no hay hoja, pide a Ana que pegue la lista (empresa, puesto, fecha de aplicación, estado).
2. Hoy es la fecha del sistema (`date +%F`). Clasifica:
   - **Aplicada hace 7-13 días** → primer seguimiento.
   - **Aplicada hace 14-29 días** → segundo y último seguimiento.
   - **30 días o más** → sugerir marcar "Rechazada" (sin respuesta) y seguir adelante.
   - **Entrevista** → mensaje de agradecimiento si fue hace poco, o preguntar por los siguientes pasos si pasaron más de 5 días.
   - Sin "Fecha aplicación": pedir a Ana que la complete.
3. Para cada una, redacta un mensaje breve (≤ 600 caracteres), cordial, en español, que mencione el puesto y un aporte concreto. Sin sonar desesperada.
4. Cierra con el **embudo**: número de ofertas por estado, tasa de respuesta y una recomendación accionable (p. ej., "estás aplicando mucho a X y no responden; prioriza startups de Get on Board").

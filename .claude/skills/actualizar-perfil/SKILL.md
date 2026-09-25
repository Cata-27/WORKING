---
name: actualizar-perfil
description: Actualiza config/perfil.md a partir de un CV nuevo (.docx, .pdf o texto), o de cambios que cuente Ana (nuevo proyecto, nuevo trabajo, semestre). Úsalo cuando diga "actualicé mi CV", "agrega este proyecto" o "/actualizar-perfil".
argument-hint: [ruta al CV o descripción del cambio]
---

# Actualizar perfil

1. Lee el CV nuevo. Para `.docx`: `python -c "import zipfile,re;x=zipfile.ZipFile('RUTA').read('word/document.xml').decode();print(re.sub(r'<[^>]+>','',re.sub('</w:p>','\n',x)))"`. Para PDF usa Read.
2. Compara con `config/perfil.md` y muestra un diff resumido: qué se agrega, qué cambia y qué se elimina.
3. Aplica los cambios manteniendo la estructura del archivo. Reglas:
   - **Nunca** escribas teléfono ni correo (el repositorio es público; van en el secreto `DATOS_CONTACTO`).
   - Actualiza "Diferenciadores" si hay algo nuevo y fuerte.
   - Si aparecen tecnologías nuevas, agrégalas también a `tecnologias_perfil` en `config/busqueda.yaml`.
4. Ejecuta `python -m pytest -q` y confirma los cambios en una línea.

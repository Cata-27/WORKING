# 💼 Búsqueda de empleo automatizada

Cada mañana (lunes a viernes) este proyecto:

1. **Busca** ofertas de desarrollo junior o de práctica en Get on Board, Remotive y las bolsas de empleo de startups (Greenhouse, Lever y Ashby).
2. **Filtra** gratis por reglas: solo remoto para Colombia/LATAM o híbrido en Barranquilla, sin inglés avanzado, sin senior.
3. **Evalúa** con Claude las mejores (puntaje 0-100, con bonificación a startups).
4. **Prepara la aplicación**: carta de presentación, mensaje corto, asunto de correo, puntos a destacar y preguntas probables.
5. **Lo deja en Google Sheets** y te manda un **correo** con el resumen y los enlaces de búsqueda del día (LinkedIn, Computrabajo, etc.).

Tú revisas, copias la carta, **envías** y cambias el Estado a "Aplicada". El plan completo está en [`docs/PLAN.md`](docs/PLAN.md).

---

## Configuración (unos 20 minutos, una sola vez)

### 1. Clave de Claude
1. Entra a <https://platform.claude.com> → **API Keys** → *Create Key*.
2. Carga algo de saldo (con 5 USD alcanza para empezar; puedes bajar el costo en `config/busqueda.yaml` con `max_evaluaciones_por_dia` o `esfuerzo: low`).
3. Guarda la clave: la usarás en el paso 3.

### 2. Hoja de Google Sheets
1. Crea una hoja nueva en <https://sheets.new> y llámala, por ejemplo, **Búsqueda de empleo**.
2. **Extensiones → Apps Script**. Borra lo que haya y pega el contenido de [`apps_script/Code.gs`](apps_script/Code.gs). Guarda.
3. ⚙️ **Configuración del proyecto → Propiedades del script → Agregar propiedad**:
   - Propiedad: `TOKEN`
   - Valor: una contraseña larga inventada (ej. `busqueda-7f3k9-2026-ana`). **Anótala.**
4. Arriba, elige la función **`configurar`** y dale ▶ **Ejecutar**. Acepta los permisos (Google avisará que la app no está verificada: *Configuración avanzada → Ir a proyecto*; es tu propio script).
5. **Implementar → Nueva implementación** → ⚙️ tipo **Aplicación web**:
   - Ejecutar como: **Yo**
   - Quién tiene acceso: **Cualquier persona** (el TOKEN protege la escritura)
6. Copia la **URL de la aplicación web** (termina en `/exec`).

### 3. Secretos en GitHub
En el repositorio: **Settings → Secrets and variables → Actions → New repository secret**. Crea estos 4:

| Nombre | Valor |
|---|---|
| `ANTHROPIC_API_KEY` | la clave del paso 1 |
| `SHEETS_WEBHOOK_URL` | la URL `/exec` del paso 2.6 |
| `SHEETS_TOKEN` | la contraseña del paso 2.3 |
| `DATOS_CONTACTO` | lo que va al final de cada carta, ej. `tucorreo@gmail.com · 300 000 0000 · github.com/Cata-27` |

### 4. Probar
1. Pestaña **Actions → Buscar empleo → Run workflow**. Marca **prueba** la primera vez: solo muestra qué ofertas pasarían los filtros, sin gastar en Claude.
2. Luego ejecútalo sin la opción de prueba y con `limite` = 5. Revisa la hoja: deberían aparecer filas y llegarte un correo.
3. Listo: desde ahí corre sola cada mañana a las 6:47 a. m.

> 🔒 **Recomendado:** este repositorio es público. Tus datos personales no están en el código, pero puedes hacerlo privado en *Settings → General → Danger zone → Change visibility*. GitHub Actions sigue siendo gratis para repositorios privados, con un límite de minutos mensuales de sobra para este proyecto.

---

## Uso diario

**En la hoja**
- Ordena por **Puntaje**: verde (75 o más) es aplica ya; amarillo (55-74) vale la pena mirarlo.
- Abre el **Enlace**, copia la **Carta de presentación** o el **Mensaje corto** y envía.
- Cambia **Estado** (Nueva → Aplicada → Entrevista → Oferta / Rechazada / Descartada) y pon la **Fecha aplicación**.
- La pestaña **Enlaces del día** tiene búsquedas ya filtradas de LinkedIn, Computrabajo, elempleo, Magneto, Indeed, Wellfound y YC.

**Con Claude Code** (abre una sesión en este repositorio):

| Comando | Qué hace |
|---|---|
| `/buscar-empleo` | Corrida completa + búsqueda web extra (Barranquilla, LinkedIn, Computrabajo…) |
| `/preparar-aplicacion <url>` | Evalúa una oferta que encontraste tú y te arma la carta |
| `/seguimiento` | Te dice a quién escribirle y redacta los mensajes de seguimiento |
| `/preparar-entrevista <empresa>` | Investigación de la empresa, preguntas técnicas, STAR y simulacro |
| `/actualizar-perfil <cv>` | Actualiza tu perfil cuando cambie tu CV |

Agentes disponibles: `cazador-ofertas`, `evaluador-ofertas`, `redactor-aplicaciones`, `investigador-startups`, `coach-entrevistas`.

---

## Personalizar

- **Qué buscar**: `config/busqueda.yaml` (roles, exclusiones, días máximos, bonificaciones, modelo y límites de Claude).
- **Tu perfil**: `config/perfil.md` (todo lo que Claude sabe de ti; nunca inventa nada fuera de esto).
- **Startups a vigilar**: `config/empresas.yaml` (o pídele a Claude: *"usa investigador-startups para agregar startups colombianas"*).

## Ramas

`main` es la versión estable (de aquí corre la búsqueda diaria) y `dev` es la de integración. Todo cambio entra por **pull request**: rama de trabajo → `dev` → `main`. Ver [`docs/FLUJO_RAMAS.md`](docs/FLUJO_RAMAS.md).

## Desarrollo local

```bash
pip install -r requirements-dev.txt
cp .env.example .env          # completa tus claves (este archivo no se sube)
python -m pytest -q
python -m jobhunt buscar --prueba
python -m jobhunt buscar --limite 5
```

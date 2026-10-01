# Flujo de trabajo con ramas

```
  rama de trabajo ──PR──▶ dev ──PR──▶ main
  (feature/…, fix/…,       (integración:       (estable: de aquí corre la
   claude/…)                se prueba aquí)     búsqueda diaria programada)
```

| Rama | Para qué | Quién escribe |
|---|---|---|
| `main` | Versión estable. GitHub Actions ejecuta la búsqueda diaria **desde la rama por defecto**, que debe ser `main`. | Solo mediante PR desde `dev` |
| `dev` | Integración de cambios; aquí se prueban antes de pasar a `main`. | Solo mediante PR desde ramas de trabajo |
| `feature/…`, `fix/…`, `claude/…` | Un cambio concreto cada una. | Libre |

## Pasos

1. Crea una rama desde `dev`: `git checkout dev && git pull && git checkout -b feature/mi-cambio`.
2. Haz commits y abre un **PR hacia `dev`**. La acción **Pruebas** debe quedar en verde.
3. Revisa, fusiona y prueba en `dev` (Actions → Buscar empleo → Run workflow → rama `dev`, con **prueba** marcada).
4. Cuando `dev` esté bien, abre un **PR `dev` → `main`** y fusiónalo.

## Configuración recomendada en GitHub

- **Settings → General → Default branch → `main`**: así la búsqueda programada corre desde `main`.
- **Settings → Branches → Add branch ruleset** para `main` y `dev`: *Require a pull request before merging* y *Require status checks to pass* (check **Pruebas / pytest**).
- Después de fusionar, borra la rama de trabajo (GitHub ofrece el botón).

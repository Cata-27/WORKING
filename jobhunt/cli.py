"""Línea de comandos.

    python -m jobhunt buscar            # corrida completa (fuentes -> filtros -> Claude -> Sheets)
    python -m jobhunt buscar --prueba   # sin Claude ni Sheets: muestra qué pasaría los filtros
    python -m jobhunt importar data/bandeja.json   # evalúa ofertas encontradas por el agente cazador
    python -m jobhunt enlaces           # imprime los enlaces de búsqueda manual del día
    python -m jobhunt aplicadas         # JSON con lo aplicado (para /seguimiento)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from . import config as config_mod
from .filters import Filtro, deduplicar
from .links import enlaces_del_dia
from .llm import ErrorFatal, Evaluador
from .models import Job, fecha_desde
from .scoring import priorizar
from .sheets import Salida, fila
from .sources import recolectar

log = logging.getLogger("jobhunt")


def procesar(ofertas: list[Job], cfg, salida: Salida, *, prueba: bool, limite: int | None,
             filtrar: bool = True, evaluador: Evaluador | None = None) -> dict:
    vistos = salida.vistos()
    nuevas = deduplicar(ofertas, vistos)
    motivos = {}
    if filtrar:
        nuevas, motivos = Filtro(cfg.busqueda).aplicar(nuevas)
    lim = limite or cfg.claude.get("max_evaluaciones_por_dia", 25)
    seleccion = priorizar(nuevas, cfg.busqueda, lim)

    resumen = {
        "recolectadas": len(ofertas),
        "nuevas_tras_filtros": len(nuevas),
        "rechazos": dict(motivos),
        "evaluadas": 0,
        "a_la_hoja": 0,
        "destino": "",
        "seleccion": [(j.extra["prepuntaje"], j.empresa, j.titulo, j.fuente) for j in seleccion],
    }
    if prueba:
        return resumen

    evaluador = evaluador or Evaluador(cfg.perfil, cfg.claude)
    minimo = cfg.claude.get("puntaje_minimo_para_hoja", 55)
    hoy = datetime.now().strftime("%Y-%m-%d")
    filas, evaluadas = [], []
    for job in seleccion:
        ev = evaluador.evaluar(job)
        if ev is None:
            continue  # no se marca como vista: se reintenta en la próxima corrida
        evaluadas.append(job.id)
        log.info("%3d  %-9s  %s | %s", ev["encaje"], ev["recomendacion"], job.empresa, job.titulo)
        if ev["encaje"] >= minimo and ev["recomendacion"] != "descartar":
            filas.append(fila(job, ev, cfg.contacto, hoy))

    filas.sort(key=lambda f: f["Puntaje"], reverse=True)
    resumen["evaluadas"] = len(evaluadas)
    resumen["a_la_hoja"] = len(filas)
    resumen["destino"] = salida.publicar(filas, evaluadas, enlaces_del_dia(cfg.busqueda.get("ciudad", "Barranquilla")))
    return resumen


def leer_bandeja(ruta: Path) -> list[Job]:
    """Formato: lista de objetos con titulo, empresa, url y, opcionalmente, descripcion, ubicacion,
    modalidad (remoto|hibrido|presencial), publicada (ISO) y fuente."""
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    ofertas = []
    for d in datos:
        if not d.get("url") or not d.get("titulo"):
            continue
        ofertas.append(Job(
            fuente=d.get("fuente") or "web",
            id_fuente=hashlib.sha1(d["url"].encode()).hexdigest()[:12],
            titulo=d["titulo"],
            empresa=d.get("empresa") or "",
            url=d["url"],
            descripcion=d.get("descripcion") or "",
            ubicacion=d.get("ubicacion") or "",
            modalidad=d.get("modalidad") or "",
            publicada=fecha_desde(d.get("publicada")),
            es_startup=bool(d.get("startup")),
        ))
    return ofertas


def imprimir_resumen(r: dict, prueba: bool) -> None:
    lineas = [
        f"## Búsqueda de empleo: {datetime.now():%Y-%m-%d %H:%M}",
        "",
        f"- Ofertas recolectadas: **{r['recolectadas']}**",
        f"- Nuevas que pasan los filtros: **{r['nuevas_tras_filtros']}**",
    ]
    if not prueba:
        lineas += [
            f"- Evaluadas con Claude: **{r['evaluadas']}**",
            f"- Enviadas a la hoja: **{r['a_la_hoja']}** → {r['destino']}",
        ]
    if r["rechazos"]:
        lineas += ["", "### Motivos de descarte", ""]
        lineas += [f"- {m}: {n}" for m, n in sorted(r["rechazos"].items(), key=lambda x: -x[1])]
    if r["seleccion"]:
        lineas += ["", "### Seleccionadas para evaluar (pre-puntaje)", "", "| Pre | Empresa | Puesto | Fuente |", "|---|---|---|---|"]
        lineas += [f"| {p} | {e} | {t} | {f} |" for p, e, t, f in r["seleccion"]]
    texto = "\n".join(lineas)
    print(texto)
    if resumen_gh := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(resumen_gh, "a", encoding="utf-8") as f:
            f.write(texto + "\n")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="jobhunt", description="Búsqueda de empleo automatizada")
    sub = p.add_subparsers(dest="comando", required=True)

    b = sub.add_parser("buscar", help="Corrida completa")
    b.add_argument("--prueba", action="store_true", help="Sin Claude ni Sheets")
    b.add_argument("--limite", type=int, help="Máximo de ofertas a evaluar con Claude")

    i = sub.add_parser("importar", help="Evaluar ofertas de un JSON (bandeja del agente cazador)")
    i.add_argument("archivo", type=Path)
    i.add_argument("--prueba", action="store_true")
    i.add_argument("--sin-filtros", action="store_true", help="No aplicar filtros por reglas")
    i.add_argument("--limite", type=int)

    sub.add_parser("enlaces", help="Enlaces de búsqueda manual del día")
    sub.add_parser("aplicadas", help="Ofertas en estado Aplicada/Entrevista (JSON)")

    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    cfg = config_mod.cargar()

    if args.comando == "enlaces":
        for e in enlaces_del_dia(cfg.busqueda.get("ciudad", "Barranquilla")):
            print(f"- {e['portal']}: {e['descripcion']}\n  {e['url']}")
        return 0

    salida = Salida(cfg.sheets_url, cfg.sheets_token)
    if args.comando == "aplicadas":
        if not salida.usa_sheets:
            log.error("Configura SHEETS_WEBHOOK_URL y SHEETS_TOKEN para leer la hoja")
            return 2
        print(json.dumps(salida.aplicadas(), ensure_ascii=False, indent=2))
        return 0
    if not salida.usa_sheets:
        log.info("SHEETS_WEBHOOK_URL/SHEETS_TOKEN no configurados: se guardará un CSV en salida/")
    if not args.prueba and not os.environ.get("ANTHROPIC_API_KEY"):
        log.error("Falta ANTHROPIC_API_KEY (o usa --prueba)")
        return 2

    if args.comando == "buscar":
        ofertas = recolectar(cfg)
        filtrar = True
    else:
        ofertas = leer_bandeja(args.archivo)
        filtrar = not args.sin_filtros

    try:
        resumen = procesar(ofertas, cfg, salida, prueba=args.prueba, limite=args.limite, filtrar=filtrar)
    except ErrorFatal as e:
        log.error("%s", e)
        return 1
    imprimir_resumen(resumen, args.prueba)
    return 0


if __name__ == "__main__":
    sys.exit(main())

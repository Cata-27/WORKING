import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from jobhunt import cli, config as config_mod, sheets
from jobhunt.filters import Filtro, anios_requeridos, deduplicar
from jobhunt.lang import es_espanol, exige_ingles
from jobhunt.models import Job, html_a_texto
from jobhunt.scoring import prepuntaje
from jobhunt.sources import ats, getonbrd, remotive

FIX = Path(__file__).parent / "fixtures"
AHORA = datetime(2026, 9, 25, tzinfo=timezone.utc)


def fixture(nombre):
    return json.loads((FIX / nombre).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def cfg():
    return config_mod.cargar()


@pytest.fixture
def filtro(cfg):
    return Filtro(cfg.busqueda, ahora=AHORA)


# --- Fuentes -------------------------------------------------------------

def test_getonbrd_parsea_empresa_modalidad_y_seniority():
    jobs = [getonbrd.parsear(i) for i in fixture("getonbrd.json")["data"]]
    junior = jobs[0]
    assert junior.empresa == "Startup X"
    assert junior.modalidad == "remoto"
    assert junior.extra["seniority_id"] == 2
    assert junior.aplicantes == 12
    assert "Integrar APIs" in junior.descripcion
    assert "<" not in junior.descripcion
    assert junior.id == "getonbrd:desarrollador-fullstack-junior-startup-x-remote"


def test_ats_parsers():
    emp = {"nombre": "Ejemplo", "slug": "ejemplo"}
    lever = ats.parsear_lever(fixture("lever.json"), emp)[0]
    assert lever.modalidad == "hibrido" and "Barranquilla" in lever.ubicacion
    assert "Estudiante de ingeniería" in lever.descripcion
    gh = ats.parsear_greenhouse(fixture("greenhouse.json"), emp)[0]
    assert "HTML, CSS" in gh.descripcion and "&lt;" not in gh.descripcion
    assert gh.modalidad == "remoto"
    ash = ats.parsear_ashby(fixture("ashby.json"), emp)[0]
    assert ash.modalidad == "presencial"


def test_fuente_ats_tolera_slug_inexistente(cfg):
    class Http:
        def get(self, url, timeout):
            return SimpleNamespace(status_code=404)
    c = SimpleNamespace(empresas=[{"nombre": "X", "ats": "lever", "slug": "no-existe"}])
    assert ats.buscar(c, Http()) == []


# --- Idioma --------------------------------------------------------------

@pytest.mark.parametrize("texto,esperado", [
    ("Requisitos: inglés avanzado (C1)", True),
    ("Nivel de inglés B2 o superior", True),
    ("Fluent English is a must", True),
    ("Buscamos persona bilingüe", True),
    ("Inglés básico", False),
    ("Inglés deseable, no excluyente", False),
    ("Inglés avanzado es un plus, deseable", False),
    ("Trabajarás con Python y MySQL", False),
])
def test_exige_ingles(texto, esperado):
    assert exige_ingles(texto) is esperado


def test_detecta_espanol():
    assert es_espanol("Buscamos una persona para nuestro equipo de desarrollo con experiencia en Java")
    assert not es_espanol("We are looking for a developer to join our team with experience in Java")


def test_anios_requeridos():
    assert anios_requeridos("Mínimo 3 años de experiencia en backend") == 3
    assert anios_requeridos("5+ years of experience") == 5
    assert anios_requeridos("experiencia de 1 año") is None or anios_requeridos("experiencia de 1 año") <= 1
    assert anios_requeridos("Sin experiencia previa") is None
    assert anios_requeridos("Con 30 years of experience delivering software") is None


# --- Filtros -------------------------------------------------------------

def test_filtros_sobre_fixtures(filtro):
    emp = {"nombre": "Ejemplo", "slug": "ejemplo"}
    ofertas = (
        [getonbrd.parsear(i) for i in fixture("getonbrd.json")["data"]]
        + [remotive.parsear(i) for i in fixture("remotive.json")["jobs"]]
        + ats.parsear_lever(fixture("lever.json"), emp)
        + ats.parsear_greenhouse(fixture("greenhouse.json"), emp)
        + ats.parsear_ashby(fixture("ashby.json"), emp)
    )
    aceptadas, motivos = filtro.aplicar(ofertas)
    titulos = sorted(j.titulo for j in aceptadas)
    assert titulos == [
        "Desarrollador Backend Junior",            # remotive, LATAM, español
        "Desarrollador Frontend Junior",           # greenhouse remoto LATAM
        "Desarrollador Mobile Flutter Trainee",    # lever híbrido Barranquilla
        "Desarrollador/a Fullstack Junior",        # getonbrd remoto Colombia
    ]
    assert motivos["título excluido"] == 1          # Senior Backend Engineer
    assert motivos["presencial fuera de Barranquilla"] == 1  # práctica en Bogotá
    assert motivos["remoto fuera de Colombia/LATAM"] == 1    # USA Only
    assert ("remotive", "Junior Frontend Developer", "remoto restringido a USA Only") in filtro.descartes


def _job(**kw):
    base = dict(fuente="t", id_fuente="1", titulo="Desarrollador Junior", empresa="E", url="u",
                descripcion="Buscamos una persona para nuestro equipo de desarrollo web.",
                modalidad="remoto", ubicacion="")
    base.update(kw)
    return Job(**base)


def test_remoto_local_de_otro_pais_se_descarta(filtro):
    j = _job(extra={"paises": ["México"]})
    assert "remoto solo para" in filtro.motivo_rechazo(j)


def test_hibrido_en_barranquilla_pasa(filtro):
    j = _job(modalidad="hibrido", ubicacion="Barranquilla, Atlántico")
    assert filtro.motivo_rechazo(j) is None


def test_semi_senior_y_anios(filtro):
    assert filtro.motivo_rechazo(_job(titulo="Desarrollador Semi Senior Java"))
    j = _job(descripcion="Buscamos una persona para el equipo con 4 años de experiencia en Java y de la empresa.")
    assert "4 años" in filtro.motivo_rechazo(j)


def test_oferta_vieja(filtro):
    j = _job(publicada=datetime(2026, 7, 1, tzinfo=timezone.utc))
    assert "publicada hace" in filtro.motivo_rechazo(j)


def test_deduplicar_entre_fuentes_y_vistos():
    a = _job(fuente="getonbrd", id_fuente="1", empresa="Acme", titulo="Dev Junior")
    b = _job(fuente="lever", id_fuente="9", empresa="ACME", titulo="Dev  junior")
    c = _job(fuente="remotive", id_fuente="3", titulo="Otro")
    assert deduplicar([a, b, c], vistos={"remotive:3"}) == [a]


# --- Puntaje -------------------------------------------------------------

def test_prepuntaje_premia_startup_junior_y_barranquilla(cfg):
    base = prepuntaje(_job(titulo="Desarrollador web"), cfg.busqueda)
    mejor = prepuntaje(_job(titulo="Desarrollador web junior",
                            descripcion="Startup en Barranquilla, Python y Flutter", aplicantes=5), cfg.busqueda)
    assert mejor > base
    assert mejor <= 100


# --- Salida y orquestación ------------------------------------------------

def test_html_a_texto():
    assert html_a_texto("<p>Hola&nbsp;<b>mundo</b></p><ul><li>uno</li></ul>") == "Hola\xa0mundo\n\nuno"


class EvaluadorFalso:
    def __init__(self, puntajes):
        self.puntajes = puntajes

    def evaluar(self, job):
        p = self.puntajes.get(job.titulo)
        if p is None:
            return None
        return {"encaje": p, "recomendacion": "aplicar" if p >= 70 else "descartar", "es_startup": True,
                "resumen_oferta": "r", "razones": ["a"], "riesgos": [], "puntos_a_destacar": ["TikTime"],
                "carta": "Hola equipo.\nAna Catalina Torres Oñate", "mensaje_corto": "m", "asunto_correo": "s",
                "preguntas_probables": [{"pregunta": "¿Por qué?", "respuesta_sugerida": "Porque sí"}]}


def test_procesar_envia_solo_buenas_y_marca_vistas(cfg, tmp_path, monkeypatch):
    monkeypatch.setattr(sheets, "VISTOS_LOCAL", tmp_path / "vistos.json")
    salida = sheets.Salida(carpeta=tmp_path)
    buena = _job(id_fuente="1", titulo="Desarrollador Junior Flutter")
    mala = _job(id_fuente="2", titulo="Desarrollador Junior PHP")
    falla = _job(id_fuente="3", titulo="Desarrollador Junior Java")
    ev = EvaluadorFalso({buena.titulo: 85, mala.titulo: 30})
    cfg.contacto = "correo@ejemplo.com"

    r = cli.procesar([buena, mala, falla], cfg, salida, prueba=False, limite=None, evaluador=ev)

    assert r["evaluadas"] == 2 and r["a_la_hoja"] == 1
    vistos = set(json.loads((tmp_path / "vistos.json").read_text()))
    assert vistos == {buena.id, mala.id}            # la que falló se reintenta mañana
    csv_txt = next(tmp_path.glob("ofertas-*.csv")).read_text(encoding="utf-8-sig")
    assert "Desarrollador Junior Flutter" in csv_txt and "PHP" not in csv_txt
    assert "correo@ejemplo.com" in csv_txt           # contacto al final de la carta

    # Segunda corrida: nada nuevo que evaluar salvo la que falló.
    r2 = cli.procesar([buena, mala, falla], cfg, salida, prueba=True, limite=None)
    assert [s[2] for s in r2["seleccion"]] == [falla.titulo]


def test_leer_bandeja(tmp_path):
    ruta = tmp_path / "b.json"
    ruta.write_text(json.dumps([
        {"titulo": "Dev Junior", "empresa": "Local SAS", "url": "https://x.co/1", "modalidad": "hibrido",
         "ubicacion": "Barranquilla", "startup": True},
        {"titulo": "sin url"},
    ]), encoding="utf-8")
    ofertas = cli.leer_bandeja(ruta)
    assert len(ofertas) == 1 and ofertas[0].es_startup and ofertas[0].fuente == "web"


def test_empresas_yaml_valido(cfg):
    assert cfg.empresas, "empresas.yaml no tiene empresas activas"
    for e in cfg.empresas:
        assert e.get("ats") in ats.URLS, e
        assert e.get("slug") and e.get("nombre"), e

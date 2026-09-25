import json
from types import SimpleNamespace

from jobhunt.llm import BETA_FALLBACK, ESQUEMA, Evaluador
from jobhunt.models import Job


class ClienteFalso:
    def __init__(self, respuesta):
        self.respuesta = respuesta
        self.kwargs = None
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.kwargs = kwargs
        return self.respuesta


JOB = Job(fuente="t", id_fuente="1", titulo="Desarrollador Junior", empresa="Acme", url="u",
          descripcion="Buscamos junior con Python.", modalidad="remoto")


def _resp(stop="end_turn", texto=None):
    contenido = [SimpleNamespace(type="thinking", thinking="")]
    if texto is not None:
        contenido.append(SimpleNamespace(type="text", text=texto))
    return SimpleNamespace(stop_reason=stop, content=contenido)


def test_request_usa_schema_fallback_y_perfil():
    datos = {k: [] for k in ESQUEMA["required"]}
    datos.update(encaje=140, recomendacion="aplicar")
    cli = ClienteFalso(_resp(texto=json.dumps(datos)))
    ev = Evaluador("PERFIL-DE-PRUEBA", {"modelo": "claude-opus-5", "esfuerzo": "low"}, cliente=cli).evaluar(JOB)
    assert ev["encaje"] == 100  # se acota a 0-100
    k = cli.kwargs
    assert k["model"] == "claude-opus-5"
    assert k["betas"] == [BETA_FALLBACK] and k["fallbacks"] == "default"
    assert k["output_config"]["effort"] == "low"
    assert k["output_config"]["format"]["schema"] is ESQUEMA
    assert k["system"].endswith("PERFIL-DE-PRUEBA")
    assert "Acme" in k["messages"][0]["content"]


def test_rechazo_y_truncado_devuelven_none():
    for r in (_resp(stop="refusal"), _resp(stop="max_tokens", texto="{"), _resp(texto="no-json")):
        assert Evaluador("p", {}, cliente=ClienteFalso(r)).evaluar(JOB) is None

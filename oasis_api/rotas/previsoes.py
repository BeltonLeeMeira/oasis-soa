from fastapi import APIRouter

from ..esquemas import PrevisaoSaida, SimulacaoEntrada
from ..servicos import PrevisaoServico, ResultadoPrevisao
from .dependencias import ConfigDep, ModeloDep, SessaoDep

router = APIRouter(prefix="/api/previsoes", tags=["Previsão (IA)"])


def _saida(r: ResultadoPrevisao) -> PrevisaoSaida:
    return PrevisaoSaida(
        data_alvo=r.data_alvo,
        probabilidade=round(r.probabilidade, 4),
        risco=r.risco,
        limiar=r.limiar,
        versao_modelo=r.versao_modelo,
        leituras_usadas=r.leituras_usadas,
        atributos={nome: round(valor, 3) for nome, valor in r.atributos.items()},
    )


@router.get("/amanha", response_model=PrevisaoSaida, summary="Chance de amanhã ser dia de risco, com as leituras de hoje")
def prever_amanha(sessao: SessaoDep, config: ConfigDep, modelo: ModeloDep):
    return _saida(PrevisaoServico(sessao, modelo, config.zona).amanha())


@router.post("/simular", response_model=PrevisaoSaida, summary="Testa o modelo com um dia digitado (não grava)")
def simular(dados: SimulacaoEntrada, sessao: SessaoDep, config: ConfigDep, modelo: ModeloDep):
    atributos = {
        "temp_max": dados.temp_max,
        "temp_min": dados.temp_min,
        "temp_media": dados.temp_media,
        "umid_media": dados.umid_media,
        "umid_min": dados.umid_min,
        "ic_max": dados.ic_max,
    }
    return _saida(PrevisaoServico(sessao, modelo, config.zona).simular(atributos, dados.data_alvo))

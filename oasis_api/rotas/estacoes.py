from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from ..esquemas import EstacaoCriar, EstacaoSaida, LeituraCriar, LeituraRegistradaSaida, LeituraSaida
from ..seguranca import exigir_chave_posto
from ..servicos import EstacaoServico, LeituraServico
from .dependencias import SessaoDep

router = APIRouter(tags=["Estações e leituras"])


@router.get("/api/estacoes", response_model=list[EstacaoSaida], summary="Lista as estações")
def listar_estacoes(sessao: SessaoDep):
    return EstacaoServico(sessao).listar()


@router.post(
    "/api/estacoes",
    status_code=201,
    response_model=EstacaoSaida,
    dependencies=[Depends(exigir_chave_posto)],
    summary="Cadastra uma estação (exclusivo do posto)",
)
def criar_estacao(dados: EstacaoCriar, sessao: SessaoDep):
    return EstacaoServico(sessao).criar(dados.codigo, dados.nome, dados.latitude, dados.longitude, dados.ativa)


@router.get("/api/estacoes/{estacao_id}/leituras", response_model=list[LeituraSaida], summary="Histórico de uma estação")
def listar_leituras(
    estacao_id: Annotated[int, Path(ge=1)],
    sessao: SessaoDep,
    desde: datetime | None = None,
    limite: Annotated[int, Query(ge=1, le=1000)] = 100,
):
    return LeituraServico(sessao).listar(estacao_id, desde, limite)


@router.post(
    "/api/leituras",
    status_code=201,
    response_model=LeituraRegistradaSaida,
    dependencies=[Depends(exigir_chave_posto)],
    summary="Registra uma leitura por HTTP (testes e plano B da estação)",
)
def registrar_leitura(dados: LeituraCriar, sessao: SessaoDep):
    registro = LeituraServico(sessao).registrar(dados.codigo, dados.temperatura, dados.umidade)
    leitura = registro.leitura
    return LeituraRegistradaSaida(
        id=leitura.id,
        estacao_id=leitura.estacao_id,
        temperatura=leitura.temperatura,
        umidade=leitura.umidade,
        indice_calor=leitura.indice_calor,
        nivel=leitura.nivel,
        recebida_em=leitura.recebida_em,
        acao_alerta=registro.acao_alerta.value,
    )

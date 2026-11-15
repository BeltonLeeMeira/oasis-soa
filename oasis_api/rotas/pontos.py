from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, Query, Request

from ..dominio.enums import StatusPonto, TipoPonto
from ..dominio.erros import NaoEncontradoErro
from ..erros_http import AcessoNegadoErro
from ..esquemas import PontoCriar, PontoSaida, StatusAlterar
from ..seguranca import chave_posto_valida, exigir_chave_posto
from ..servicos import PontoServico
from .dependencias import SessaoDep

router = APIRouter(prefix="/api/pontos", tags=["Pontos de apoio"])


def _saida(ponto, distancia: int | None = None) -> PontoSaida:
    saida = PontoSaida.model_validate(ponto)
    saida.distancia_metros = distancia
    return saida


@router.get("", response_model=list[PontoSaida], summary="Lista pontos de água, sombra e climatizados")
def listar_pontos(
    request: Request,
    sessao: SessaoDep,
    tipo: TipoPonto | None = None,
    status: StatusPonto = StatusPonto.APROVADO,
    bairro: Annotated[str | None, Query(max_length=60)] = None,
    busca: Annotated[str | None, Query(max_length=60, description="Parte do nome do ponto")] = None,
    lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    lon: Annotated[float | None, Query(ge=-180, le=180)] = None,
    raio: Annotated[int | None, Query(ge=50, le=50_000, description="Raio em metros (com lat e lon)")] = None,
    x_chave_posto: Annotated[str | None, Header()] = None,
):
    # Pontos ainda não aprovados não foram revisados: só o posto pode vê-los.
    if status is not StatusPonto.APROVADO and not chave_posto_valida(request, x_chave_posto):
        raise AcessoNegadoErro()
    resultado = PontoServico(sessao).listar(tipo, status, bairro, busca, lat, lon, raio)
    return [_saida(ponto, distancia) for ponto, distancia in resultado]


@router.get("/{ponto_id}", response_model=PontoSaida, summary="Detalhe de um ponto")
def obter_ponto(
    request: Request,
    ponto_id: Annotated[int, Path(ge=1)],
    sessao: SessaoDep,
    x_chave_posto: Annotated[str | None, Header()] = None,
):
    ponto = PontoServico(sessao).obter(ponto_id)
    if ponto.status is not StatusPonto.APROVADO and not chave_posto_valida(request, x_chave_posto):
        raise NaoEncontradoErro(f"Ponto {ponto_id} não encontrado.")
    return _saida(ponto)


@router.post("", status_code=201, response_model=PontoSaida, summary="Sugere um ponto novo (entra como Pendente)")
def criar_ponto(dados: PontoCriar, sessao: SessaoDep):
    ponto = PontoServico(sessao).criar(
        dados.nome,
        dados.tipo,
        dados.endereco,
        dados.bairro,
        dados.latitude,
        dados.longitude,
        dados.horario,
        dados.criado_por_id,
    )
    return _saida(ponto)


@router.patch(
    "/{ponto_id}/status",
    response_model=PontoSaida,
    dependencies=[Depends(exigir_chave_posto)],
    summary="Aprova ou rejeita um ponto (exclusivo do posto)",
)
def alterar_status(ponto_id: Annotated[int, Path(ge=1)], dados: StatusAlterar, sessao: SessaoDep):
    return _saida(PontoServico(sessao).alterar_status(ponto_id, dados.status))

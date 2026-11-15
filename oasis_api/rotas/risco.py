from typing import Annotated

from fastapi import APIRouter, Query

from ..esquemas import AlertaSaida, RiscoSaida
from ..servicos import AlertaServico, RiscoServico
from .dependencias import ConfigDep, SessaoDep

router = APIRouter(tags=["Risco e alertas"])


@router.get("/api/risco/agora", response_model=list[RiscoSaida], summary="Última leitura de cada estação ativa")
def risco_agora(sessao: SessaoDep, config: ConfigDep):
    resultado = []
    for item in RiscoServico(sessao, config.leitura_atualizada_min).agora():
        leitura = item.leitura
        resultado.append(
            RiscoSaida(
                estacao=item.estacao.codigo,
                nome=item.estacao.nome,
                temperatura=leitura.temperatura if leitura else None,
                umidade=leitura.umidade if leitura else None,
                indice_calor=leitura.indice_calor if leitura else None,
                nivel=leitura.nivel if leitura else None,
                recebida_em=leitura.recebida_em if leitura else None,
                atualizada=item.atualizada,
            )
        )
    return resultado


@router.get("/api/alertas", response_model=list[AlertaSaida], summary="Alertas ativos")
def listar_alertas(sessao: SessaoDep, config: ConfigDep, ativos: Annotated[bool, Query()] = True):
    alertas = AlertaServico(sessao, config.zona).ativos() if ativos else AlertaServico(sessao, config.zona).recentes()
    return [
        AlertaSaida(
            id=a.id,
            estacao=a.estacao.codigo if a.estacao else None,
            nivel=a.nivel,
            origem=a.origem,
            mensagem=a.mensagem,
            data_alvo=a.data_alvo,
            inicio=a.inicio,
            fim=a.fim,
        )
        for a in alertas
    ]

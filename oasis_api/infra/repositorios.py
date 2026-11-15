"""Repositórios: todo acesso ao banco passa por aqui.

As consultas usam a API do SQLAlchemy, que gera SQL com parâmetros vinculados
(ex.: WHERE nome ILIKE %(nome_1)s). O valor digitado nunca é concatenado ao SQL,
o que impede SQL Injection.
"""

from datetime import date, datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ..dominio.enums import OrigemAlerta, StatusPonto, TipoPonto
from .tabelas import Alerta, Estacao, Leitura, PontoApoio, Previsao, Usuario


def _escapar_like(texto: str) -> str:
    """Faz %, _ e \\ digitados pelo usuário serem tratados como texto comum no ILIKE."""
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class UsuarioRepositorio:
    def __init__(self, sessao: Session) -> None:
        self.sessao = sessao

    def adicionar(self, usuario: Usuario) -> Usuario:
        self.sessao.add(usuario)
        self.sessao.flush()
        return usuario

    def obter(self, usuario_id: int) -> Usuario | None:
        return self.sessao.get(Usuario, usuario_id)


class PontoRepositorio:
    def __init__(self, sessao: Session) -> None:
        self.sessao = sessao

    def adicionar(self, ponto: PontoApoio) -> PontoApoio:
        self.sessao.add(ponto)
        self.sessao.flush()
        return ponto

    def obter(self, ponto_id: int) -> PontoApoio | None:
        return self.sessao.get(PontoApoio, ponto_id)

    def listar(
        self,
        tipo: TipoPonto | None = None,
        status: StatusPonto | None = None,
        bairro: str | None = None,
        busca: str | None = None,
    ) -> list[PontoApoio]:
        consulta = select(PontoApoio)
        if tipo is not None:
            consulta = consulta.where(PontoApoio.tipo == tipo)
        if status is not None:
            consulta = consulta.where(PontoApoio.status == status)
        if bairro:
            consulta = consulta.where(func.lower(PontoApoio.bairro) == bairro.lower())
        if busca:
            consulta = consulta.where(PontoApoio.nome.ilike(f"%{_escapar_like(busca)}%", escape="\\"))
        return list(self.sessao.scalars(consulta.order_by(PontoApoio.nome)))


class EstacaoRepositorio:
    def __init__(self, sessao: Session) -> None:
        self.sessao = sessao

    def adicionar(self, estacao: Estacao) -> Estacao:
        self.sessao.add(estacao)
        self.sessao.flush()
        return estacao

    def obter(self, estacao_id: int) -> Estacao | None:
        return self.sessao.get(Estacao, estacao_id)

    def obter_por_codigo(self, codigo: str) -> Estacao | None:
        return self.sessao.scalar(select(Estacao).where(Estacao.codigo == codigo))

    def listar(self, apenas_ativas: bool = False) -> list[Estacao]:
        consulta = select(Estacao).order_by(Estacao.codigo)
        if apenas_ativas:
            consulta = consulta.where(Estacao.ativa.is_(True))
        return list(self.sessao.scalars(consulta))


class LeituraRepositorio:
    def __init__(self, sessao: Session) -> None:
        self.sessao = sessao

    def adicionar(self, leitura: Leitura) -> Leitura:
        self.sessao.add(leitura)
        self.sessao.flush()
        return leitura

    def ultimas_por_estacao(self) -> dict[int, Leitura]:
        """Última leitura de cada estação (o maior id é sempre a mais recente)."""
        ultimos = select(func.max(Leitura.id)).group_by(Leitura.estacao_id).scalar_subquery()
        leituras = self.sessao.scalars(select(Leitura).where(Leitura.id.in_(ultimos)))
        return {leitura.estacao_id: leitura for leitura in leituras}

    def listar_da_estacao(self, estacao_id: int, desde: datetime | None, limite: int) -> list[Leitura]:
        consulta = select(Leitura).where(Leitura.estacao_id == estacao_id)
        if desde is not None:
            consulta = consulta.where(Leitura.recebida_em >= desde)
        return list(self.sessao.scalars(consulta.order_by(Leitura.recebida_em.desc()).limit(limite)))

    def valores_entre(self, inicio: datetime, fim: datetime) -> list[tuple[float, float]]:
        """(temperatura, umidade) das estações ativas num intervalo, para o modelo de IA."""
        consulta = (
            select(Leitura.temperatura, Leitura.umidade)
            .join(Estacao, Estacao.id == Leitura.estacao_id)
            .where(Estacao.ativa.is_(True), Leitura.recebida_em >= inicio, Leitura.recebida_em < fim)
        )
        return [(float(t), float(u)) for t, u in self.sessao.execute(consulta)]


class AlertaRepositorio:
    def __init__(self, sessao: Session) -> None:
        self.sessao = sessao

    def adicionar(self, alerta: Alerta) -> Alerta:
        self.sessao.add(alerta)
        self.sessao.flush()
        return alerta

    def ativo_de_sensor(self, estacao_id: int) -> Alerta | None:
        return self.sessao.scalar(
            select(Alerta).where(
                Alerta.estacao_id == estacao_id, Alerta.origem == OrigemAlerta.SENSOR, Alerta.fim.is_(None)
            )
        )

    def de_previsao_para(self, data_alvo: date) -> Alerta | None:
        return self.sessao.scalar(
            select(Alerta).where(Alerta.origem == OrigemAlerta.PREVISAO, Alerta.data_alvo == data_alvo)
        )

    def ativos(self) -> list[Alerta]:
        return list(self.sessao.scalars(select(Alerta).where(Alerta.fim.is_(None)).order_by(Alerta.inicio.desc())))

    def recentes(self, limite: int = 50) -> list[Alerta]:
        return list(self.sessao.scalars(select(Alerta).order_by(Alerta.inicio.desc()).limit(limite)))

    def encerrar_previsoes_vencidas(self, hoje: date, agora: datetime) -> int:
        """Alerta de previsão vale até o fim do dia previsto."""
        resultado = self.sessao.execute(
            update(Alerta)
            .where(Alerta.origem == OrigemAlerta.PREVISAO, Alerta.fim.is_(None), Alerta.data_alvo < hoje)
            .values(fim=agora)
        )
        return resultado.rowcount or 0


class PrevisaoRepositorio:
    def __init__(self, sessao: Session) -> None:
        self.sessao = sessao

    def adicionar(self, previsao: Previsao) -> Previsao:
        self.sessao.add(previsao)
        self.sessao.flush()
        return previsao

    def ultima_para(self, data_alvo: date, criada_depois_de: datetime) -> Previsao | None:
        return self.sessao.scalar(
            select(Previsao)
            .where(Previsao.data_alvo == data_alvo, Previsao.criada_em >= criada_depois_de)
            .order_by(Previsao.criada_em.desc())
            .limit(1)
        )

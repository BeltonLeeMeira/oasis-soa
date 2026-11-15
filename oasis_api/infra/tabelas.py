"""Mapeamento das entidades do domínio para tabelas do PostgreSQL.

O formato das tabelas é criado e evoluído pelas migrações do Alembic (migrations/versions).
"""

from datetime import date, datetime

from sqlalchemy import JSON, BigInteger, Boolean, Date, DateTime, Enum, Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..dominio.enums import NivelRisco, OrigemAlerta, Perfil, StatusPonto, TipoPonto, valores
from .banco import Base


def _enum(enum_cls, tamanho: int = 20) -> Enum:
    # Grava o texto do enum (ex.: "Agua") numa coluna VARCHAR; a migração cria o CHECK.
    return Enum(enum_cls, native_enum=False, length=tamanho, values_callable=valores, validate_strings=True)


class Usuario(Base):
    """Cidadão que usa o app. Sem CPF, telefone ou endereço: só o necessário."""

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    apelido: Mapped[str] = mapped_column(String(40))
    perfil: Mapped[Perfil] = mapped_column(_enum(Perfil))
    bairro: Mapped[str] = mapped_column(String(60))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PontoApoio(Base):
    """Lugar com água, sombra ou ambiente climatizado aberto ao público."""

    __tablename__ = "pontos_apoio"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(80))
    tipo: Mapped[TipoPonto] = mapped_column(_enum(TipoPonto))
    endereco: Mapped[str] = mapped_column(String(120))
    bairro: Mapped[str] = mapped_column(String(60))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    horario: Mapped[str | None] = mapped_column(String(60))
    status: Mapped[StatusPonto] = mapped_column(
        _enum(StatusPonto), default=StatusPonto.PENDENTE, server_default=StatusPonto.PENDENTE.value
    )
    criado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    avaliado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_pontos_apoio_bairro", "bairro"),
        Index("ix_pontos_apoio_status", "status"),
    )


class Estacao(Base):
    """Estação de medição (ESP32 + DHT22) instalada num ponto do bairro."""

    __tablename__ = "estacoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True)
    nome: Mapped[str] = mapped_column(String(80))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    ativa: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class Leitura(Base):
    """Uma medição de temperatura e umidade, com o índice de calor calculado pela API."""

    __tablename__ = "leituras"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    estacao_id: Mapped[int] = mapped_column(ForeignKey("estacoes.id", ondelete="CASCADE"))
    temperatura: Mapped[float] = mapped_column(Float)
    umidade: Mapped[float] = mapped_column(Float)
    indice_calor: Mapped[float] = mapped_column(Float)
    nivel: Mapped[NivelRisco] = mapped_column(_enum(NivelRisco))
    recebida_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    estacao: Mapped[Estacao] = relationship(lazy="joined")

    __table_args__ = (Index("ix_leituras_estacao_recebida", "estacao_id", "recebida_em"),)


class Alerta(Base):
    """Aviso de risco: aberto por uma leitura da estação ou pela previsão do modelo."""

    __tablename__ = "alertas"

    id: Mapped[int] = mapped_column(primary_key=True)
    estacao_id: Mapped[int | None] = mapped_column(ForeignKey("estacoes.id", ondelete="SET NULL"))
    nivel: Mapped[NivelRisco] = mapped_column(_enum(NivelRisco))
    origem: Mapped[OrigemAlerta] = mapped_column(_enum(OrigemAlerta))
    mensagem: Mapped[str] = mapped_column(String(200))
    data_alvo: Mapped[date | None] = mapped_column(Date)
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fim: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    estacao: Mapped[Estacao | None] = relationship(lazy="joined")

    __table_args__ = (Index("ix_alertas_fim", "fim"),)


class Previsao(Base):
    """Resultado do modelo de IA para o dia seguinte."""

    __tablename__ = "previsoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    data_alvo: Mapped[date] = mapped_column(Date, index=True)
    probabilidade: Mapped[float] = mapped_column(Float)
    risco: Mapped[bool] = mapped_column(Boolean)
    versao_modelo: Mapped[str] = mapped_column(String(40))
    leituras_usadas: Mapped[int] = mapped_column(Integer)
    atributos: Mapped[dict[str, float]] = mapped_column(JSON)
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

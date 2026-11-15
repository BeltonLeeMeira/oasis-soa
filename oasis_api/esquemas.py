"""Formatos de entrada e saída da API (DTOs).

Os campos são snake_case no Python e camelCase no JSON (ex.: criado_em -> criadoEm).
Datas e horas saem no horário de Brasília, com o fuso explícito (-03:00).
"""

from datetime import date, datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, model_validator
from pydantic.alias_generators import to_camel

from .dominio.enums import NivelRisco, OrigemAlerta, Perfil, StatusPonto, TipoPonto

FUSO = ZoneInfo("America/Sao_Paulo")
PADRAO_CODIGO_ESTACAO = r"^EST-[A-Z]{2}-\d{2}$"

DataHora = Annotated[datetime, PlainSerializer(lambda d: d.astimezone(FUSO).isoformat(timespec="seconds"), return_type=str)]


class Esquema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
        from_attributes=True,
        str_strip_whitespace=True,
        allow_inf_nan=False,
    )


# ----------------------------------------------------------------- usuários ---


class UsuarioCriar(Esquema):
    apelido: str = Field(min_length=2, max_length=40, examples=["Dona Cida"])
    perfil: Perfil
    bairro: str = Field(min_length=2, max_length=60, examples=["Vila Mariana"])


class UsuarioSaida(Esquema):
    id: int
    apelido: str
    perfil: Perfil
    bairro: str
    criado_em: DataHora


# ------------------------------------------------------------------- pontos ---


class PontoCriar(Esquema):
    nome: str = Field(min_length=3, max_length=80, examples=["Bebedouro da praça"])
    tipo: TipoPonto
    endereco: str = Field(min_length=3, max_length=120, examples=["Rua Exemplo, 100"])
    bairro: str = Field(min_length=2, max_length=60, examples=["Vila Mariana"])
    latitude: float = Field(ge=-90, le=90, examples=[-23.5891])
    longitude: float = Field(ge=-180, le=180, examples=[-46.6346])
    horario: str | None = Field(default=None, max_length=60, examples=["6h às 22h"])
    criado_por_id: int | None = Field(default=None, ge=1)


class PontoSaida(Esquema):
    id: int
    nome: str
    tipo: TipoPonto
    endereco: str
    bairro: str
    latitude: float
    longitude: float
    horario: str | None
    status: StatusPonto
    criado_em: DataHora
    distancia_metros: int | None = None


class StatusAlterar(Esquema):
    status: StatusPonto


# ----------------------------------------------------------------- estações ---


class EstacaoCriar(Esquema):
    codigo: str = Field(pattern=PADRAO_CODIGO_ESTACAO, examples=["EST-VM-02"])
    nome: str = Field(min_length=3, max_length=80)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    ativa: bool = True


class EstacaoSaida(Esquema):
    id: int
    codigo: str
    nome: str
    latitude: float
    longitude: float
    ativa: bool


# ----------------------------------------------------------------- leituras ---


class LeituraCriar(Esquema):
    """As faixas de temperatura e umidade são checadas pela regra do domínio."""

    codigo: str = Field(pattern=PADRAO_CODIGO_ESTACAO, examples=["EST-VM-01"])
    temperatura: float = Field(examples=[34.0])
    umidade: float = Field(examples=[55.0])


class LeituraSaida(Esquema):
    id: int
    estacao_id: int
    temperatura: float
    umidade: float
    indice_calor: float
    nivel: NivelRisco
    recebida_em: DataHora


class LeituraRegistradaSaida(LeituraSaida):
    acao_alerta: str


class RiscoSaida(Esquema):
    estacao: str
    nome: str
    temperatura: float | None
    umidade: float | None
    indice_calor: float | None
    nivel: NivelRisco | None
    recebida_em: DataHora | None
    atualizada: bool


class AlertaSaida(Esquema):
    id: int
    estacao: str | None
    nivel: NivelRisco
    origem: OrigemAlerta
    mensagem: str
    data_alvo: date | None
    inicio: DataHora
    fim: DataHora | None


# ---------------------------------------------------------------- previsões ---


class PrevisaoSaida(Esquema):
    data_alvo: date
    probabilidade: float
    risco: bool
    limiar: float
    versao_modelo: str
    leituras_usadas: int
    atributos: dict[str, float]


class SimulacaoEntrada(Esquema):
    """Resumo de um dia digitado à mão, para testar o modelo sem estação."""

    temp_max: float = Field(ge=-10, le=60, examples=[33.5])
    temp_min: float = Field(ge=-10, le=60, examples=[21.0])
    temp_media: float = Field(ge=-10, le=60, examples=[26.8])
    umid_media: float = Field(ge=0, le=100, examples=[58.0])
    umid_min: float = Field(ge=0, le=100, examples=[35.0])
    ic_max: float = Field(ge=-20, le=80, examples=[34.2])
    data_alvo: date | None = None

    @model_validator(mode="after")
    def coerente(self) -> "SimulacaoEntrada":
        if not self.temp_min <= self.temp_media <= self.temp_max:
            raise ValueError("Use tempMin <= tempMedia <= tempMax.")
        if self.umid_min > self.umid_media:
            raise ValueError("Use umidMin <= umidMedia.")
        return self


# -------------------------------------------------------------------- saúde ---


class SaudeSaida(Esquema):
    status: str
    banco: str
    mqtt: str
    modelo: str
    leituras_mqtt_aceitas: int
    leituras_mqtt_rejeitadas: int


# -------------------------------------------------------------------- erros ---


class ErroCampo(BaseModel):
    campo: str
    mensagem: str


class Problema(BaseModel):
    """Formato padrão de erro (RFC 9457, Problem Details)."""

    type: str = "about:blank"
    title: str
    status: int
    detail: str
    erros: list[ErroCampo] = []

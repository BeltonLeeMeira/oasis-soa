"""Regras de negócio puras: não acessam banco, rede nem HTTP.

Por serem funções simples, são testadas direto em tests/test_dominio.py.
"""

import math
from datetime import date
from enum import StrEnum
from statistics import fmean
from typing import Sequence

from .enums import NivelRisco, StatusPonto
from .erros import RegraVioladaErro
from .indice_calor import indice_calor_exato

# ---------------------------------------------------------------- leituras ---

TEMPERATURA_MIN, TEMPERATURA_MAX = -10.0, 60.0
UMIDADE_MIN, UMIDADE_MAX = 0.0, 100.0


def validar_leitura(temperatura: float, umidade: float) -> None:
    """Rejeita leituras fisicamente impossíveis (sensor com defeito ou dado forjado)."""
    if not TEMPERATURA_MIN <= temperatura <= TEMPERATURA_MAX:
        raise RegraVioladaErro(
            f"Temperatura fora da faixa aceita ({TEMPERATURA_MIN:g} a {TEMPERATURA_MAX:g} °C).",
            campo="temperatura",
        )
    if not UMIDADE_MIN <= umidade <= UMIDADE_MAX:
        raise RegraVioladaErro("Umidade fora da faixa aceita (0 a 100%).", campo="umidade")


# ----------------------------------------------------------------- alertas ---


class AcaoAlerta(StrEnum):
    ABRIR = "Abrir"
    ESCALAR = "Escalar"
    MANTER = "Manter"
    FECHAR = "Fechar"
    NENHUMA = "Nenhuma"


def decidir_alerta(nivel_leitura: NivelRisco, nivel_alerta_ativo: NivelRisco | None) -> AcaoAlerta:
    """Decide o que fazer com o alerta de sensor de uma estação após uma nova leitura.

    - Abre quando a leitura chega a Alerta ou Perigo e não há alerta ativo.
    - Escala quando o alerta ativo é Alerta e a leitura chega a Perigo.
    - Fecha quando a leitura volta abaixo de Alerta.
    """
    em_risco = nivel_leitura.ordem >= NivelRisco.ALERTA.ordem
    if nivel_alerta_ativo is None:
        return AcaoAlerta.ABRIR if em_risco else AcaoAlerta.NENHUMA
    if not em_risco:
        return AcaoAlerta.FECHAR
    if nivel_leitura.ordem > nivel_alerta_ativo.ordem:
        return AcaoAlerta.ESCALAR
    return AcaoAlerta.MANTER


def mensagem_alerta_sensor(nivel: NivelRisco, indice_c: float, local: str) -> str:
    """Texto curto e em linguagem simples, pensado para quem vai ler no celular."""
    indice = f"{indice_c:.1f}".replace(".", ",")
    if nivel is NivelRisco.PERIGO:
        conselho = "Evite o sol, beba água e procure um lugar fresco."
    else:
        conselho = "Beba água e procure sombra."
    return f"{nivel.value}: sensação de {indice} °C em {local}. {conselho}"


def mensagem_alerta_previsao(data_alvo: date, probabilidade: float) -> str:
    dia = data_alvo.strftime("%d/%m")
    chance = min(probabilidade, 0.99)  # nunca prometer 100%
    return f"Amanhã ({dia}) pode ser dia de calor forte: {chance:.0%} de chance. Planeje água e sombra."


# ------------------------------------------------------------------ pontos ---

# Retângulo que contém a cidade de São Paulo (aproximado).
LATITUDE_SP = (-24.01, -23.35)
LONGITUDE_SP = (-46.83, -46.36)


def validar_localizacao_sp(latitude: float, longitude: float) -> None:
    """Pontos de apoio só podem ser cadastrados dentro da cidade de São Paulo."""
    if not (LATITUDE_SP[0] <= latitude <= LATITUDE_SP[1] and LONGITUDE_SP[0] <= longitude <= LONGITUDE_SP[1]):
        raise RegraVioladaErro("O ponto precisa ficar dentro da cidade de São Paulo.", campo="latitude")


TRANSICOES_STATUS: dict[StatusPonto, set[StatusPonto]] = {
    StatusPonto.PENDENTE: {StatusPonto.APROVADO, StatusPonto.REJEITADO},
    StatusPonto.APROVADO: {StatusPonto.REJEITADO},
    StatusPonto.REJEITADO: {StatusPonto.APROVADO},
}


def validar_transicao_status(atual: StatusPonto, novo: StatusPonto) -> None:
    """Só o posto muda o status, e só por caminhos permitidos (ex.: nada volta a Pendente)."""
    if novo not in TRANSICOES_STATUS[atual]:
        raise RegraVioladaErro(f"Não é possível mudar o ponto de {atual.value} para {novo.value}.", campo="status")


def distancia_metros(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distância em linha reta entre dois pontos (fórmula de haversine)."""
    raio = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * raio * math.asin(math.sqrt(a))


# --------------------------------------------------------------- previsão ---

# Mesmos nomes e mesma ordem usados no treino do notebook (oasis_risco_calor.ipynb, no repositório oasis-ia-ml).
ATRIBUTOS_MODELO = [
    "temp_max",
    "temp_min",
    "temp_media",
    "umid_media",
    "umid_min",
    "ic_max",
    "dia_sen",
    "dia_cos",
]


def sazonalidade(data_alvo: date) -> tuple[float, float]:
    """Dia do ano como um ponto no círculo, para dezembro ficar perto de janeiro."""
    angulo = 2 * math.pi * data_alvo.timetuple().tm_yday / 365.25
    return math.sin(angulo), math.cos(angulo)


def atributos_do_dia(leituras: Sequence[tuple[float, float]], data_alvo: date) -> dict[str, float]:
    """Resume as leituras (temperatura, umidade) de hoje nos atributos do modelo.

    É a mesma conta que o notebook faz com os dados horários do INMET.
    """
    if not leituras:
        raise RegraVioladaErro("É preciso ao menos uma leitura para calcular os atributos.")
    temperaturas = [t for t, _ in leituras]
    umidades = [u for _, u in leituras]
    sen, cos = sazonalidade(data_alvo)
    return {
        "temp_max": max(temperaturas),
        "temp_min": min(temperaturas),
        "temp_media": fmean(temperaturas),
        "umid_media": fmean(umidades),
        "umid_min": min(umidades),
        "ic_max": max(indice_calor_exato(t, u) for t, u in leituras),
        "dia_sen": sen,
        "dia_cos": cos,
    }

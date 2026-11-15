"""Índice de calor (sensação térmica) e nível de risco.

Fórmula: regressão de Rothfusz usada pelo serviço meteorológico dos EUA (NOAA/NWS),
calculada em °F e convertida para °C.
https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml

Faixas de risco: tabela do NWS (https://www.weather.gov/ama/HeatIndex),
convertidas para °C e arredondadas: 27, 32 e 39 °C.

A mesma fórmula existe no notebook de IA (Python) e na estação ESP32 (C++).
Os três passam nos mesmos casos de teste.
"""

import math

from .enums import NivelRisco

LIMITE_ATENCAO = 27.0
LIMITE_ALERTA = 32.0
LIMITE_PERIGO = 39.0


def indice_calor_exato(temperatura_c: float, umidade: float) -> float:
    """Índice de calor em °C, sem arredondar."""
    t = temperatura_c * 9 / 5 + 32
    rh = umidade

    # 1) Fórmula simples de Steadman. Vale enquanto a média dela com a temperatura
    #    ficar abaixo de 80 °F.
    simples = 0.5 * (t + 61.0 + (t - 68.0) * 1.2 + rh * 0.094)
    if (simples + t) / 2 < 80:
        hi = simples
    else:
        # 2) Regressão completa de Rothfusz.
        hi = (
            -42.379
            + 2.04901523 * t
            + 10.14333127 * rh
            - 0.22475541 * t * rh
            - 0.00683783 * t * t
            - 0.05481717 * rh * rh
            + 0.00122874 * t * t * rh
            + 0.00085282 * t * rh * rh
            - 0.00000199 * t * t * rh * rh
        )
        # 3) Ajustes para umidade muito baixa ou muito alta.
        if rh < 13 and 80 <= t <= 112:
            hi -= ((13 - rh) / 4) * math.sqrt((17 - abs(t - 95)) / 17)
        elif rh > 85 and 80 <= t <= 87:
            hi += ((rh - 85) / 10) * ((87 - t) / 5)

    return (hi - 32) * 5 / 9


def indice_calor_c(temperatura_c: float, umidade: float) -> float:
    """Índice de calor em °C com uma casa decimal (o valor que gravamos e mostramos)."""
    return round(indice_calor_exato(temperatura_c, umidade), 1)


def classificar(indice_c: float) -> NivelRisco:
    """Converte o índice de calor no nível de risco."""
    if indice_c >= LIMITE_PERIGO:
        return NivelRisco.PERIGO
    if indice_c >= LIMITE_ALERTA:
        return NivelRisco.ALERTA
    if indice_c >= LIMITE_ATENCAO:
        return NivelRisco.ATENCAO
    return NivelRisco.NORMAL

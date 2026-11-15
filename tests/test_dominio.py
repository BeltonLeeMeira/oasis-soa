"""Regras puras do domínio (não precisam de banco)."""

from datetime import date

import pytest

from oasis_api.dominio.enums import NivelRisco, StatusPonto
from oasis_api.dominio.erros import RegraVioladaErro
from oasis_api.dominio.indice_calor import classificar, indice_calor_c
from oasis_api.dominio.regras import (
    AcaoAlerta,
    atributos_do_dia,
    decidir_alerta,
    distancia_metros,
    validar_leitura,
    validar_localizacao_sp,
    validar_transicao_status,
)

# Mesmos casos usados no notebook (Python) e na estação ESP32 (C++).
CASOS_INDICE = [
    (24, 50, 23.8, NivelRisco.NORMAL),  # fórmula simples
    (28, 60, 29.4, NivelRisco.ATENCAO),  # regressão
    (31, 50, 32.6, NivelRisco.ALERTA),
    (34, 55, 40.2, NivelRisco.PERIGO),
    (29, 90, 37.2, NivelRisco.ALERTA),  # ajuste de umidade alta
    (38, 10, 34.7, NivelRisco.ALERTA),  # ajuste de umidade baixa
]


@pytest.mark.parametrize(("temperatura", "umidade", "esperado", "nivel"), CASOS_INDICE)
def test_indice_de_calor_e_nivel(temperatura, umidade, esperado, nivel):
    indice = indice_calor_c(temperatura, umidade)
    assert indice == pytest.approx(esperado, abs=0.1)
    assert classificar(indice) is nivel


@pytest.mark.parametrize(
    ("indice", "nivel"),
    [(26.9, NivelRisco.NORMAL), (27.0, NivelRisco.ATENCAO), (31.9, NivelRisco.ATENCAO), (32.0, NivelRisco.ALERTA), (39.0, NivelRisco.PERIGO)],
)
def test_limites_das_faixas(indice, nivel):
    assert classificar(indice) is nivel


@pytest.mark.parametrize(("temperatura", "umidade"), [(-11, 50), (61, 50), (25, -1), (25, 101)])
def test_leitura_fora_da_faixa(temperatura, umidade):
    with pytest.raises(RegraVioladaErro):
        validar_leitura(temperatura, umidade)


@pytest.mark.parametrize(
    ("leitura", "ativo", "acao"),
    [
        (NivelRisco.ATENCAO, None, AcaoAlerta.NENHUMA),
        (NivelRisco.ALERTA, None, AcaoAlerta.ABRIR),
        (NivelRisco.PERIGO, NivelRisco.ALERTA, AcaoAlerta.ESCALAR),
        (NivelRisco.ALERTA, NivelRisco.PERIGO, AcaoAlerta.MANTER),
        (NivelRisco.ALERTA, NivelRisco.ALERTA, AcaoAlerta.MANTER),
        (NivelRisco.ATENCAO, NivelRisco.PERIGO, AcaoAlerta.FECHAR),
    ],
)
def test_decisao_do_alerta(leitura, ativo, acao):
    assert decidir_alerta(leitura, ativo) is acao


def test_transicoes_de_status():
    validar_transicao_status(StatusPonto.PENDENTE, StatusPonto.APROVADO)
    validar_transicao_status(StatusPonto.APROVADO, StatusPonto.REJEITADO)
    with pytest.raises(RegraVioladaErro):
        validar_transicao_status(StatusPonto.APROVADO, StatusPonto.PENDENTE)


def test_localizacao_dentro_e_fora_de_sp():
    validar_localizacao_sp(-23.5891, -46.6346)  # Vila Mariana
    with pytest.raises(RegraVioladaErro):
        validar_localizacao_sp(-22.9068, -43.1729)  # Rio de Janeiro


def test_distancia_aproximada():
    # Do SESC Vila Mariana ao Parque Ibirapuera: cerca de 2,3 km em linha reta.
    assert distancia_metros(-23.5893, -46.6352, -23.5874, -46.6576) == pytest.approx(2290, rel=0.05)


def test_atributos_do_dia():
    atributos = atributos_do_dia([(30.0, 50.0), (34.0, 55.0), (24.0, 80.0)], date(2027, 1, 15))
    assert atributos["temp_max"] == 34.0
    assert atributos["temp_min"] == 24.0
    assert atributos["umid_min"] == 50.0
    assert atributos["ic_max"] == pytest.approx(40.2, abs=0.1)
    assert -1 <= atributos["dia_sen"] <= 1 and -1 <= atributos["dia_cos"] <= 1

"""Evidências dos controles de segurança (usadas no relatório de Cybersecurity)."""

import pytest
from sqlalchemy import text

TENTATIVAS_SQLI = [
    "' OR '1'='1",
    "' OR 1=1 --",
    "'; DROP TABLE pontos_apoio; --",
    "%' UNION SELECT id, apelido, perfil, bairro FROM usuarios --",
    "\\' OR \\'1\\'=\\'1",
]


@pytest.mark.parametrize("ataque", TENTATIVAS_SQLI)
def test_sql_injection_na_busca_nao_tem_efeito(cliente, fabrica_sessoes, ataque):
    resposta = cliente.get("/api/pontos", params={"busca": ataque})
    # O texto é tratado como valor (parâmetro vinculado): nenhum ponto tem esse nome.
    assert resposta.status_code == 200 and resposta.json() == []
    with fabrica_sessoes() as sessao:  # e a tabela continua lá, intacta
        assert sessao.execute(text("SELECT count(*) FROM pontos_apoio")).scalar() == 3


def test_busca_com_coringa_do_like_e_texto_comum(cliente):
    # '%' sozinho não pode virar "traga tudo".
    assert cliente.get("/api/pontos", params={"busca": "%"}).json() == []
    assert [p["nome"] for p in cliente.get("/api/pontos", params={"busca": "sesc"}).json()] == ["SESC Vila Mariana"]


@pytest.mark.parametrize(
    "caminho",
    [
        "/../../etc/passwd",
        "/..%2f..%2f..%2fetc%2fpasswd",
        "/%2e%2e/%2e%2e/etc/passwd",
        "/..\\..\\windows\\win.ini",
        "/estilo.css/../../oasis_api/config.py",
        "/....//....//etc/passwd",
    ],
)
def test_lfi_path_traversal_na_pagina_publica(cliente, caminho):
    resposta = cliente.get(caminho)
    assert resposta.status_code == 404
    assert "root:" not in resposta.text and "OASIS_" not in resposta.text


def test_cabecalhos_de_seguranca(cliente):
    cabecalhos = cliente.get("/").headers
    assert cabecalhos["x-content-type-options"] == "nosniff"
    assert cabecalhos["x-frame-options"] == "DENY"
    assert "default-src 'self'" in cabecalhos["content-security-policy"]


def test_chave_errada_e_negada_e_registrada(cliente, caplog):
    with caplog.at_level("WARNING", logger="oasis.seguranca"):
        resposta = cliente.patch("/api/pontos/1/status", json={"status": "Rejeitado"}, headers={"X-Chave-Posto": "chute"})
    assert resposta.status_code == 401
    assert "Acesso negado" in caplog.text


def test_erros_nao_vazam_detalhes_internos(cliente):
    resposta = cliente.post("/api/usuarios", content=b"{json quebrado", headers={"Content-Type": "application/json"})
    assert resposta.status_code == 400
    assert "Traceback" not in resposta.text and "sqlalchemy" not in resposta.text.lower()


def test_nan_e_infinito_sao_recusados(cliente):
    resposta = cliente.post("/api/previsoes/simular", content=b'{"tempMax": NaN, "tempMin": 1, "tempMedia": 1, "umidMedia": 1, "umidMin": 1, "icMax": 1}', headers={"Content-Type": "application/json"})
    assert resposta.status_code == 400

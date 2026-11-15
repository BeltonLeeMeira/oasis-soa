"""Configuração dos testes: banco oasis_teste, migrações aplicadas do zero e dados mínimos por teste.

Rodar (com o PostgreSQL ligado e o banco oasis_teste criado):
    pytest -v
"""

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from fastapi.testclient import TestClient
from sqlalchemy import text

PASTA_API = Path(__file__).resolve().parent.parent
URL_TESTE = os.environ.get("OASIS_TESTE_DATABASE_URL", "postgresql+psycopg://oasis:oasis_dev@localhost:5432/oasis_teste")
CHAVE_POSTO = "chave-de-teste-do-posto"
CHAVE_HMAC = "chave-hmac-de-teste"

# As variáveis valem para o Alembic e para a API criados dentro dos testes.
os.environ["OASIS_DATABASE_URL"] = URL_TESTE
os.environ["OASIS_ENV_FILE"] = str(PASTA_API / "nao-existe.env")

from oasis_api.config import Config  # noqa: E402
from oasis_api.dominio.enums import StatusPonto, TipoPonto  # noqa: E402
from oasis_api.infra.banco import criar_engine, criar_fabrica_sessoes  # noqa: E402
from oasis_api.infra.tabelas import Estacao, PontoApoio  # noqa: E402
from oasis_api.main import criar_app  # noqa: E402

TABELAS = "previsoes, alertas, leituras, pontos_apoio, estacoes, usuarios"


@pytest.fixture(scope="session")
def banco_migrado():
    """Aplica as migrações do zero: também prova que downgrade e upgrade funcionam."""
    cfg = AlembicConfig(str(PASTA_API / "alembic.ini"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture
def config(tmp_path) -> Config:
    return Config(
        database_url=URL_TESTE,
        chave_posto=CHAVE_POSTO,
        mqtt_habilitado=False,
        mqtt_hmac_chave=CHAVE_HMAC,
        mqtt_prefixo="oasis-teste",
        mqtt_host="localhost",
    )


@pytest.fixture
def fabrica_sessoes(banco_migrado):
    engine = criar_engine(URL_TESTE)
    with engine.begin() as conexao:
        conexao.execute(text(f"TRUNCATE {TABELAS} RESTART IDENTITY CASCADE"))
    fabrica = criar_fabrica_sessoes(engine)
    with fabrica() as sessao:
        sessao.add(Estacao(codigo="EST-VM-01", nome="Vila Mariana", latitude=-23.5891, longitude=-46.6346, ativa=True))
        sessao.add(Estacao(codigo="EST-VM-09", nome="Estação desligada", latitude=-23.59, longitude=-46.63, ativa=False))
        sessao.add(
            PontoApoio(
                nome="SESC Vila Mariana", tipo=TipoPonto.CLIMATIZADO, endereco="Rua Pelotas, 141", bairro="Vila Mariana",
                latitude=-23.5893, longitude=-46.6352, horario="10h às 21h", status=StatusPonto.APROVADO,
            )
        )
        sessao.add(
            PontoApoio(
                nome="Parque Ibirapuera", tipo=TipoPonto.SOMBRA, endereco="Av. Pedro Álvares Cabral", bairro="Vila Mariana",
                latitude=-23.5874, longitude=-46.6576, horario=None, status=StatusPonto.APROVADO,
            )
        )
        sessao.add(
            PontoApoio(
                nome="Bebedouro sem revisão", tipo=TipoPonto.AGUA, endereco="Rua Exemplo, 1", bairro="Vila Mariana",
                latitude=-23.5890, longitude=-46.6347, horario=None, status=StatusPonto.PENDENTE,
            )
        )
        sessao.commit()
    yield fabrica
    engine.dispose()


@pytest.fixture
def cliente(config, fabrica_sessoes):
    app = criar_app(config)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def posto():
    return {"X-Chave-Posto": CHAVE_POSTO}

"""Ponto de entrada da API Oásis.

Para rodar:  uvicorn oasis_api.main:criar_app --factory --port 8000
Documentação interativa: http://localhost:8000/docs   Página pública: http://localhost:8000/
"""

import logging
import logging.handlers
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import CHAVE_POSTO_PADRAO, Config, carregar_config
from .erros_http import registrar_erros
from .infra.banco import criar_engine, criar_fabrica_sessoes
from .infra.modelo_ml import ModeloRisco
from .infra.mqtt_coletor import ColetorMqtt
from .rotas import ROTEADORES
from .seguranca import cabecalhos_seguranca

PASTA_WEB = Path(__file__).resolve().parent / "web"
log = logging.getLogger("oasis")

DESCRICAO = """
Backend da CitizenTech **Oásis**: avisa idosos e trabalhadores de rua de São Paulo
quando o calor vira risco e mostra onde há água e sombra por perto.

- **Pontos de apoio**: o app sugere, o posto aprova (cabeçalho `X-Chave-Posto`).
- **Leituras**: chegam das estações ESP32 pelo MQTT (ou por HTTP nos testes).
- **Risco e alertas**: índice de calor da NOAA e faixas do NWS.
- **Previsão**: modelo treinado com dados do INMET (ver o repositório `oasis-ia-ml`).
"""


def configurar_logs(config: Config) -> None:
    raiz = logging.getLogger("oasis")
    if raiz.handlers:
        return
    formato = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(formato)
    raiz.addHandler(console)
    if config.log_arquivo:
        config.log_arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo = logging.handlers.RotatingFileHandler(config.log_arquivo, maxBytes=5_000_000, backupCount=5, encoding="utf-8")
        arquivo.setFormatter(formato)
        raiz.addHandler(arquivo)
    raiz.setLevel(logging.INFO)


def criar_app(config: Config | None = None) -> FastAPI:
    config = config or carregar_config()
    configurar_logs(config)

    engine = criar_engine(config.database_url)
    fabrica_sessoes = criar_fabrica_sessoes(engine)
    modelo = ModeloRisco(config.modelo_dir)
    coletor = ColetorMqtt(config, fabrica_sessoes)

    @asynccontextmanager
    async def ciclo_de_vida(_app: FastAPI):
        if config.chave_posto == CHAVE_POSTO_PADRAO:
            log.warning("OASIS_CHAVE_POSTO está com o valor padrão: troque antes de publicar.")
        if config.mqtt_habilitado:
            coletor.iniciar()
        log.info("API Oásis no ar")
        yield
        coletor.parar()
        engine.dispose()
        log.info("API Oásis encerrada")

    docs = config.docs_habilitada
    app = FastAPI(
        title="Oásis API",
        version="1.0.0",
        description=DESCRICAO,
        lifespan=ciclo_de_vida,
        docs_url="/docs" if docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if docs else None,
    )
    app.state.config = config
    app.state.engine = engine
    app.state.fabrica_sessoes = fabrica_sessoes
    app.state.modelo = modelo
    app.state.coletor = coletor

    registrar_erros(app)
    app.middleware("http")(cabecalhos_seguranca)
    for roteador in ROTEADORES:
        app.include_router(roteador)
    # Página pública (a "aplicação web" hospedada no IIS). Fica por último para não cobrir as rotas da API.
    app.mount("/", StaticFiles(directory=PASTA_WEB, html=True), name="web")
    return app

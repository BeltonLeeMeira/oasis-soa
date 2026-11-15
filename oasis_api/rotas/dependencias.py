"""Dependências compartilhadas pelas rotas (injeção de dependência do FastAPI)."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from ..config import Config
from ..infra.modelo_ml import ModeloRisco


def obter_sessao(request: Request) -> Iterator[Session]:
    """Uma sessão do banco por requisição; o 'with' fecha (e desfaz o que não teve commit)."""
    with request.app.state.fabrica_sessoes() as sessao:
        yield sessao


def obter_config(request: Request) -> Config:
    return request.app.state.config


def obter_modelo(request: Request) -> ModeloRisco:
    return request.app.state.modelo


SessaoDep = Annotated[Session, Depends(obter_sessao)]
ConfigDep = Annotated[Config, Depends(obter_config)]
ModeloDep = Annotated[ModeloRisco, Depends(obter_modelo)]

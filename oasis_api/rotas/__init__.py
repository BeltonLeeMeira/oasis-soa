"""Camada HTTP: cada módulo agrupa as rotas de um recurso."""

from . import estacoes, pontos, previsoes, risco, saude, usuarios

ROTEADORES = [usuarios.router, pontos.router, estacoes.router, risco.router, previsoes.router, saude.router]

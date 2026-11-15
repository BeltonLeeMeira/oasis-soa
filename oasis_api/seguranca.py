"""Controles de segurança da camada HTTP."""

import hmac
import logging
from typing import Annotated

from fastapi import Header, Request

from .erros_http import AcessoNegadoErro

log = logging.getLogger("oasis.seguranca")


def chave_posto_valida(request: Request, chave: str | None) -> bool:
    esperada = request.app.state.config.chave_posto
    # compare_digest leva o mesmo tempo para qualquer chave errada (evita adivinhar pelo tempo de resposta).
    return chave is not None and hmac.compare_digest(chave.encode(), esperada.encode())


def exigir_chave_posto(request: Request, x_chave_posto: Annotated[str | None, Header()] = None) -> None:
    """Dependência das rotas exclusivas do posto. Toda tentativa negada fica no log (auditoria)."""
    if not chave_posto_valida(request, x_chave_posto):
        origem = request.client.host if request.client else "desconhecida"
        log.warning("Acesso negado: %s %s (origem %s)", request.method, request.url.path, origem)
        raise AcessoNegadoErro()


ROTAS_DOCUMENTACAO = ("/docs", "/redoc", "/openapi.json")
POLITICA_CONTEUDO = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
)


async def cabecalhos_seguranca(request: Request, chamar_proximo):
    """Cabeçalhos que endurecem o navegador contra sniffing, clickjacking e scripts de terceiros."""
    resposta = await chamar_proximo(request)
    resposta.headers.setdefault("X-Content-Type-Options", "nosniff")
    resposta.headers.setdefault("X-Frame-Options", "DENY")
    resposta.headers.setdefault("Referrer-Policy", "no-referrer")
    if not request.url.path.startswith(ROTAS_DOCUMENTACAO):
        resposta.headers.setdefault("Content-Security-Policy", POLITICA_CONTEUDO)
    return resposta

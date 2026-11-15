"""Traduz erros em respostas HTTP no formato Problem Details (application/problem+json).

Nenhuma resposta de erro mostra stack trace ou detalhes internos: o detalhe vai só para o log.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .dominio.erros import (
    ConflitoErro,
    ErroDominio,
    IndisponivelErro,
    NaoEncontradoErro,
    RegraVioladaErro,
    SemDadosErro,
)
from .esquemas import ErroCampo, Problema

log = logging.getLogger("oasis.erros")


class AcessoNegadoErro(Exception):
    """Chave do posto ausente ou errada."""


STATUS_POR_ERRO: list[tuple[type[ErroDominio], int, str]] = [
    (NaoEncontradoErro, 404, "Não encontrado"),
    (ConflitoErro, 409, "Conflito"),
    (SemDadosErro, 422, "Dados insuficientes"),
    (IndisponivelErro, 503, "Serviço indisponível"),
    (RegraVioladaErro, 400, "Regra de negócio violada"),
]


def _mensagem(erro: dict) -> str:
    """Mensagens de validação em português simples (o app mostra estes textos)."""
    tipo, ctx = erro.get("type", ""), erro.get("ctx", {}) or {}
    traducoes = {
        "missing": "Campo obrigatório.",
        "string_too_short": f"Use pelo menos {ctx.get('min_length')} caracteres.",
        "string_too_long": f"Use no máximo {ctx.get('max_length')} caracteres.",
        "string_pattern_mismatch": "Formato inválido.",
        "greater_than_equal": f"Deve ser maior ou igual a {ctx.get('ge')}.",
        "less_than_equal": f"Deve ser menor ou igual a {ctx.get('le')}.",
        "float_parsing": "Informe um número.",
        "float_type": "Informe um número.",
        "int_parsing": "Informe um número inteiro.",
        "int_type": "Informe um número inteiro.",
        "finite_number": "Informe um número válido.",
        "bool_parsing": "Use true ou false.",
        "date_from_datetime_parsing": "Data inválida (use AAAA-MM-DD).",
        "date_parsing": "Data inválida (use AAAA-MM-DD).",
        "datetime_from_date_parsing": "Data e hora inválidas.",
        "json_invalid": "JSON inválido.",
        "enum": f"Valor inválido. Use: {ctx.get('expected')}.",
        "model_attributes_type": "Envie um objeto JSON.",
        "value_error": str(ctx.get("error", erro.get("msg", "Valor inválido."))),
    }
    return traducoes.get(tipo, erro.get("msg", "Valor inválido."))


def _campo(loc: tuple) -> str:
    partes = [str(p) for p in loc if p not in ("body", "query", "path", "header")]
    return ".".join(partes) or "corpo"


def _problema(status: int, titulo: str, detalhe: str, erros: list[ErroCampo] | None = None) -> JSONResponse:
    corpo = Problema(title=titulo, status=status, detail=detalhe, erros=erros or [])
    return JSONResponse(corpo.model_dump(), status_code=status, media_type="application/problem+json")


def registrar_erros(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _validacao(_request: Request, exc: RequestValidationError) -> JSONResponse:
        erros = [ErroCampo(campo=_campo(tuple(e.get("loc", ()))), mensagem=_mensagem(e)) for e in exc.errors()]
        return _problema(400, "Dados inválidos", "Confira os campos indicados em 'erros'.", erros)

    @app.exception_handler(ErroDominio)
    async def _dominio(_request: Request, exc: ErroDominio) -> JSONResponse:
        status, titulo = 400, "Requisição inválida"
        for classe, codigo, nome in STATUS_POR_ERRO:
            if isinstance(exc, classe):
                status, titulo = codigo, nome
                break
        erros = [ErroCampo(campo=exc.campo, mensagem=exc.mensagem)] if exc.campo else []
        return _problema(status, titulo, exc.mensagem, erros)

    @app.exception_handler(AcessoNegadoErro)
    async def _acesso(_request: Request, _exc: AcessoNegadoErro) -> JSONResponse:
        resposta = _problema(401, "Não autorizado", "Esta ação é exclusiva do posto: envie o cabeçalho X-Chave-Posto.")
        resposta.headers["WWW-Authenticate"] = 'ApiKey header="X-Chave-Posto"'
        return resposta

    @app.exception_handler(StarletteHTTPException)
    async def _http(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        titulos = {404: "Não encontrado", 405: "Método não permitido"}
        detalhe = "Recurso não encontrado." if exc.status_code == 404 else str(exc.detail)
        return _problema(exc.status_code, titulos.get(exc.status_code, "Erro"), detalhe)

    @app.exception_handler(Exception)
    async def _inesperado(request: Request, exc: Exception) -> JSONResponse:
        log.exception("Erro inesperado em %s %s", request.method, request.url.path)
        return _problema(500, "Erro interno", "Ocorreu um erro inesperado. Tente de novo em instantes.")

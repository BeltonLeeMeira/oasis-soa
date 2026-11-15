from typing import Annotated

from fastapi import APIRouter, Depends, Path

from ..esquemas import UsuarioCriar, UsuarioSaida
from ..seguranca import exigir_chave_posto
from ..servicos import UsuarioServico
from .dependencias import SessaoDep

router = APIRouter(prefix="/api/usuarios", tags=["Usuários"])


@router.post("", status_code=201, response_model=UsuarioSaida, summary="Identifica um cidadão no app")
def criar_usuario(dados: UsuarioCriar, sessao: SessaoDep):
    return UsuarioServico(sessao).criar(dados.apelido, dados.perfil, dados.bairro)


@router.get(
    "/{usuario_id}",
    response_model=UsuarioSaida,
    summary="Consulta um usuário (só o posto)",
    description="Pede `X-Chave-Posto`. Os ids são sequenciais: sem a chave, qualquer pessoa poderia "
    "percorrer 1, 2, 3... e montar uma lista de idosos por bairro (enumeração de usuários).",
    dependencies=[Depends(exigir_chave_posto)],
)
def obter_usuario(usuario_id: Annotated[int, Path(ge=1)], sessao: SessaoDep):
    return UsuarioServico(sessao).obter(usuario_id)

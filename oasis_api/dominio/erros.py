"""Erros do domínio. Não sabem nada de HTTP: a camada de rotas traduz cada um."""


class ErroDominio(Exception):
    """Base de todos os erros de regra de negócio."""

    def __init__(self, mensagem: str, campo: str | None = None) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.campo = campo


class RegraVioladaErro(ErroDominio):
    """O pedido é bem formado, mas quebra uma regra (ex.: ponto fora de São Paulo)."""


class NaoEncontradoErro(ErroDominio):
    """O recurso pedido não existe."""


class ConflitoErro(ErroDominio):
    """O recurso já existe (ex.: código de estação repetido)."""


class SemDadosErro(ErroDominio):
    """Ainda não há dados suficientes para responder (ex.: nenhuma leitura hoje)."""


class IndisponivelErro(ErroDominio):
    """Um componente necessário não está disponível (ex.: modelo de IA ausente)."""

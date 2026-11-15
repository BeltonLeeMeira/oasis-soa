"""Conexão com o PostgreSQL via SQLAlchemy.

O driver psycopg 3 envia o texto do SQL e os valores separados (parâmetros vinculados),
então nenhum valor digitado pelo usuário vira parte do comando SQL.
"""

from sqlalchemy import Engine, MetaData, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Nomes previsíveis para chaves e índices: as migrações usam exatamente estes nomes.
CONVENCAO_NOMES = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Classe base de todas as tabelas (ver infra/tabelas.py)."""

    metadata = MetaData(naming_convention=CONVENCAO_NOMES)


def criar_engine(url: str, echo: bool = False) -> Engine:
    # pool_pre_ping testa a conexão antes de usar: se o PostgreSQL reiniciou, reconecta sozinho.
    return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5, echo=echo)


def criar_fabrica_sessoes(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def banco_responde(engine: Engine) -> bool:
    try:
        with engine.connect() as conexao:
            conexao.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

"""Ambiente do Alembic: conecta no banco da configuração da API e aplica as migrações."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from oasis_api.config import carregar_config
from oasis_api.infra import tabelas  # noqa: F401  (registra as tabelas no metadata)
from oasis_api.infra.banco import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata
URL = carregar_config().database_url


def run_migrations_offline() -> None:
    """Gera o SQL sem conectar (alembic upgrade head --sql)."""
    context.configure(url=URL, target_metadata=target_metadata, literal_binds=True, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(URL, poolclass=pool.NullPool)
    with engine.connect() as conexao:
        context.configure(connection=conexao, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

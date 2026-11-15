"""Configuração lida de variáveis de ambiente (prefixo OASIS_) ou de um arquivo .env.

Segredos (senha do banco, chave do posto, chave HMAC) nunca ficam no código.
Em produção, OASIS_ENV_FILE aponta para um arquivo fora da pasta do site,
com permissão NTFS só para a identidade do pool do IIS e para administradores.
"""

import os
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict

PASTA_API = Path(__file__).resolve().parent.parent
CHAVE_POSTO_PADRAO = "troque-esta-chave-do-posto"


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OASIS_", extra="ignore", env_file_encoding="utf-8")

    database_url: str = "postgresql+psycopg://oasis:oasis_dev@localhost:5432/oasis"
    chave_posto: str = CHAVE_POSTO_PADRAO
    fuso: str = "America/Sao_Paulo"
    modelo_dir: Path = PASTA_API / "modelo"
    docs_habilitada: bool = True
    log_arquivo: Path | None = None
    leitura_atualizada_min: int = 15

    mqtt_habilitado: bool = False
    mqtt_host: str = "broker.hivemq.com"
    mqtt_porta: int = 1883
    mqtt_prefixo: str = "oasis-rm560760"
    mqtt_hmac_chave: str = ""
    mqtt_tolerancia_s: int = 300

    @property
    def zona(self) -> ZoneInfo:
        return ZoneInfo(self.fuso)

    @property
    def assinatura_exigida(self) -> bool:
        return bool(self.mqtt_hmac_chave)


def carregar_config() -> Config:
    """Lê o .env indicado em OASIS_ENV_FILE (ou api/.env, se existir) e o ambiente."""
    arquivo = Path(os.environ.get("OASIS_ENV_FILE", PASTA_API / ".env"))
    return Config(_env_file=arquivo if arquivo.exists() else None)

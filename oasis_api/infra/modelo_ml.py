"""Carrega o modelo treinado no notebook de IA e faz a previsão.

Arquivos esperados em OASIS_MODELO_DIR (por padrão, a pasta modelo/ deste repositório):
- modelo_risco.joblib: o pipeline do scikit-learn (padronização + regressão logística);
- modelo_risco.json: atributos na ordem do treino, limiar de decisão, métricas e o SHA-256 do .joblib.

O .joblib só é aberto se o SHA-256 bater com o do .json: um arquivo trocado
(e um pickle pode executar código ao ser aberto) não é carregado.
"""

import hashlib
import json
import logging
from pathlib import Path

import joblib
import numpy as np

from ..dominio.erros import IndisponivelErro

log = logging.getLogger("oasis.modelo")

ARQUIVO_MODELO = "modelo_risco.joblib"
ARQUIVO_META = "modelo_risco.json"


class ModeloRisco:
    def __init__(self, pasta: Path) -> None:
        self.pasta = pasta
        self.meta: dict = {}
        self._pipeline = None
        self.problema: str | None = None
        self._carregar()

    def _carregar(self) -> None:
        caminho_modelo, caminho_meta = self.pasta / ARQUIVO_MODELO, self.pasta / ARQUIVO_META
        if not (caminho_modelo.exists() and caminho_meta.exists()):
            self.problema = f"arquivos do modelo não encontrados em {self.pasta}"
            log.warning("Modelo de IA indisponível: %s", self.problema)
            return
        meta = json.loads(caminho_meta.read_text(encoding="utf-8"))
        hash_arquivo = hashlib.sha256(caminho_modelo.read_bytes()).hexdigest()
        if hash_arquivo != meta.get("sha256"):
            self.problema = "SHA-256 do modelo não confere com modelo_risco.json"
            log.error("Modelo de IA recusado: %s", self.problema)
            return
        self._pipeline = joblib.load(caminho_modelo)
        self.meta = meta
        log.info("Modelo %s carregado (limiar %.2f)", self.versao, self.limiar)

    @property
    def disponivel(self) -> bool:
        return self._pipeline is not None

    @property
    def versao(self) -> str:
        return str(self.meta.get("versao", ""))

    @property
    def limiar(self) -> float:
        return float(self.meta.get("limiar", 0.5))

    @property
    def atributos(self) -> list[str]:
        return list(self.meta.get("atributos", []))

    def prever(self, atributos: dict[str, float]) -> tuple[float, bool]:
        """Devolve (probabilidade de amanhã ser dia de risco, decisão pelo limiar)."""
        if not self.disponivel:
            raise IndisponivelErro("O modelo de previsão não está disponível no servidor.")
        linha = np.array([[float(atributos[nome]) for nome in self.atributos]], dtype=float)
        probabilidade = float(self._pipeline.predict_proba(linha)[0, 1])
        return probabilidade, probabilidade >= self.limiar

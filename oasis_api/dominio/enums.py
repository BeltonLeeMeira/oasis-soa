"""Vocabulário do domínio Oásis.

Os valores (lado direito) são os que aparecem no banco e no JSON da API.
"""

from enum import StrEnum


class Perfil(StrEnum):
    IDOSO = "Idoso"
    TRABALHADOR_DE_RUA = "TrabalhadorDeRua"
    CUIDADOR = "Cuidador"
    OUTRO = "Outro"


class TipoPonto(StrEnum):
    AGUA = "Agua"
    SOMBRA = "Sombra"
    CLIMATIZADO = "Climatizado"


class StatusPonto(StrEnum):
    PENDENTE = "Pendente"
    APROVADO = "Aprovado"
    REJEITADO = "Rejeitado"


class NivelRisco(StrEnum):
    NORMAL = "Normal"
    ATENCAO = "Atencao"
    ALERTA = "Alerta"
    PERIGO = "Perigo"

    @property
    def ordem(self) -> int:
        """Posição na escala: Normal = 0 ... Perigo = 3."""
        return list(NivelRisco).index(self)


class OrigemAlerta(StrEnum):
    SENSOR = "Sensor"
    PREVISAO = "Previsao"


def valores(enum_cls: type[StrEnum]) -> list[str]:
    """Lista os valores de um enum (usada pelo SQLAlchemy para gravar o texto)."""
    return [item.value for item in enum_cls]

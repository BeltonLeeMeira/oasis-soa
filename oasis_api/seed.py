"""Dados iniciais de demonstração. Pode rodar várias vezes: só insere o que ainda não existe.

    python -m oasis_api.seed

Os pontos são lugares públicos conhecidos da Vila Mariana e arredores, com coordenadas
aproximadas e horários não conferidos: servem para demonstrar o protótipo.
Nenhum dado pessoal: não há usuários nem pessoas acompanhadas no seed.
"""

from sqlalchemy import select

from .config import carregar_config
from .dominio.enums import StatusPonto, TipoPonto
from .infra.banco import criar_engine, criar_fabrica_sessoes
from .infra.tabelas import Estacao, PontoApoio

ESTACOES = [
    {"codigo": "EST-VM-01", "nome": "Vila Mariana", "latitude": -23.5891, "longitude": -46.6346},
]

PONTOS = [
    ("SESC Vila Mariana", TipoPonto.CLIMATIZADO, "Rua Pelotas, 141", "Vila Mariana", -23.5893, -46.6352, "Ter a dom, 10h às 21h", StatusPonto.APROVADO),
    ("Biblioteca Viriato Corrêa", TipoPonto.CLIMATIZADO, "Rua Sena Madureira, 298", "Vila Mariana", -23.5878, -46.6334, "Seg a sex, 9h às 18h", StatusPonto.APROVADO),
    ("Parque Ibirapuera", TipoPonto.SOMBRA, "Av. Pedro Álvares Cabral, s/n", "Vila Mariana", -23.5874, -46.6576, "5h às 0h", StatusPonto.APROVADO),
    ("Parque da Aclimação", TipoPonto.SOMBRA, "Rua Muniz de Souza, 1119", "Aclimação", -23.5730, -46.6290, "5h às 20h", StatusPonto.APROVADO),
    ("Centro Cultural São Paulo", TipoPonto.CLIMATIZADO, "Rua Vergueiro, 1000", "Paraíso", -23.5711, -46.6400, "Ter a dom, 10h às 20h", StatusPonto.APROVADO),
    ("Bebedouro da estação Vila Mariana", TipoPonto.AGUA, "Rua Domingos de Morais, 1500", "Vila Mariana", -23.5890, -46.6347, "Horário do metrô", StatusPonto.PENDENTE),
]


def semear() -> None:
    config = carregar_config()
    engine = criar_engine(config.database_url)
    with criar_fabrica_sessoes(engine)() as sessao:
        for dados in ESTACOES:
            if sessao.scalar(select(Estacao).where(Estacao.codigo == dados["codigo"])) is None:
                sessao.add(Estacao(**dados, ativa=True))
                print(f"+ estação {dados['codigo']}")
        for nome, tipo, endereco, bairro, lat, lon, horario, status in PONTOS:
            if sessao.scalar(select(PontoApoio).where(PontoApoio.nome == nome)) is None:
                sessao.add(
                    PontoApoio(
                        nome=nome, tipo=tipo, endereco=endereco, bairro=bairro, latitude=lat, longitude=lon, horario=horario, status=status
                    )
                )
                print(f"+ ponto {nome} ({status.value})")
        sessao.commit()
    engine.dispose()
    print("Seed concluído.")


if __name__ == "__main__":
    semear()

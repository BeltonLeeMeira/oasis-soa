"""Casos de uso: combinam as regras do domínio com os repositórios.

Cada operação que grava termina com commit (uma transação por caso de uso).
As rotas HTTP e o coletor MQTT chamam estes serviços; nenhum dos dois fala direto com o banco.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from .dominio.enums import NivelRisco, OrigemAlerta, Perfil, StatusPonto, TipoPonto
from .dominio.erros import ConflitoErro, NaoEncontradoErro, RegraVioladaErro, SemDadosErro
from .dominio.indice_calor import classificar, indice_calor_c
from .dominio.regras import (
    AcaoAlerta,
    atributos_do_dia,
    decidir_alerta,
    distancia_metros,
    mensagem_alerta_previsao,
    mensagem_alerta_sensor,
    sazonalidade,
    validar_leitura,
    validar_localizacao_sp,
    validar_transicao_status,
)
from .infra.modelo_ml import ModeloRisco
from .infra.repositorios import (
    AlertaRepositorio,
    EstacaoRepositorio,
    LeituraRepositorio,
    PontoRepositorio,
    PrevisaoRepositorio,
    UsuarioRepositorio,
)
from .infra.tabelas import Alerta, Estacao, Leitura, PontoApoio, Previsao, Usuario


def agora_utc() -> datetime:
    return datetime.now(ZoneInfo("UTC"))


class UsuarioServico:
    def __init__(self, sessao: Session) -> None:
        self.sessao = sessao
        self.usuarios = UsuarioRepositorio(sessao)

    def criar(self, apelido: str, perfil: Perfil, bairro: str) -> Usuario:
        usuario = self.usuarios.adicionar(Usuario(apelido=apelido, perfil=perfil, bairro=bairro))
        self.sessao.commit()
        return usuario

    def obter(self, usuario_id: int) -> Usuario:
        usuario = self.usuarios.obter(usuario_id)
        if usuario is None:
            raise NaoEncontradoErro(f"Usuário {usuario_id} não encontrado.")
        return usuario


class PontoServico:
    def __init__(self, sessao: Session) -> None:
        self.sessao = sessao
        self.pontos = PontoRepositorio(sessao)
        self.usuarios = UsuarioRepositorio(sessao)

    def criar(
        self,
        nome: str,
        tipo: TipoPonto,
        endereco: str,
        bairro: str,
        latitude: float,
        longitude: float,
        horario: str | None,
        criado_por_id: int | None,
    ) -> PontoApoio:
        validar_localizacao_sp(latitude, longitude)
        if criado_por_id is not None and self.usuarios.obter(criado_por_id) is None:
            raise RegraVioladaErro("O usuário informado em criadoPorId não existe.", campo="criadoPorId")
        # Todo ponto novo entra como Pendente: só aparece para o público depois que o posto aprovar.
        ponto = PontoApoio(
            nome=nome,
            tipo=tipo,
            endereco=endereco,
            bairro=bairro,
            latitude=latitude,
            longitude=longitude,
            horario=horario,
            status=StatusPonto.PENDENTE,
            criado_por_id=criado_por_id,
        )
        self.pontos.adicionar(ponto)
        self.sessao.commit()
        return ponto

    def listar(
        self,
        tipo: TipoPonto | None,
        status: StatusPonto | None,
        bairro: str | None,
        busca: str | None,
        latitude: float | None,
        longitude: float | None,
        raio_m: int | None,
    ) -> list[tuple[PontoApoio, int | None]]:
        pontos = self.pontos.listar(tipo=tipo, status=status, bairro=bairro, busca=busca)
        if latitude is None or longitude is None:
            return [(ponto, None) for ponto in pontos]
        com_distancia = [
            (ponto, round(distancia_metros(latitude, longitude, ponto.latitude, ponto.longitude))) for ponto in pontos
        ]
        if raio_m is not None:
            com_distancia = [(p, d) for p, d in com_distancia if d <= raio_m]
        return sorted(com_distancia, key=lambda item: item[1])

    def obter(self, ponto_id: int) -> PontoApoio:
        ponto = self.pontos.obter(ponto_id)
        if ponto is None:
            raise NaoEncontradoErro(f"Ponto {ponto_id} não encontrado.")
        return ponto

    def alterar_status(self, ponto_id: int, novo: StatusPonto) -> PontoApoio:
        ponto = self.obter(ponto_id)
        validar_transicao_status(ponto.status, novo)
        ponto.status = novo
        ponto.avaliado_em = agora_utc()
        self.sessao.commit()
        return ponto


class EstacaoServico:
    def __init__(self, sessao: Session) -> None:
        self.sessao = sessao
        self.estacoes = EstacaoRepositorio(sessao)

    def listar(self) -> list[Estacao]:
        return self.estacoes.listar()

    def obter(self, estacao_id: int) -> Estacao:
        estacao = self.estacoes.obter(estacao_id)
        if estacao is None:
            raise NaoEncontradoErro(f"Estação {estacao_id} não encontrada.")
        return estacao

    def criar(self, codigo: str, nome: str, latitude: float, longitude: float, ativa: bool) -> Estacao:
        validar_localizacao_sp(latitude, longitude)
        if self.estacoes.obter_por_codigo(codigo) is not None:
            raise ConflitoErro(f"Já existe uma estação com o código {codigo}.", campo="codigo")
        estacao = self.estacoes.adicionar(
            Estacao(codigo=codigo, nome=nome, latitude=latitude, longitude=longitude, ativa=ativa)
        )
        self.sessao.commit()
        return estacao


@dataclass
class LeituraRegistrada:
    leitura: Leitura
    acao_alerta: AcaoAlerta
    alerta: Alerta | None


class LeituraServico:
    def __init__(self, sessao: Session) -> None:
        self.sessao = sessao
        self.estacoes = EstacaoRepositorio(sessao)
        self.leituras = LeituraRepositorio(sessao)
        self.alertas = AlertaRepositorio(sessao)

    def registrar(self, codigo: str, temperatura: float, umidade: float) -> LeituraRegistrada:
        estacao = self.estacoes.obter_por_codigo(codigo)
        if estacao is None:
            raise NaoEncontradoErro(f"Estação {codigo} não cadastrada.", campo="codigo")
        if not estacao.ativa:
            raise RegraVioladaErro(f"A estação {codigo} está inativa.", campo="codigo")
        validar_leitura(temperatura, umidade)

        # O índice é sempre recalculado aqui: a API não confia no valor vindo do dispositivo.
        indice = indice_calor_c(temperatura, umidade)
        nivel = classificar(indice)
        agora = agora_utc()
        leitura = self.leituras.adicionar(
            Leitura(
                estacao_id=estacao.id,
                temperatura=round(temperatura, 1),
                umidade=round(umidade, 1),
                indice_calor=indice,
                nivel=nivel,
                recebida_em=agora,
            )
        )

        ativo = self.alertas.ativo_de_sensor(estacao.id)
        acao = decidir_alerta(nivel, ativo.nivel if ativo else None)
        alerta = ativo
        if acao is AcaoAlerta.ABRIR:
            alerta = self.alertas.adicionar(
                Alerta(
                    estacao_id=estacao.id,
                    nivel=nivel,
                    origem=OrigemAlerta.SENSOR,
                    mensagem=mensagem_alerta_sensor(nivel, indice, estacao.nome),
                    inicio=agora,
                )
            )
        elif acao is AcaoAlerta.ESCALAR and ativo is not None:
            ativo.nivel = nivel
            ativo.mensagem = mensagem_alerta_sensor(nivel, indice, estacao.nome)
        elif acao is AcaoAlerta.FECHAR and ativo is not None:
            ativo.fim = agora
        self.sessao.commit()
        return LeituraRegistrada(leitura=leitura, acao_alerta=acao, alerta=alerta)

    def listar(self, estacao_id: int, desde: datetime | None, limite: int) -> list[Leitura]:
        if self.estacoes.obter(estacao_id) is None:
            raise NaoEncontradoErro(f"Estação {estacao_id} não encontrada.")
        return self.leituras.listar_da_estacao(estacao_id, desde, limite)


@dataclass
class RiscoEstacao:
    estacao: Estacao
    leitura: Leitura | None
    atualizada: bool


class RiscoServico:
    def __init__(self, sessao: Session, minutos_validade: int) -> None:
        self.estacoes = EstacaoRepositorio(sessao)
        self.leituras = LeituraRepositorio(sessao)
        self.minutos_validade = minutos_validade

    def agora(self) -> list[RiscoEstacao]:
        ultimas = self.leituras.ultimas_por_estacao()
        limite = agora_utc() - timedelta(minutes=self.minutos_validade)
        resultado = []
        for estacao in self.estacoes.listar(apenas_ativas=True):
            leitura = ultimas.get(estacao.id)
            resultado.append(RiscoEstacao(estacao, leitura, leitura is not None and leitura.recebida_em >= limite))
        return resultado


class AlertaServico:
    def __init__(self, sessao: Session, zona: ZoneInfo) -> None:
        self.sessao = sessao
        self.alertas = AlertaRepositorio(sessao)
        self.zona = zona

    def ativos(self) -> list[Alerta]:
        agora = agora_utc()
        if self.alertas.encerrar_previsoes_vencidas(agora.astimezone(self.zona).date(), agora):
            self.sessao.commit()
        return self.alertas.ativos()

    def recentes(self) -> list[Alerta]:
        """Os 50 alertas mais recentes, ativos ou encerrados (histórico)."""
        return self.alertas.recentes()


@dataclass
class ResultadoPrevisao:
    data_alvo: date
    probabilidade: float
    risco: bool
    versao_modelo: str
    limiar: float
    atributos: dict[str, float]
    leituras_usadas: int


class PrevisaoServico:
    MINUTOS_CACHE = 10

    def __init__(self, sessao: Session, modelo: ModeloRisco, zona: ZoneInfo) -> None:
        self.sessao = sessao
        self.modelo = modelo
        self.zona = zona
        self.leituras = LeituraRepositorio(sessao)
        self.alertas = AlertaRepositorio(sessao)
        self.previsoes = PrevisaoRepositorio(sessao)

    def amanha(self) -> ResultadoPrevisao:
        """Resume as leituras de hoje (horário de Brasília) e pergunta ao modelo sobre amanhã.

        A previsão fica guardada (histórico e auditoria) e é recalculada no máximo a cada
        MINUTOS_CACHE minutos: várias telas abertas não geram uma linha por acesso.
        """
        agora = agora_utc()
        hoje = agora.astimezone(self.zona).date()
        data_alvo = hoje + timedelta(days=1)
        recente = self.previsoes.ultima_para(data_alvo, agora - timedelta(minutes=self.MINUTOS_CACHE))
        if recente is not None:
            return ResultadoPrevisao(
                data_alvo,
                recente.probabilidade,
                recente.risco,
                recente.versao_modelo,
                self.modelo.limiar,
                recente.atributos,
                recente.leituras_usadas,
            )

        inicio = datetime.combine(hoje, time.min, tzinfo=self.zona)
        valores = self.leituras.valores_entre(inicio, inicio + timedelta(days=1))
        if not valores:
            raise SemDadosErro("Ainda não há leituras hoje. A previsão usa as leituras do dia nas estações ativas.")

        atributos = atributos_do_dia(valores, data_alvo)
        probabilidade, risco = self.modelo.prever(atributos)
        self.previsoes.adicionar(
            Previsao(
                data_alvo=data_alvo,
                probabilidade=probabilidade,
                risco=risco,
                versao_modelo=self.modelo.versao,
                leituras_usadas=len(valores),
                atributos=atributos,
                criada_em=agora,
            )
        )
        if risco and self.alertas.de_previsao_para(data_alvo) is None:
            self.alertas.adicionar(
                Alerta(
                    estacao_id=None,
                    nivel=NivelRisco.ALERTA,
                    origem=OrigemAlerta.PREVISAO,
                    mensagem=mensagem_alerta_previsao(data_alvo, probabilidade),
                    data_alvo=data_alvo,
                    inicio=agora,
                )
            )
        self.sessao.commit()
        return ResultadoPrevisao(
            data_alvo, probabilidade, risco, self.modelo.versao, self.modelo.limiar, atributos, len(valores)
        )

    def simular(self, atributos_do_dia_informados: dict[str, float], data_alvo: date | None) -> ResultadoPrevisao:
        """Previsão para valores digitados (demonstração no Insomnia). Não grava nada."""
        alvo = data_alvo or (agora_utc().astimezone(self.zona).date() + timedelta(days=1))
        sen, cos = sazonalidade(alvo)
        atributos = {**atributos_do_dia_informados, "dia_sen": sen, "dia_cos": cos}
        probabilidade, risco = self.modelo.prever(atributos)
        return ResultadoPrevisao(alvo, probabilidade, risco, self.modelo.versao, self.modelo.limiar, atributos, 0)

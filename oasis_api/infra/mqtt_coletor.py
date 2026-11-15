"""Recebe as leituras das estações pelo MQTT e grava pela mesma regra da API.

Por que MQTT: a estação roda no simulador Wokwi, que tem saída para a internet mas não
enxerga a rede local. Ela publica num broker público e a API, na VM, assina o tópico
(conexão de saída, que funciona atrás do roteador).

Como o broker é público, qualquer pessoa pode publicar no tópico. Por isso cada mensagem:
1. tem tamanho máximo e formato validado;
2. traz o código da estação igual ao do tópico;
3. é assinada com HMAC-SHA256 (chave só da estação e da API) e tem horário recente,
   o que barra mensagem forjada e mensagem antiga repetida (replay);
4. passa pelas mesmas validações de faixa do POST /api/leituras.
"""

import hashlib
import hmac
import json
import logging
import secrets
import time
from dataclasses import dataclass

import paho.mqtt.client as mqtt
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session, sessionmaker

from ..config import Config
from ..dominio.erros import ErroDominio
from ..servicos import LeituraServico

log = logging.getLogger("oasis.mqtt")

TAMANHO_MAXIMO = 512


class MensagemLeitura(BaseModel):
    codigo: str = Field(pattern=r"^EST-[A-Z]{2}-\d{2}$")
    temperatura: float
    umidade: float
    ts: int | None = None
    sig: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


def texto_assinado(codigo: str, temperatura: float, umidade: float, ts: int) -> str:
    """Texto que a estação assina. O sketch do ESP32 monta exatamente o mesmo."""
    return f"{codigo}|{temperatura:.1f}|{umidade:.1f}|{ts}"


def assinar(chave: str, texto: str) -> str:
    return hmac.new(chave.encode(), texto.encode(), hashlib.sha256).hexdigest()


@dataclass
class Resultado:
    aceita: bool
    motivo: str
    nivel: str | None = None


class ColetorMqtt:
    def __init__(self, config: Config, fabrica_sessoes: sessionmaker[Session]) -> None:
        self.config = config
        self.fabrica_sessoes = fabrica_sessoes
        self.conectado = False
        self.aceitas = 0
        self.rejeitadas = 0
        self._ultimo_ts: dict[str, int] = {}
        self._cliente: mqtt.Client | None = None

    @property
    def topico_leituras(self) -> str:
        return f"{self.config.mqtt_prefixo}/estacoes/+/leituras"

    def topico_nivel(self, codigo: str) -> str:
        return f"{self.config.mqtt_prefixo}/estacoes/{codigo}/nivel"

    # ------------------------------------------------------------ conexão ---

    def iniciar(self) -> None:
        cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"oasis-api-{secrets.token_hex(4)}")
        cliente.on_connect = self._ao_conectar
        cliente.on_disconnect = self._ao_desconectar
        cliente.on_message = self._ao_receber
        cliente.reconnect_delay_set(min_delay=1, max_delay=30)
        cliente.connect_async(self.config.mqtt_host, self.config.mqtt_porta, keepalive=30)
        cliente.loop_start()
        self._cliente = cliente
        log.info("Coletor MQTT iniciado: %s:%s, tópico %s", self.config.mqtt_host, self.config.mqtt_porta, self.topico_leituras)

    def parar(self) -> None:
        if self._cliente is not None:
            self._cliente.loop_stop()
            self._cliente.disconnect()
            self._cliente = None
        self.conectado = False

    def _ao_conectar(self, cliente, _userdata, _flags, reason_code, _properties) -> None:
        if reason_code.is_failure:
            log.warning("Falha ao conectar no broker MQTT: %s", reason_code)
            return
        self.conectado = True
        cliente.subscribe(self.topico_leituras, qos=1)
        log.info("Conectado ao broker MQTT e inscrito em %s", self.topico_leituras)

    def _ao_desconectar(self, _cliente, _userdata, _flags, reason_code, _properties) -> None:
        self.conectado = False
        log.warning("Desconectado do broker MQTT (%s); tentando reconectar", reason_code)

    def _ao_receber(self, _cliente, _userdata, mensagem: mqtt.MQTTMessage) -> None:
        try:
            self.processar(mensagem.topic, mensagem.payload)
        except Exception:
            log.exception("Erro inesperado ao processar mensagem de %s", mensagem.topic)

    # ------------------------------------------------------- processamento ---

    def _rejeitar(self, topico: str, motivo: str) -> Resultado:
        self.rejeitadas += 1
        log.warning("Leitura MQTT rejeitada (%s): %s", topico, motivo)
        return Resultado(False, motivo)

    def processar(self, topico: str, payload: bytes) -> Resultado:
        if len(payload) > TAMANHO_MAXIMO:
            return self._rejeitar(topico, "mensagem grande demais")
        try:
            msg = MensagemLeitura.model_validate_json(payload)
        except ValidationError:
            return self._rejeitar(topico, "formato inválido")

        partes = topico.split("/")
        if len(partes) != 4 or partes[3] != "leituras" or partes[2] != msg.codigo:
            return self._rejeitar(topico, "código da mensagem diferente do tópico")

        if self.config.assinatura_exigida:
            if msg.sig is None or msg.ts is None:
                return self._rejeitar(topico, "mensagem sem assinatura")
            esperado = assinar(self.config.mqtt_hmac_chave, texto_assinado(msg.codigo, msg.temperatura, msg.umidade, msg.ts))
            if not hmac.compare_digest(esperado, msg.sig):
                return self._rejeitar(topico, "assinatura inválida")
            if abs(time.time() - msg.ts) > self.config.mqtt_tolerancia_s:
                return self._rejeitar(topico, "horário fora da janela (mensagem antiga ou relógio errado)")
            if msg.ts <= self._ultimo_ts.get(msg.codigo, 0):
                return self._rejeitar(topico, "mensagem repetida (replay)")

        with self.fabrica_sessoes() as sessao:
            try:
                registro = LeituraServico(sessao).registrar(msg.codigo, msg.temperatura, msg.umidade)
            except ErroDominio as erro:
                return self._rejeitar(topico, erro.mensagem)

        if msg.ts is not None:
            self._ultimo_ts[msg.codigo] = msg.ts
        self.aceitas += 1
        leitura = registro.leitura
        if self._cliente is not None:
            resposta = {"nivel": leitura.nivel.value, "indiceCalor": leitura.indice_calor, "alerta": registro.acao_alerta.value}
            self._cliente.publish(self.topico_nivel(msg.codigo), json.dumps(resposta), qos=0)
        return Resultado(True, "ok", leitura.nivel.value)

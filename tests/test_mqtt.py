"""Coletor MQTT: regras de aceitação das mensagens e um teste real com broker local."""

import json
import socket
import time

import paho.mqtt.client as mqtt
import pytest
from sqlalchemy import func, select

from oasis_api.infra.mqtt_coletor import ColetorMqtt, assinar, texto_assinado
from oasis_api.infra.tabelas import Leitura

from .conftest import CHAVE_HMAC

TOPICO = "oasis-teste/estacoes/EST-VM-01/leituras"


def mensagem(temperatura=34.0, umidade=55.0, ts=None, codigo="EST-VM-01", chave=CHAVE_HMAC, **extra) -> bytes:
    ts = int(time.time()) if ts is None else ts
    corpo = {"codigo": codigo, "temperatura": temperatura, "umidade": umidade, "ts": ts}
    if chave:
        corpo["sig"] = assinar(chave, texto_assinado(codigo, temperatura, umidade, ts))
    corpo.update(extra)
    return json.dumps(corpo).encode()


@pytest.fixture
def coletor(config, fabrica_sessoes):
    return ColetorMqtt(config, fabrica_sessoes)


def contar_leituras(fabrica_sessoes) -> int:
    with fabrica_sessoes() as sessao:
        return sessao.scalar(select(func.count()).select_from(Leitura))


def test_mensagem_assinada_e_aceita(coletor, fabrica_sessoes):
    resultado = coletor.processar(TOPICO, mensagem())
    assert resultado.aceita and resultado.nivel == "Perigo"
    assert contar_leituras(fabrica_sessoes) == 1


@pytest.mark.parametrize(
    ("payload", "motivo"),
    [
        (mensagem(chave=None), "mensagem sem assinatura"),
        (mensagem(chave="chave-do-atacante"), "assinatura inválida"),
        (mensagem(ts=int(time.time()) - 3600), "horário fora da janela"),
        (b"isto nao e json", "formato inválido"),
        (mensagem(codigo="EST-VM-02"), "código da mensagem diferente do tópico"),
        (b"{" + b" " * 600 + b"}", "mensagem grande demais"),
        (mensagem(temperatura=80.0), "Temperatura fora da faixa"),
    ],
)
def test_mensagens_rejeitadas(coletor, fabrica_sessoes, payload, motivo):
    resultado = coletor.processar(TOPICO, payload)
    assert not resultado.aceita and motivo in resultado.motivo
    assert contar_leituras(fabrica_sessoes) == 0


def test_replay_e_bloqueado(coletor, fabrica_sessoes):
    capturada = mensagem()
    assert coletor.processar(TOPICO, capturada).aceita
    assert "replay" in coletor.processar(TOPICO, capturada).motivo
    assert contar_leituras(fabrica_sessoes) == 1


def _broker_local() -> bool:
    try:
        socket.create_connection(("localhost", 1883), timeout=1).close()
        return True
    except OSError:
        return False


@pytest.mark.skipif(not _broker_local(), reason="sem broker MQTT em localhost:1883")
def test_integracao_com_broker(coletor, fabrica_sessoes):
    coletor.iniciar()
    try:
        for _ in range(50):
            if coletor.conectado:
                break
            time.sleep(0.1)
        assert coletor.conectado
        time.sleep(0.3)  # tempo para a inscrição no tópico ser confirmada

        respostas = []
        estacao = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        estacao.on_message = lambda _c, _u, msg: respostas.append(json.loads(msg.payload))
        estacao.connect("localhost", 1883)
        estacao.subscribe("oasis-teste/estacoes/EST-VM-01/nivel")
        estacao.loop_start()
        time.sleep(0.3)
        estacao.publish(TOPICO, mensagem(31.0, 50.0), qos=1).wait_for_publish(5)

        for _ in range(50):
            if respostas:
                break
            time.sleep(0.1)
        estacao.loop_stop()
        estacao.disconnect()
        assert contar_leituras(fabrica_sessoes) == 1
        assert respostas and respostas[0]["nivel"] == "Alerta" and respostas[0]["alerta"] == "Abrir"
    finally:
        coletor.parar()

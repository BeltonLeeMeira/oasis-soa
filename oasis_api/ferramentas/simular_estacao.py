"""Publica leituras no MQTT do mesmo jeito que o ESP32 do Wokwi (inclusive a assinatura).

Útil para testar a API sem abrir o simulador:

    python -m oasis_api.ferramentas.simular_estacao --temperatura 34 --umidade 55
    python -m oasis_api.ferramentas.simular_estacao --temperatura 34 --umidade 55 --repetir 6 --intervalo 10

Usa as mesmas variáveis OASIS_MQTT_* da API (host, porta, prefixo e chave HMAC).
"""

import argparse
import json
import time

import paho.mqtt.client as mqtt

from ..config import carregar_config
from ..infra.mqtt_coletor import assinar, texto_assinado


def main() -> None:
    parser = argparse.ArgumentParser(description="Simula a estação ESP32 publicando no MQTT")
    parser.add_argument("--codigo", default="EST-VM-01")
    parser.add_argument("--temperatura", type=float, required=True)
    parser.add_argument("--umidade", type=float, required=True)
    parser.add_argument("--repetir", type=int, default=1)
    parser.add_argument("--intervalo", type=float, default=10.0)
    parser.add_argument("--sem-assinatura", action="store_true", help="envia sem HMAC (a API deve rejeitar)")
    args = parser.parse_args()

    config = carregar_config()
    topico = f"{config.mqtt_prefixo}/estacoes/{args.codigo}/leituras"
    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    cliente.connect(config.mqtt_host, config.mqtt_porta, keepalive=30)
    cliente.loop_start()
    for i in range(args.repetir):
        temperatura, umidade, ts = round(args.temperatura, 1), round(args.umidade, 1), int(time.time())
        mensagem = {"codigo": args.codigo, "temperatura": temperatura, "umidade": umidade, "ts": ts}
        if config.mqtt_hmac_chave and not args.sem_assinatura:
            mensagem["sig"] = assinar(config.mqtt_hmac_chave, texto_assinado(args.codigo, temperatura, umidade, ts))
        cliente.publish(topico, json.dumps(mensagem), qos=1).wait_for_publish(5)
        print(f"publicado em {topico}: {mensagem}")
        if i < args.repetir - 1:
            time.sleep(args.intervalo)
    cliente.loop_stop()
    cliente.disconnect()


if __name__ == "__main__":
    main()

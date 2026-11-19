"""Ataca a API Oásis de propósito e grava, em markdown, o que aconteceu (evidências de Cybersecurity).

Roda contra a API local ou contra o servidor IIS:

    python coletar_evidencias.py --base-url http://localhost:8000 --chave-posto SUA_CHAVE \
        --mqtt-host localhost --hmac-chave oasis-demo-2026-troque-esta-chave --log-api ../../api.log

Cada teste mostra o pedido, a resposta e o que se esperava. Nada aqui altera dados reais:
os ataques de SQL injection só leem, e as leituras MQTT válidas são de teste.
"""

import argparse
import hashlib
import hmac
import http.client
import json
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlsplit

import paho.mqtt.client as mqtt

linhas: list[str] = []


def escrever(*partes: str) -> None:
    linhas.extend(partes)


def pedido(base: str, metodo: str, caminho: str, corpo: dict | str | None = None, cabecalhos: dict | None = None):
    """Usa http.client para mandar o caminho exatamente como está (sem normalizar ../)."""
    url = urlsplit(base)
    conexao = http.client.HTTPConnection(url.hostname, url.port or 80, timeout=10)
    cabecalhos = dict(cabecalhos or {})
    dados = None
    if corpo is not None:
        dados = corpo.encode() if isinstance(corpo, str) else json.dumps(corpo).encode()
        cabecalhos.setdefault("Content-Type", "application/json")
    conexao.request(metodo, caminho, body=dados, headers=cabecalhos)
    resposta = conexao.getresponse()
    texto = resposta.read().decode("utf-8", "replace")
    conexao.close()
    return resposta.status, dict(resposta.getheaders()), texto


def bloco(texto: str, limite: int = 600) -> str:
    texto = texto.strip()
    return texto if len(texto) <= limite else texto[:limite] + " ..."


def resultado(ok: bool) -> str:
    return "**Protegido**" if ok else "**FALHOU: revisar**"


def sql_injection(base: str) -> None:
    escrever("## 1. SQL injection na busca de pontos", "",
             "A busca `GET /api/pontos?busca=` recebe texto livre e é o alvo natural de SQL injection. "
             "A consulta usa parâmetro vinculado (prepared statement) e escapa os curingas do LIKE.", "")
    _, _, antes = pedido(base, "GET", "/api/pontos")
    total_antes = len(json.loads(antes))
    escrever(f"Pontos aprovados antes dos ataques: **{total_antes}**", "",
             "| Ataque enviado em `busca` | Status | Resposta | Resultado |", "| --- | --- | --- | --- |")
    for ataque in ["' OR '1'='1", "' OR 1=1 --", "'; DROP TABLE pontos_apoio; --",
                   "%' UNION SELECT id, apelido, perfil, bairro FROM usuarios --", "%"]:
        status, _, texto = pedido(base, "GET", "/api/pontos?busca=" + quote(ataque))
        ok = status == 200 and texto.strip() == "[]"
        escrever(f"| `{ataque.replace('|', '\\|')}` | {status} | `{bloco(texto, 60)}` | {resultado(ok)} |")
    _, _, depois = pedido(base, "GET", "/api/pontos")
    total_depois = len(json.loads(depois))
    escrever("", f"Pontos aprovados depois: **{total_depois}** (a tabela continua intacta: {resultado(total_antes == total_depois)}).", "")


def lfi(base: str) -> None:
    escrever("## 2. LFI / path traversal na página pública", "",
             "A página pública é servida pelo StaticFiles do Starlette, que resolve o caminho e recusa "
             "qualquer arquivo fora da pasta `web/`. Os segredos ficam fora da pasta do site (`C:\\oasis\\config`).", "",
             "| Caminho pedido (cru, sem normalizar) | Status | Vazou algo? | Resultado |", "| --- | --- | --- | --- |")
    for caminho in ["/../../etc/passwd", "/..%2f..%2f..%2fetc%2fpasswd", "/%2e%2e/%2e%2e/etc/passwd",
                    "/..\\..\\windows\\win.ini", "/estilo.css/../../oasis_api/config.py", "/....//....//etc/passwd",
                    "/../config/oasis.env"]:
        status, _, texto = pedido(base, "GET", caminho)
        vazou = any(marca in texto for marca in ("root:", "OASIS_", "[fonts]", "database_url"))
        escrever(f"| `{caminho}` | {status} | {'sim' if vazou else 'não'} | {resultado(status in (400, 404) and not vazou)} |")
    escrever("")


def controle_de_acesso(base: str, chave: str) -> None:
    escrever("## 3. Controle de acesso das rotas do posto", "",
             "Aprovar ponto, cadastrar estação, enviar leitura por HTTP, ver pendentes e consultar usuário "
             "pedem o cabeçalho `X-Chave-Posto`, comparado em tempo constante (`hmac.compare_digest`).", "",
             "| Pedido | Chave | Status | Resultado |", "| --- | --- | --- | --- |")
    casos = [
        ("GET", "/api/pontos?status=Pendente", None, None),
        ("GET", "/api/pontos?status=Pendente", "chute", None),
        ("PATCH", "/api/pontos/1/status", "chute", {"status": "Rejeitado"}),
        ("POST", "/api/estacoes", None, {"codigo": "EST-ZZ-99", "nome": "Falsa", "latitude": -23.55, "longitude": -46.63}),
        ("GET", "/api/usuarios/1", None, None),
        ("GET", "/api/usuarios/2", None, None),
    ]
    for metodo, caminho, valor, corpo in casos:
        cabecalhos = {"X-Chave-Posto": valor} if valor else {}
        status, _, _ = pedido(base, metodo, caminho, corpo, cabecalhos)
        descricao = "sem chave" if valor is None else f"`{valor}`"
        escrever(f"| `{metodo} {caminho}` | {descricao} | {status} | {resultado(status == 401)} |")
    status, _, _ = pedido(base, "GET", "/api/pontos?status=Pendente", cabecalhos={"X-Chave-Posto": chave})
    escrever(f"| `GET /api/pontos?status=Pendente` | chave certa | {status} | {'**Acesso liberado**' if status == 200 else '**FALHOU**'} |", "",
             "A consulta de usuário pede a chave porque os ids são sequenciais: sem ela, qualquer pessoa "
             "percorreria 1, 2, 3... e montaria uma lista de idosos por bairro (enumeração para OSINT).", "")


def validacao_e_erros(base: str, chave: str) -> None:
    escrever("## 4. Validação de entrada e mensagens de erro", "",
             "| Entrada maliciosa ou impossível | Status | Trecho da resposta | Resultado |", "| --- | --- | --- | --- |")
    posto = {"X-Chave-Posto": chave}
    casos = [
        ("JSON quebrado", "POST", "/api/usuarios", "{json quebrado", {}),
        ("Leitura de 85 °C (sensor falso)", "POST", "/api/leituras", {"codigo": "EST-VM-01", "temperatura": 85, "umidade": 50}, posto),
        ("Umidade de 140%", "POST", "/api/leituras", {"codigo": "EST-VM-01", "temperatura": 30, "umidade": 140}, posto),
        ("NaN na previsão", "POST", "/api/previsoes/simular", '{"tempMax": NaN, "tempMin": 1, "tempMedia": 1, "umidMedia": 1, "umidMin": 1, "icMax": 1}', {}),
        ("Apelido com 5.000 letras", "POST", "/api/usuarios", {"apelido": "A" * 5000, "perfil": "Idoso", "bairro": "Vila Mariana"}, {}),
        ("Ponto em Paris", "POST", "/api/pontos", {"nome": "Torre", "tipo": "Sombra", "endereco": "Champ de Mars", "bairro": "Paris", "latitude": 48.8584, "longitude": 2.2945}, {}),
    ]
    for nome, metodo, caminho, corpo, cabecalhos in casos:
        status, _, texto = pedido(base, metodo, caminho, corpo, cabecalhos)
        vazou = any(marca in texto for marca in ("Traceback", "sqlalchemy", "psycopg", 'File "'))
        trecho = bloco(texto.replace("\n", " "), 110).replace("|", "\\|")
        escrever(f"| {nome} | {status} | `{trecho}` | {resultado(status == 400 and not vazou)} |")
    escrever("", "Nenhuma resposta traz pilha de chamadas, SQL ou caminho de arquivo: os erros saem no formato Problem Details (RFC 9457).", "")


def cabecalhos_seguranca(base: str) -> None:
    status, cabecalhos, _ = pedido(base, "GET", "/")
    escrever("## 5. Cabeçalhos de segurança da página pública", "", f"`GET /` respondeu {status} com:", "", "```")
    for nome in ("content-security-policy", "x-content-type-options", "x-frame-options", "referrer-policy", "server"):
        valor = next((v for k, v in cabecalhos.items() if k.lower() == nome), "(ausente)")
        escrever(f"{nome}: {valor}")
    escrever("```", "", "A política de conteúdo só permite scripts do próprio site (barra XSS com script de terceiros), "
             "`DENY` impede a página dentro de um iframe (clickjacking) e o servidor não se identifica.", "")


def assinar(chave: str, codigo: str, temperatura: float, umidade: float, ts: int) -> str:
    return hmac.new(chave.encode(), f"{codigo}|{temperatura:.1f}|{umidade:.1f}|{ts}".encode(), hashlib.sha256).hexdigest()


def contadores(base: str) -> tuple[int, int]:
    _, _, texto = pedido(base, "GET", "/health")
    saude = json.loads(texto)
    return saude["leiturasMqttAceitas"], saude["leiturasMqttRejeitadas"]


def mqtt_forjado(base: str, host: str, porta: int, prefixo: str, chave: str, log_api: Path | None) -> None:
    escrever("## 6. Leituras forjadas no broker MQTT", "",
             "O broker é público: quem descobrir o tópico pode publicar. Cada leitura precisa de assinatura "
             "HMAC-SHA256 com a chave da estação, horário recente (5 min) e número crescente (anti-replay), "
             "além das faixas válidas de temperatura e umidade.", "")
    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"evidencias-{int(time.time())}")
    cliente.connect(host, porta, keepalive=30)
    cliente.loop_start()
    time.sleep(1)
    topico = f"{prefixo}/estacoes/EST-VM-01/leituras"
    agora = int(time.time())
    valida = {"codigo": "EST-VM-01", "temperatura": 33.0, "umidade": 50.0, "ts": agora,
              "sig": assinar(chave, "EST-VM-01", 33.0, 50.0, agora)}
    adulterada = dict(valida, temperatura=12.0)  # assinatura de 33 °C, valor trocado para esconder o calor
    antiga_ts = agora - 900
    fora_faixa_ts = agora + 2
    casos = [
        ("Leitura legítima, assinada", topico, json.dumps(valida), True),
        ("Replay: a mesma mensagem de novo", topico, json.dumps(valida), False),
        ("Sem assinatura (45 °C para causar pânico)", topico, json.dumps({"codigo": "EST-VM-01", "temperatura": 45.0, "umidade": 50.0}), False),
        ("Assinada com chave errada", topico, json.dumps(dict(valida, ts=agora + 1, sig=assinar("chave-errada", "EST-VM-01", 33.0, 50.0, agora + 1))), False),
        ("Valor trocado depois de assinar (12 °C)", topico, json.dumps(dict(adulterada, ts=agora + 1)), False),
        ("Mensagem antiga (15 min)", topico, json.dumps({"codigo": "EST-VM-01", "temperatura": 33.0, "umidade": 50.0, "ts": antiga_ts, "sig": assinar(chave, "EST-VM-01", 33.0, 50.0, antiga_ts)}), False),
        ("Código diferente do tópico", f"{prefixo}/estacoes/EST-XX-99/leituras", json.dumps(dict(valida, ts=agora + 1)), False),
        ("Mensagem gigante (600 bytes)", topico, json.dumps({"codigo": "EST-VM-01", "lixo": "x" * 600}), False),
        ("Assinada, mas 85 °C (fora da faixa)", topico, json.dumps({"codigo": "EST-VM-01", "temperatura": 85.0, "umidade": 50.0, "ts": fora_faixa_ts, "sig": assinar(chave, "EST-VM-01", 85.0, 50.0, fora_faixa_ts)}), False),
    ]
    tamanho_log = log_api.stat().st_size if log_api and log_api.exists() else 0
    escrever("| Mensagem publicada | Esperado | Aceitas | Rejeitadas | Resultado |", "| --- | --- | --- | --- | --- |")
    for nome, destino, carga, deve_aceitar in casos:
        aceitas_antes, rejeitadas_antes = contadores(base)
        cliente.publish(destino, carga, qos=1).wait_for_publish(5)
        time.sleep(1.5)
        aceitas, rejeitadas = contadores(base)
        aceitou = aceitas > aceitas_antes
        rejeitou = rejeitadas > rejeitadas_antes
        ok = aceitou if deve_aceitar else (rejeitou and not aceitou)
        escrever(f"| {nome} | {'aceitar' if deve_aceitar else 'recusar'} | +{aceitas - aceitas_antes} | +{rejeitadas - rejeitadas_antes} | {resultado(ok)} |")
    cliente.loop_stop()
    cliente.disconnect()
    if log_api and log_api.exists():
        with log_api.open(encoding="utf-8", errors="replace") as arquivo:
            arquivo.seek(tamanho_log)
            motivos = [linha.strip() for linha in arquivo if "MQTT rejeitada" in linha]
        escrever("", "Motivos registrados no log da API:", "", "```", *motivos, "```")
    escrever("")


def main() -> None:
    argumentos = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    argumentos.add_argument("--base-url", default="http://localhost:8000")
    argumentos.add_argument("--chave-posto", default="troque-esta-chave-do-posto")
    argumentos.add_argument("--mqtt-host", default="localhost")
    argumentos.add_argument("--mqtt-porta", type=int, default=1883)
    argumentos.add_argument("--mqtt-prefixo", default="oasis-rm560760")
    argumentos.add_argument("--hmac-chave", default="oasis-demo-2026-troque-esta-chave")
    argumentos.add_argument("--log-api", type=Path, help="arquivo de log da API, para listar os motivos de rejeição")
    argumentos.add_argument("--sem-mqtt", action="store_true")
    argumentos.add_argument("--saida", type=Path, default=Path(__file__).resolve().parent.parent / "evidencias" / "evidencias-api.md")
    a = argumentos.parse_args()

    escrever("# Evidências de segurança da API Oásis", "",
             f"Execução real de `seguranca/scripts/coletar_evidencias.py` em {datetime.now():%d/%m/%Y %H:%M}, contra `{a.base_url}`.", "")
    sql_injection(a.base_url)
    lfi(a.base_url)
    controle_de_acesso(a.base_url, a.chave_posto)
    validacao_e_erros(a.base_url, a.chave_posto)
    cabecalhos_seguranca(a.base_url)
    if not a.sem_mqtt:
        mqtt_forjado(a.base_url, a.mqtt_host, a.mqtt_porta, a.mqtt_prefixo, a.hmac_chave, a.log_api)
    a.saida.parent.mkdir(parents=True, exist_ok=True)
    a.saida.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    falhas = sum("FALHOU" in linha for linha in linhas)
    print(f"{a.saida}  ({falhas} falha(s))")


if __name__ == "__main__":
    main()

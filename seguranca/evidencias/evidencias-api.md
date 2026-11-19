# Evidências de segurança da API Oásis

Execução real de `seguranca/scripts/coletar_evidencias.py` em 10/11/2026 17:49, contra `http://localhost:8000`.

## 1. SQL injection na busca de pontos

A busca `GET /api/pontos?busca=` recebe texto livre e é o alvo natural de SQL injection. A consulta usa parâmetro vinculado (prepared statement) e escapa os curingas do LIKE.

Pontos aprovados antes dos ataques: **6**

| Ataque enviado em `busca` | Status | Resposta | Resultado |
| --- | --- | --- | --- |
| `' OR '1'='1` | 200 | `[]` | **Protegido** |
| `' OR 1=1 --` | 200 | `[]` | **Protegido** |
| `'; DROP TABLE pontos_apoio; --` | 200 | `[]` | **Protegido** |
| `%' UNION SELECT id, apelido, perfil, bairro FROM usuarios --` | 200 | `[]` | **Protegido** |
| `%` | 200 | `[]` | **Protegido** |

Pontos aprovados depois: **6** (a tabela continua intacta: **Protegido**).

## 2. LFI / path traversal na página pública

A página pública é servida pelo StaticFiles do Starlette, que resolve o caminho e recusa qualquer arquivo fora da pasta `web/`. Os segredos ficam fora da pasta do site (`C:\oasis\config`).

| Caminho pedido (cru, sem normalizar) | Status | Vazou algo? | Resultado |
| --- | --- | --- | --- |
| `/../../etc/passwd` | 404 | não | **Protegido** |
| `/..%2f..%2f..%2fetc%2fpasswd` | 404 | não | **Protegido** |
| `/%2e%2e/%2e%2e/etc/passwd` | 404 | não | **Protegido** |
| `/..\..\windows\win.ini` | 404 | não | **Protegido** |
| `/estilo.css/../../oasis_api/config.py` | 404 | não | **Protegido** |
| `/....//....//etc/passwd` | 404 | não | **Protegido** |
| `/../config/oasis.env` | 404 | não | **Protegido** |

## 3. Controle de acesso das rotas do posto

Aprovar ponto, cadastrar estação, enviar leitura por HTTP, ver pendentes e consultar usuário pedem o cabeçalho `X-Chave-Posto`, comparado em tempo constante (`hmac.compare_digest`).

| Pedido | Chave | Status | Resultado |
| --- | --- | --- | --- |
| `GET /api/pontos?status=Pendente` | sem chave | 401 | **Protegido** |
| `GET /api/pontos?status=Pendente` | `chute` | 401 | **Protegido** |
| `PATCH /api/pontos/1/status` | `chute` | 401 | **Protegido** |
| `POST /api/estacoes` | sem chave | 401 | **Protegido** |
| `GET /api/usuarios/1` | sem chave | 401 | **Protegido** |
| `GET /api/usuarios/2` | sem chave | 401 | **Protegido** |
| `GET /api/pontos?status=Pendente` | chave certa | 200 | **Acesso liberado** |

A consulta de usuário pede a chave porque os ids são sequenciais: sem ela, qualquer pessoa percorreria 1, 2, 3... e montaria uma lista de idosos por bairro (enumeração para OSINT).

## 4. Validação de entrada e mensagens de erro

| Entrada maliciosa ou impossível | Status | Trecho da resposta | Resultado |
| --- | --- | --- | --- |
| JSON quebrado | 400 | `{"type":"about:blank","title":"Dados inválidos","status":400,"detail":"Confira os campos indicados em 'erros'. ...` | **Protegido** |
| Leitura de 85 °C (sensor falso) | 400 | `{"type":"about:blank","title":"Regra de negócio violada","status":400,"detail":"Temperatura fora da faixa acei ...` | **Protegido** |
| Umidade de 140% | 400 | `{"type":"about:blank","title":"Regra de negócio violada","status":400,"detail":"Umidade fora da faixa aceita ( ...` | **Protegido** |
| NaN na previsão | 400 | `{"type":"about:blank","title":"Dados inválidos","status":400,"detail":"Confira os campos indicados em 'erros'. ...` | **Protegido** |
| Apelido com 5.000 letras | 400 | `{"type":"about:blank","title":"Dados inválidos","status":400,"detail":"Confira os campos indicados em 'erros'. ...` | **Protegido** |
| Ponto em Paris | 400 | `{"type":"about:blank","title":"Regra de negócio violada","status":400,"detail":"O ponto precisa ficar dentro d ...` | **Protegido** |

Nenhuma resposta traz pilha de chamadas, SQL ou caminho de arquivo: os erros saem no formato Problem Details (RFC 9457).

## 5. Cabeçalhos de segurança da página pública

`GET /` respondeu 200 com:

```
content-security-policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'
x-content-type-options: nosniff
x-frame-options: DENY
referrer-policy: no-referrer
server: (ausente)
```

A política de conteúdo só permite scripts do próprio site (barra XSS com script de terceiros), `DENY` impede a página dentro de um iframe (clickjacking) e o servidor não se identifica.

## 6. Leituras forjadas no broker MQTT

O broker é público: quem descobrir o tópico pode publicar. Cada leitura precisa de assinatura HMAC-SHA256 com a chave da estação, horário recente (5 min) e número crescente (anti-replay), além das faixas válidas de temperatura e umidade.

| Mensagem publicada | Esperado | Aceitas | Rejeitadas | Resultado |
| --- | --- | --- | --- | --- |
| Leitura legítima, assinada | aceitar | +1 | +0 | **Protegido** |
| Replay: a mesma mensagem de novo | recusar | +0 | +1 | **Protegido** |
| Sem assinatura (45 °C para causar pânico) | recusar | +0 | +1 | **Protegido** |
| Assinada com chave errada | recusar | +0 | +1 | **Protegido** |
| Valor trocado depois de assinar (12 °C) | recusar | +0 | +1 | **Protegido** |
| Mensagem antiga (15 min) | recusar | +0 | +1 | **Protegido** |
| Código diferente do tópico | recusar | +0 | +1 | **Protegido** |
| Mensagem gigante (600 bytes) | recusar | +0 | +1 | **Protegido** |
| Assinada, mas 85 °C (fora da faixa) | recusar | +0 | +1 | **Protegido** |

Motivos registrados no log da API:

```
2026-11-10 17:49:05,429 WARNING oasis.mqtt: Leitura MQTT rejeitada (oasis-rm560760/estacoes/EST-VM-01/leituras): mensagem repetida (replay)
2026-11-10 17:49:06,935 WARNING oasis.mqtt: Leitura MQTT rejeitada (oasis-rm560760/estacoes/EST-VM-01/leituras): mensagem sem assinatura
2026-11-10 17:49:08,442 WARNING oasis.mqtt: Leitura MQTT rejeitada (oasis-rm560760/estacoes/EST-VM-01/leituras): assinatura inválida
2026-11-10 17:49:09,948 WARNING oasis.mqtt: Leitura MQTT rejeitada (oasis-rm560760/estacoes/EST-VM-01/leituras): assinatura inválida
2026-11-10 17:49:11,455 WARNING oasis.mqtt: Leitura MQTT rejeitada (oasis-rm560760/estacoes/EST-VM-01/leituras): horário fora da janela (mensagem antiga ou relógio errado)
2026-11-10 17:49:12,961 WARNING oasis.mqtt: Leitura MQTT rejeitada (oasis-rm560760/estacoes/EST-XX-99/leituras): código da mensagem diferente do tópico
2026-11-10 17:49:14,468 WARNING oasis.mqtt: Leitura MQTT rejeitada (oasis-rm560760/estacoes/EST-VM-01/leituras): mensagem grande demais
2026-11-10 17:49:15,976 WARNING oasis.mqtt: Leitura MQTT rejeitada (oasis-rm560760/estacoes/EST-VM-01/leituras): Temperatura fora da faixa aceita (-10 a 60 °C).
```


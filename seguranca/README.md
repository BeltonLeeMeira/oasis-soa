# Oásis · Gestão de Riscos (Cybersecurity)

**Integrante:** Belton Lee Carr De Muzio Meira · RM560760 · 3ESPA

O relatório completo (ativos, agentes de ameaça, 10 cenários de ataque, matriz de risco, controles e evidências) está em [`relatorio-gestao-de-riscos.pdf`](relatorio-gestao-de-riscos.pdf). Esta pasta guarda o que comprova o relatório: o script de ataque e as saídas reais. Os controles estão no código desta API (`oasis_api/seguranca.py`, `tests/test_seguranca.py`), e o servidor está em [oasis-operating-systems](https://github.com/BeltonLeeMeira/oasis-operating-systems).

## Resumo

| | |
| --- | --- |
| Ativos mapeados | 9, com destaque para a lista de idosos do posto (dado de saúde), que nunca entra na API |
| Agentes de ameaça | 6, do golpista que procura idosos sozinhos (OSINT) ao robô que varre a internet |
| Cenários de ataque | 10: SQL injection, LFI, leitura falsa no MQTT, enumeração de usuários, vazamento do arquivo do posto, acesso indevido, ponto falso, portas expostas, queda no dia de calor e vazamento de detalhes técnicos |
| Antes dos controles | 3 críticos, 6 altos, 1 médio |
| Depois dos controles | 6 baixos, 4 médios, nenhum alto ou crítico |

## Como a rubrica foi atendida

| Critério | Onde está |
| --- | --- |
| Mapeamento de ativos e ameaças (2,5) | Seções 3 e 4 do relatório |
| Análise de vulnerabilidades e riscos (3,0) | Seções 5 e 6: cenários por tecnologia, probabilidade × impacto, matriz antes e depois, OWASP Top 10:2025 |
| Definição de controles (2,5) | Seção 7: 14 controles implementados, 5 propostos e as decisões de Security by Design |
| Evidências técnicas (2,0) | Seções 8 e 9, com as saídas desta pasta e os prints da VM |

## Evidências desta pasta

| Arquivo | O que prova |
| --- | --- |
| [`evidencias/evidencias-api.md`](evidencias/evidencias-api.md) | Execução real dos ataques: SQL injection, path traversal, rotas do posto sem chave, entradas maliciosas, cabeçalhos e leituras MQTT forjadas |
| [`evidencias/postgresql-parametros.txt`](evidencias/postgresql-parametros.txt) | Log do PostgreSQL mostrando o prepared statement: a consulta com `$1` e `$2` e o ataque chegando como valor |
| [`evidencias/pytest-seguranca.txt`](evidencias/pytest-seguranca.txt) | Os 26 testes automáticos de segurança e MQTT passando |
| [`evidencias/painel-do-posto-cofre.txt`](evidencias/painel-do-posto-cofre.txt) | Testes do arquivo cifrado do Painel do Posto |

## Rodar os ataques de novo

Com a API no ar (local ou no servidor) e o mesmo broker MQTT que ela usa:

```powershell
cd seguranca\scripts
pip install paho-mqtt
python coletar_evidencias.py --base-url http://localhost:8000 --chave-posto SUA_CHAVE `
    --mqtt-host broker.hivemq.com --hmac-chave oasis-demo-2026-troque-esta-chave `
    --log-api ..\..\api.log
```

O script não altera dados reais: os ataques de SQL injection só leem, e as leituras MQTT válidas são de teste. No fim, ele mostra quantos testes falharam (o esperado é zero).

### Log do PostgreSQL (prepared statement)

No `psql` como `postgres`, ligue o log de comandos só durante o teste:

```sql
ALTER SYSTEM SET log_statement = 'all';
SELECT pg_reload_conf();
-- faça o pedido GET /api/pontos?busca=' OR '1'='1 e veja o log em
-- C:\Program Files\PostgreSQL\17\data\log
ALTER SYSTEM RESET log_statement;
SELECT pg_reload_conf();
```

### Portas do servidor

O teste de portas feito do PC e o `netstat` do servidor estão na seção 9 do relatório.

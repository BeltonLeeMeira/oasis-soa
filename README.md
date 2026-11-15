# Oásis · API (Arquitetura Orientada a Serviços e Web Services)

## Ficha da CitizenTech

|Campo|Resposta|
|-|-|
|**Nome da CitizenTech**|Oásis|
|**Equipe**|Belton Lee Carr De Muzio Meira · RM560760 · 3ESPA (equipe individual)|
|**Cidade e bairro**|São Paulo, Vila Mariana|
|**Cidadão beneficiado**|Idosos que moram sozinhos e trabalhadores de rua (ambulantes, entregadores, garis)|
|**Problema, em uma frase**|Nos dias de calor extremo, idosos e trabalhadores de rua não ficam sabendo a tempo que o risco está alto nem onde há água e sombra por perto.|
|**Como funciona**|Estações com sensor medem temperatura e umidade e calculam o índice de calor. Um modelo treinado com 11 anos de dados do INMET prevê se amanhã será dia de risco. O app avisa e mostra os pontos de água e sombra mais próximos, e o posto comunitário valida os pontos e prioriza quem acompanhar nos dias críticos.|
|**O que cada parte faz**|API `oasis-soa` (SOA) guarda e serve os dados e a página pública · Modelo `oasis-ia-ml` (IA \& ML) prevê o risco de amanhã · Painel do Posto `oasis-csharp` (C#) aprova pontos e organiza a busca ativa · Servidor `oasis-operating-systems` (Operating Systems) hospeda a API no IIS · App (Mobile) é a porta do cidadão · Estação ESP32 (Physical) mede e sinaliza no local · Relatório de riscos (Cyber) protege a solução · ArchiMate (Testing) descreve a arquitetura|
|**Link do repositório**|https://github.com/BeltonLeeMeira/oasis-soa|
|**Indicador de impacto**|Percentual dos dias de risco avisados na véspera (recall do modelo: 85% no teste, contra 49% sem o modelo) e percentual das pessoas acompanhadas contatadas até 12h nos dias de risco (meta: 100%)|
|**ODS conectados**|3 (saúde: alerta precoce, meta 3.d) · 10 (redução das desigualdades, meta 10.2) · 11 (cidades: espaços públicos acessíveis, meta 11.7) · 13 (clima: resiliência e alerta precoce, metas 13.1 e 13.3)|

Backend da CitizenTech **Oásis**: guarda os pontos de água e sombra, recebe as leituras das estações, calcula o risco de calor, abre alertas e serve a previsão do modelo de IA. App, Painel do Posto, estação ESP32 e página pública usam todos esta mesma API.

**Integrante:** Belton Lee Carr De Muzio Meira · RM560760 · 3ESPA

|||
|-|-|
|Linguagem|Python 3.13|
|Framework|FastAPI (REST + documentação OpenAPI em `/docs`)|
|Banco|PostgreSQL 16 ou 17, via SQLAlchemy 2 e driver psycopg 3|
|Migrações|Alembic (3 migrações em sequência)|
|Mensageria|MQTT (paho-mqtt) para receber as leituras do ESP32|
|Testes|72 testes automáticos (pytest) + coleção do Insomnia com 31 pedidos|

## Como a rubrica foi atendida

|Critério|Onde está|
|-|-|
|**Estruturação do domínio (3,0)**|`oasis\_api/dominio/`: enums, regras e erros sem dependência de banco ou HTTP. `servicos.py` traz os casos de uso. `rotas/` é só a camada HTTP.|
|**Conexão com banco (3,0)**|`oasis\_api/infra/banco.py` (engine, pool, reconexão automática), `infra/tabelas.py` (mapeamento), `infra/repositorios.py` (todas as consultas). A URL vem de variável de ambiente, nunca do código.|
|**Migrações (2,5)**|`migrations/versions/`: `0001\_inicial` → `0002\_status\_ponto` (com migração de dados: pontos antigos viram Aprovado) → `0003\_alertas\_previsoes`. Sobem e descem; o `alembic check` não acha diferença entre código e banco. Seed em `oasis\_api/seed.py`.|
|**Testes manuais (1,5)**|`insomnia/oasis-insomnia.json`: 31 pedidos em ordem, com sucesso e erro (400, 401, 404, 409, 422). Respostas reais de uma execução completa em `evidencias/execucao-insomnia.md`.|

## Arquitetura em camadas

```
api/
├── oasis\_api/
│   ├── dominio/          regras de negócio puras
│   │   ├── enums.py           Perfil, TipoPonto, StatusPonto, NivelRisco, OrigemAlerta
│   │   ├── indice\_calor.py    fórmula da NOAA e faixas de risco
│   │   ├── regras.py          leitura válida, alerta, ponto em SP, status, atributos da IA
│   │   └── erros.py           erros do domínio (sem HTTP)
│   ├── servicos.py       casos de uso (uma transação por operação)
│   ├── infra/            banco, tabelas, repositórios, coletor MQTT, modelo de IA
│   ├── rotas/            endpoints REST, um arquivo por recurso
│   ├── esquemas.py       DTOs de entrada e saída (camelCase no JSON)
│   ├── erros\_http.py     erros no formato Problem Details (RFC 9457)
│   ├── seguranca.py      chave do posto e cabeçalhos de segurança
│   ├── web/              página pública (a aplicação web hospedada no IIS)
│   ├── seed.py           dados de demonstração
│   └── ferramentas/      simulador de estação MQTT
├── migrations/           Alembic
├── tests/                pytest
├── insomnia/             coleção para importar no Insomnia
├── evidencias/           respostas reais e roteiro de prints
└── deploy/web.config     hospedagem no IIS
```

## Rotas

|Método e rota|Quem usa|O que faz|
|-|-|-|
|`POST /api/usuarios`|App|Identificação (apelido, perfil, bairro)|
|`GET /api/usuarios/{id}`|Painel, Insomnia|Consulta um usuário (pede `X-Chave-Posto`: ids sequenciais não podem ser percorridos por qualquer um)|
|`GET /api/pontos?tipo=\&bairro=\&busca=\&lat=\&lon=\&raio=`|App, página|Pontos aprovados, por distância quando há lat/lon|
|`GET /api/pontos?status=Pendente`|Painel|Fila de moderação (pede `X-Chave-Posto`)|
|`GET /api/pontos/{id}`|App|Detalhe|
|`POST /api/pontos`|App|Sugere ponto (entra Pendente)|
|`PATCH /api/pontos/{id}/status`|Painel|Aprova ou rejeita (pede `X-Chave-Posto`)|
|`GET /api/estacoes` · `POST /api/estacoes`|Painel|Estações (o POST pede `X-Chave-Posto`)|
|`GET /api/estacoes/{id}/leituras`|App, Painel|Histórico da estação|
|`POST /api/leituras`|Insomnia, plano B|Leitura por HTTP (pede `X-Chave-Posto`)|
|`GET /api/risco/agora`|App, Painel, página|Última leitura de cada estação, com índice e nível|
|`GET /api/alertas?ativos=true`|App, Painel, página|Alertas ativos (ou histórico com `false`)|
|`GET /api/previsoes/amanha`|App, Painel, página|Modelo de IA com as leituras de hoje|
|`POST /api/previsoes/simular`|Insomnia|Testa o modelo com um dia digitado|
|`GET /health`|Monitoramento|Banco, MQTT e modelo|

A estação ESP32 não usa HTTP: publica no tópico MQTT `oasis-rm560760/estacoes/{codigo}/leituras`, e a API assina esse tópico (ver `infra/mqtt\_coletor.py` e parte `iot` do projeto).

## Como rodar

Pré-requisitos: **Python 3.13** e **PostgreSQL 16 ou 17**.

1. Crie o banco (no `psql` ou no pgAdmin):

```sql
   CREATE USER oasis WITH PASSWORD 'sua\_senha';
   CREATE DATABASE oasis OWNER oasis;
   ```

2. Instale e configure:

```powershell
   python -m venv .venv
   .venv\\Scripts\\activate              # Linux/Mac: source .venv/bin/activate
   pip install -r requirements-dev.txt
   copy .env.exemplo .env              # edite a senha do banco e as chaves
   ```

3. Aplique as migrações e o seed:

```powershell
   alembic upgrade head
   python -m oasis\_api.seed
   ```

4. Suba a API:

```powershell
   uvicorn oasis\_api.main:criar\_app --factory --port 8000
   ```

   * Página pública: http://localhost:8000
   * Documentação interativa: http://localhost:8000/docs
5. Sem o Wokwi aberto, simule a estação:

```powershell
   python -m oasis\_api.ferramentas.simular\_estacao --temperatura 34 --umidade 55
   ```

### Testes automáticos

Crie também o banco `oasis\_teste` (mesmo dono) e rode `pytest -v`. Os testes recriam o banco do zero com as migrações (downgrade e upgrade), então também provam que elas funcionam. O teste de integração MQTT só roda se houver um broker em `localhost:1883` (ex.: Mosquitto).

### Testes manuais no Insomnia

1. Insomnia → **Import** → arquivo `insomnia/oasis-insomnia.json`.
2. Escolha o ambiente **Local (uvicorn)** e confira `chave\_posto` com o valor do seu `.env`.
3. Com o banco recém-criado (migrações + seed), rode os pedidos de 01 a 31 na ordem.

## Evidências

`evidencias/execucao-insomnia.md` traz as respostas reais da execução completa da coleção. Para a entrega, tire os prints listados em `evidencias/README.md`.


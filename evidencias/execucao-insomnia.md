# Execução real da coleção do Insomnia

Gerado em 10/11/2026 rodando a API local (uvicorn + PostgreSQL 16 + broker MQTT local), banco recém-migrado e com o seed.
Cada bloco mostra o pedido e a resposta exata da API. Use como referência para as suas capturas de tela no Insomnia.

## 1. Usuários

### 01 · Criar usuário (201)

`POST /api/usuarios`

```json
{
  "apelido": "Dona Cida",
  "perfil": "Idoso",
  "bairro": "Vila Mariana"
}
```

**Resposta: 201**

```json
{
  "id": 1,
  "apelido": "Dona Cida",
  "perfil": "Idoso",
  "bairro": "Vila Mariana",
  "criadoEm": "2026-11-10T17:46:42-03:00"
}
```

### 02 · Criar usuário inválido (400)

`POST /api/usuarios`

```json
{
  "apelido": "A",
  "perfil": "Astronauta"
}
```

**Resposta: 400**

```json
{
  "type": "about:blank",
  "title": "Dados inválidos",
  "status": 400,
  "detail": "Confira os campos indicados em 'erros'.",
  "erros": [
    {
      "campo": "apelido",
      "mensagem": "Use pelo menos 2 caracteres."
    },
    {
      "campo": "perfil",
      "mensagem": "Valor inválido. Use: 'Idoso', 'TrabalhadorDeRua', 'Cuidador' or 'Outro'."
    },
    {
      "campo": "bairro",
      "mensagem": "Campo obrigatório."
    }
  ]
}
```

### 03 · Consultar usuário (200)

`GET /api/usuarios/1`  · cabeçalho `X-Chave-Posto`

**Resposta: 200**

```json
{
  "id": 1,
  "apelido": "Dona Cida",
  "perfil": "Idoso",
  "bairro": "Vila Mariana",
  "criadoEm": "2026-11-10T17:46:42-03:00"
}
```

### 04 · Usuário inexistente (404)

`GET /api/usuarios/9999`  · cabeçalho `X-Chave-Posto`

**Resposta: 404**

```json
{
  "type": "about:blank",
  "title": "Não encontrado",
  "status": 404,
  "detail": "Usuário 9999 não encontrado.",
  "erros": []
}
```

## 2. Pontos de apoio

### 05 · Listar pontos aprovados (200)

`GET /api/pontos`

**Resposta: 200**

```json
[
  {
    "id": 2,
    "nome": "Biblioteca Viriato Corrêa",
    "tipo": "Climatizado",
    "endereco": "Rua Sena Madureira, 298",
    "bairro": "Vila Mariana",
    "latitude": -23.5878,
    "longitude": -46.6334,
    "horario": "Seg a sex, 9h às 18h",
    "status": "Aprovado",
    "criadoEm": "2026-11-10T17:46:35-03:00",
    "distanciaMetros": null
  },
  {
    "id": 5,
    "nome": "Centro Cultural São Paulo",
    "tipo": "Climatizado",
    "endereco": "Rua Vergueiro, 1000",
    "bairro": "Paraíso",
    "latitude": -23.5711,
    "longitude": -46.64,
    "horario": "Ter a dom, 10h às 20h",
    "status": "Aprovado",
    "criadoEm": "2026-11-10T17:46:35-03:00",
    "distanciaMetros": null
  },
  {
    "id": 3,
    "nome": "Parque Ibirapuera",
    "tipo": "Sombra",
    "endereco": "Av. Pedro Álvares Cabral, s/n",
    "bairro": "Vila Mariana",
    "latitude": -23.5874,
    "longitude": -46.6576,
    "horario": "5h às 0h",
    "status": "Aprovado",
    "criadoEm": "2026-11-10T17:46:35-03:00",
    "distanciaMetros": null
  },
  {
    "id": 4,
    "nome": "Parque da Aclimação",
    "tipo": "Sombra",
    "endereco": "Rua Muniz de Souza, 1119",
    "bairro": "Aclimação",
    "latitude": -23.573,
    "longitude": -46.629,
    "horario": "5h às 20h",
    "status": "Aprovado",
    "criadoEm": "2026-11-10T17:46:35-03:00",
    "distanciaMetros": null
  },
  {
    "id": 1,
    "nome": "SESC Vila Mariana",
    "tipo": "Climatizado",
    "endereco": "Rua Pelotas, 141",
    "bairro": "Vila Mariana",
    "latitude": -23.5893,
    "longitude": -46.6352,
    "horario": "Ter a dom, 10h às 21h",
    "status": "Aprovado",
    "criadoEm": "2026-11-10T17:46:35-03:00",
    "distanciaMetros": null
  }
]
```

### 06 · Pontos perto de mim (200)

`GET /api/pontos?lat=-23.5891&lon=-46.6346&raio=3000`

**Resposta: 200**

```json
[
  {
    "id": 1,
    "nome": "SESC Vila Mariana",
    "tipo": "Climatizado",
    "endereco": "Rua Pelotas, 141",
    "bairro": "Vila Mariana",
    "latitude": -23.5893,
    "longitude": -46.6352,
    "horario": "Ter a dom, 10h às 21h",
    "status": "Aprovado",
    "criadoEm": "2026-11-10T17:46:35-03:00",
    "distanciaMetros": 65
  },
  {
    "id": 2,
    "nome": "Biblioteca Viriato Corrêa",
    "tipo": "Climatizado",
    "endereco": "Rua Sena Madureira, 298",
    "bairro": "Vila Mariana",
    "latitude": -23.5878,
    "longitude": -46.6334,
    "horario": "Seg a sex, 9h às 18h",
    "status": "Aprovado",
    "criadoEm": "2026-11-10T17:46:35-03:00",
    "distanciaMetros": 189
  },
  {
    "id": 4,
    "nome": "Parque da Aclimação",
    "tipo": "Sombra",
    "endereco": "Rua Muniz de Souza, 1119",
    "bairro": "Aclimação",
    "latitude": -23.573,
    "longitude": -46.629,
    "horario": "5h às 20h",
    "status": "Aprovado",
    "criadoEm": "2026-11-10T17:46:35-03:00",
    "distanciaMetros": 1879
  },
  {
    "id": 5,
    "nome": "Centro Cultural São Paulo",
    "tipo": "Climatizado",
    "endereco": "Rua Vergueiro, 1000",
    "bairro": "Paraíso",
    "latitude": -23.5711,
    "longitude": -46.64,
    "horario": "Ter a dom, 10h às 20h",
    "status": "Aprovado",
    "criadoEm": "2026-11-10T17:46:35-03:00",
    "distanciaMetros": 2076
  },
  {
    "id": 3,
    "nome": "Parque Ibirapuera",
    "tipo": "Sombra",
    "endereco": "Av. Pedro Álvares Cabral, s/n",
    "bairro": "Vila Mariana",
    "latitude": -23.5874,
    "longitude": -46.6576,
    "horario": "5h às 0h",
    "status": "Aprovado",
    "criadoEm": "2026-11-10T17:46:35-03:00",
    "distanciaMetros": 2351
  }
]
```

### 07 · Filtrar só água (200)

`GET /api/pontos?tipo=Agua`

**Resposta: 200**

```json
[]
```

### 08 · Sugerir ponto novo (201)

`POST /api/pontos`

```json
{
  "nome": "Bebedouro da praça",
  "tipo": "Agua",
  "endereco": "Rua Exemplo, 100",
  "bairro": "Vila Mariana",
  "latitude": -23.588,
  "longitude": -46.634,
  "horario": "6h às 22h",
  "criadoPorId": 1
}
```

**Resposta: 201**

```json
{
  "id": 7,
  "nome": "Bebedouro da praça",
  "tipo": "Agua",
  "endereco": "Rua Exemplo, 100",
  "bairro": "Vila Mariana",
  "latitude": -23.588,
  "longitude": -46.634,
  "horario": "6h às 22h",
  "status": "Pendente",
  "criadoEm": "2026-11-10T17:46:42-03:00",
  "distanciaMetros": null
}
```

### 09 · Ponto fora de São Paulo (400)

`POST /api/pontos`

```json
{
  "nome": "Praia",
  "tipo": "Sombra",
  "endereco": "Av. Atlântica",
  "bairro": "Copacabana",
  "latitude": -22.97,
  "longitude": -43.18
}
```

**Resposta: 400**

```json
{
  "type": "about:blank",
  "title": "Regra de negócio violada",
  "status": 400,
  "detail": "O ponto precisa ficar dentro da cidade de São Paulo.",
  "erros": [
    {
      "campo": "latitude",
      "mensagem": "O ponto precisa ficar dentro da cidade de São Paulo."
    }
  ]
}
```

### 10 · Pendentes sem a chave do posto (401)

`GET /api/pontos?status=Pendente`

**Resposta: 401**

```json
{
  "type": "about:blank",
  "title": "Não autorizado",
  "status": 401,
  "detail": "Esta ação é exclusiva do posto: envie o cabeçalho X-Chave-Posto.",
  "erros": []
}
```

### 11 · Pendentes com a chave do posto (200)

`GET /api/pontos?status=Pendente`  · cabeçalho `X-Chave-Posto`

**Resposta: 200**

```json
[
  {
    "id": 6,
    "nome": "Bebedouro da estação Vila Mariana",
    "tipo": "Agua",
    "endereco": "Rua Domingos de Morais, 1500",
    "bairro": "Vila Mariana",
    "latitude": -23.589,
    "longitude": -46.6347,
    "horario": "Horário do metrô",
    "status": "Pendente",
    "criadoEm": "2026-11-10T17:46:35-03:00",
    "distanciaMetros": null
  },
  {
    "id": 7,
    "nome": "Bebedouro da praça",
    "tipo": "Agua",
    "endereco": "Rua Exemplo, 100",
    "bairro": "Vila Mariana",
    "latitude": -23.588,
    "longitude": -46.634,
    "horario": "6h às 22h",
    "status": "Pendente",
    "criadoEm": "2026-11-10T17:46:42-03:00",
    "distanciaMetros": null
  }
]
```

### 12 · Aprovar ponto 7 (200)

`PATCH /api/pontos/7/status`  · cabeçalho `X-Chave-Posto`

```json
{
  "status": "Aprovado"
}
```

**Resposta: 200**

```json
{
  "id": 7,
  "nome": "Bebedouro da praça",
  "tipo": "Agua",
  "endereco": "Rua Exemplo, 100",
  "bairro": "Vila Mariana",
  "latitude": -23.588,
  "longitude": -46.634,
  "horario": "6h às 22h",
  "status": "Aprovado",
  "criadoEm": "2026-11-10T17:46:42-03:00",
  "distanciaMetros": null
}
```

### 13 · Voltar ponto para Pendente (400)

`PATCH /api/pontos/7/status`  · cabeçalho `X-Chave-Posto`

```json
{
  "status": "Pendente"
}
```

**Resposta: 400**

```json
{
  "type": "about:blank",
  "title": "Regra de negócio violada",
  "status": 400,
  "detail": "Não é possível mudar o ponto de Aprovado para Pendente.",
  "erros": [
    {
      "campo": "status",
      "mensagem": "Não é possível mudar o ponto de Aprovado para Pendente."
    }
  ]
}
```

## 3. Estações e leituras

### 14 · Listar estações (200)

`GET /api/estacoes`

**Resposta: 200**

```json
[
  {
    "id": 1,
    "codigo": "EST-VM-01",
    "nome": "Vila Mariana",
    "latitude": -23.5891,
    "longitude": -46.6346,
    "ativa": true
  }
]
```

### 15 · Cadastrar estação (201)

`POST /api/estacoes`  · cabeçalho `X-Chave-Posto`

```json
{
  "codigo": "EST-VM-02",
  "nome": "Praça da Árvore",
  "latitude": -23.6107,
  "longitude": -46.6383
}
```

**Resposta: 201**

```json
{
  "id": 2,
  "codigo": "EST-VM-02",
  "nome": "Praça da Árvore",
  "latitude": -23.6107,
  "longitude": -46.6383,
  "ativa": true
}
```

### 16 · Cadastrar estação repetida (409)

`POST /api/estacoes`  · cabeçalho `X-Chave-Posto`

```json
{
  "codigo": "EST-VM-02",
  "nome": "Praça da Árvore",
  "latitude": -23.6107,
  "longitude": -46.6383
}
```

**Resposta: 409**

```json
{
  "type": "about:blank",
  "title": "Conflito",
  "status": 409,
  "detail": "Já existe uma estação com o código EST-VM-02.",
  "erros": [
    {
      "campo": "codigo",
      "mensagem": "Já existe uma estação com o código EST-VM-02."
    }
  ]
}
```

### 17 · Leitura de calor forte (201)

`POST /api/leituras`  · cabeçalho `X-Chave-Posto`

```json
{
  "codigo": "EST-VM-01",
  "temperatura": 34.0,
  "umidade": 55.0
}
```

**Resposta: 201**

```json
{
  "id": 1,
  "estacaoId": 1,
  "temperatura": 34.0,
  "umidade": 55.0,
  "indiceCalor": 40.2,
  "nivel": "Perigo",
  "recebidaEm": "2026-11-10T17:46:42-03:00",
  "acaoAlerta": "Abrir"
}
```

### 18 · Leitura impossível (400)

`POST /api/leituras`  · cabeçalho `X-Chave-Posto`

```json
{
  "codigo": "EST-VM-01",
  "temperatura": 75.0,
  "umidade": 55.0
}
```

**Resposta: 400**

```json
{
  "type": "about:blank",
  "title": "Regra de negócio violada",
  "status": 400,
  "detail": "Temperatura fora da faixa aceita (-10 a 60 °C).",
  "erros": [
    {
      "campo": "temperatura",
      "mensagem": "Temperatura fora da faixa aceita (-10 a 60 °C)."
    }
  ]
}
```

### 19 · Histórico da estação (200)

`GET /api/estacoes/1/leituras?limite=20`

**Resposta: 200**

```json
[
  {
    "id": 1,
    "estacaoId": 1,
    "temperatura": 34.0,
    "umidade": 55.0,
    "indiceCalor": 40.2,
    "nivel": "Perigo",
    "recebidaEm": "2026-11-10T17:46:42-03:00"
  }
]
```

## 4. Risco e alertas

### 20 · Risco agora (200)

`GET /api/risco/agora`

**Resposta: 200**

```json
[
  {
    "estacao": "EST-VM-01",
    "nome": "Vila Mariana",
    "temperatura": 34.0,
    "umidade": 55.0,
    "indiceCalor": 40.2,
    "nivel": "Perigo",
    "recebidaEm": "2026-11-10T17:46:42-03:00",
    "atualizada": true
  },
  {
    "estacao": "EST-VM-02",
    "nome": "Praça da Árvore",
    "temperatura": null,
    "umidade": null,
    "indiceCalor": null,
    "nivel": null,
    "recebidaEm": null,
    "atualizada": false
  }
]
```

### 21 · Alertas ativos (200)

`GET /api/alertas?ativos=true`

**Resposta: 200**

```json
[
  {
    "id": 1,
    "estacao": "EST-VM-01",
    "nivel": "Perigo",
    "origem": "Sensor",
    "mensagem": "Perigo: sensação de 40,2 °C em Vila Mariana. Evite o sol, beba água e procure um lugar fresco.",
    "dataAlvo": null,
    "inicio": "2026-11-10T17:46:42-03:00",
    "fim": null
  }
]
```

### 22 · Leitura amena (fecha o alerta) (201)

`POST /api/leituras`  · cabeçalho `X-Chave-Posto`

```json
{
  "codigo": "EST-VM-01",
  "temperatura": 24.0,
  "umidade": 60.0
}
```

**Resposta: 201**

```json
{
  "id": 2,
  "estacaoId": 1,
  "temperatura": 24.0,
  "umidade": 60.0,
  "indiceCalor": 24.0,
  "nivel": "Normal",
  "recebidaEm": "2026-11-10T17:46:42-03:00",
  "acaoAlerta": "Fechar"
}
```

### 23 · Histórico de alertas (200)

`GET /api/alertas?ativos=false`

**Resposta: 200**

```json
[
  {
    "id": 1,
    "estacao": "EST-VM-01",
    "nivel": "Perigo",
    "origem": "Sensor",
    "mensagem": "Perigo: sensação de 40,2 °C em Vila Mariana. Evite o sol, beba água e procure um lugar fresco.",
    "dataAlvo": null,
    "inicio": "2026-11-10T17:46:42-03:00",
    "fim": "2026-11-10T17:46:42-03:00"
  }
]
```

## 5. Previsão (IA)

### 24 · Previsão de amanhã (200)

`GET /api/previsoes/amanha`

**Resposta: 200**

```json
{
  "dataAlvo": "2026-11-11",
  "probabilidade": 0.9971,
  "risco": true,
  "limiar": 0.55,
  "versaoModelo": "rl-2026-11-10",
  "leiturasUsadas": 2,
  "atributos": {
    "temp_max": 34.0,
    "temp_min": 24.0,
    "temp_media": 29.0,
    "umid_media": 57.5,
    "umid_min": 55.0,
    "ic_max": 40.182,
    "dia_sen": -0.761,
    "dia_cos": 0.649
  }
}
```

### 25 · Simular dia quente de janeiro (200)

`POST /api/previsoes/simular`

```json
{
  "tempMax": 34.5,
  "tempMin": 22.0,
  "tempMedia": 27.5,
  "umidMedia": 55,
  "umidMin": 35,
  "icMax": 35.5,
  "dataAlvo": "2027-01-20"
}
```

**Resposta: 200**

```json
{
  "dataAlvo": "2027-01-20",
  "probabilidade": 0.9801,
  "risco": true,
  "limiar": 0.55,
  "versaoModelo": "rl-2026-11-10",
  "leiturasUsadas": 0,
  "atributos": {
    "temp_max": 34.5,
    "temp_min": 22.0,
    "temp_media": 27.5,
    "umid_media": 55.0,
    "umid_min": 35.0,
    "ic_max": 35.5,
    "dia_sen": 0.337,
    "dia_cos": 0.941
  }
}
```

### 26 · Simular dia ameno de julho (200)

`POST /api/previsoes/simular`

```json
{
  "tempMax": 22.0,
  "tempMin": 14.0,
  "tempMedia": 17.5,
  "umidMedia": 75,
  "umidMin": 55,
  "icMax": 21.5,
  "dataAlvo": "2027-07-20"
}
```

**Resposta: 200**

```json
{
  "dataAlvo": "2027-07-20",
  "probabilidade": 0.0012,
  "risco": false,
  "limiar": 0.55,
  "versaoModelo": "rl-2026-11-10",
  "leiturasUsadas": 0,
  "atributos": {
    "temp_max": 22.0,
    "temp_min": 14.0,
    "temp_media": 17.5,
    "umid_media": 75.0,
    "umid_min": 55.0,
    "ic_max": 21.5,
    "dia_sen": -0.311,
    "dia_cos": -0.95
  }
}
```

## 6. Segurança (evidências de Cyber)

### 27 · SQL injection na busca (200, lista vazia)

`GET /api/pontos?busca=' OR '1'='1`

**Resposta: 200**

```json
[]
```

### 28 · DROP TABLE na busca (200, lista vazia)

`GET /api/pontos?busca='; DROP TABLE pontos_apoio; --`

**Resposta: 200**

```json
[]
```

### 29 · Chave do posto errada (401)

`PATCH /api/pontos/1/status`  · cabeçalho `X-Chave-Posto`

```json
{
  "status": "Rejeitado"
}
```

**Resposta: 401**

```json
{
  "type": "about:blank",
  "title": "Não autorizado",
  "status": 401,
  "detail": "Esta ação é exclusiva do posto: envie o cabeçalho X-Chave-Posto.",
  "erros": []
}
```

### 30 · Path traversal (LFI) (404)

`GET /..%2f..%2f..%2fetc%2fpasswd`

**Resposta: 404**

```json
{
  "type": "about:blank",
  "title": "Não encontrado",
  "status": 404,
  "detail": "Recurso não encontrado.",
  "erros": []
}
```

## 7. Saúde

### 31 · Health (200)

`GET /health`

**Resposta: 200**

```json
{
  "status": "ok",
  "banco": "ok",
  "mqtt": "conectado",
  "modelo": "carregado (rl-2026-11-10)",
  "leiturasMqttAceitas": 0,
  "leiturasMqttRejeitadas": 0
}
```

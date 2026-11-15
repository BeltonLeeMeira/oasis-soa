"""Testes de ponta a ponta das rotas, com o banco PostgreSQL de teste."""

import pytest


def _usuario(cliente, apelido="Dona Cida"):
    resposta = cliente.post("/api/usuarios", json={"apelido": apelido, "perfil": "Idoso", "bairro": "Vila Mariana"})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _leitura(cliente, posto, temperatura, umidade, codigo="EST-VM-01"):
    return cliente.post("/api/leituras", json={"codigo": codigo, "temperatura": temperatura, "umidade": umidade}, headers=posto)


# ---------------------------------------------------------------- usuários ---


def test_cria_e_consulta_usuario(cliente, posto):
    criado = _usuario(cliente)
    assert criado["perfil"] == "Idoso" and "criadoEm" in criado
    consulta = cliente.get(f"/api/usuarios/{criado['id']}", headers=posto)
    assert consulta.status_code == 200 and consulta.json()["apelido"] == "Dona Cida"


def test_consulta_de_usuario_sem_chave_e_negada(cliente):
    # Ids são sequenciais: sem a chave, daria para listar apelido, perfil e bairro de todos.
    criado = _usuario(cliente)
    assert cliente.get(f"/api/usuarios/{criado['id']}").status_code == 401


def test_usuario_invalido_devolve_400_com_campos(cliente):
    resposta = cliente.post("/api/usuarios", json={"apelido": "A", "perfil": "Astronauta"})
    assert resposta.status_code == 400
    corpo = resposta.json()
    assert resposta.headers["content-type"].startswith("application/problem+json")
    campos = {e["campo"]: e["mensagem"] for e in corpo["erros"]}
    assert campos["apelido"] == "Use pelo menos 2 caracteres."
    assert campos["bairro"] == "Campo obrigatório."
    assert "perfil" in campos


def test_usuario_inexistente_devolve_404(cliente, posto):
    resposta = cliente.get("/api/usuarios/999", headers=posto)
    assert resposta.status_code == 404 and resposta.json()["title"] == "Não encontrado"


# ------------------------------------------------------------------ pontos ---


def test_lista_publica_mostra_so_aprovados(cliente):
    nomes = [p["nome"] for p in cliente.get("/api/pontos").json()]
    assert nomes == ["Parque Ibirapuera", "SESC Vila Mariana"]


def test_pendentes_exigem_chave_do_posto(cliente, posto):
    assert cliente.get("/api/pontos", params={"status": "Pendente"}).status_code == 401
    resposta = cliente.get("/api/pontos", params={"status": "Pendente"}, headers=posto)
    assert resposta.status_code == 200 and [p["nome"] for p in resposta.json()] == ["Bebedouro sem revisão"]


def test_ordena_por_distancia(cliente):
    pontos = cliente.get("/api/pontos", params={"lat": -23.5891, "lon": -46.6346}).json()
    assert [p["nome"] for p in pontos] == ["SESC Vila Mariana", "Parque Ibirapuera"]
    assert pontos[0]["distanciaMetros"] < pontos[1]["distanciaMetros"]
    perto = cliente.get("/api/pontos", params={"lat": -23.5891, "lon": -46.6346, "raio": 500}).json()
    assert [p["nome"] for p in perto] == ["SESC Vila Mariana"]


def test_ponto_novo_entra_pendente_e_o_posto_aprova(cliente, posto):
    usuario = _usuario(cliente)
    novo = {
        "nome": "Bebedouro da praça", "tipo": "Agua", "endereco": "Rua Exemplo, 100", "bairro": "Vila Mariana",
        "latitude": -23.5880, "longitude": -46.6340, "horario": "6h às 22h", "criadoPorId": usuario["id"],
    }
    criado = cliente.post("/api/pontos", json=novo)
    assert criado.status_code == 201 and criado.json()["status"] == "Pendente"
    ponto_id = criado.json()["id"]
    assert cliente.get(f"/api/pontos/{ponto_id}").status_code == 404  # ainda invisível ao público

    assert cliente.patch(f"/api/pontos/{ponto_id}/status", json={"status": "Aprovado"}).status_code == 401
    aprovado = cliente.patch(f"/api/pontos/{ponto_id}/status", json={"status": "Aprovado"}, headers=posto)
    assert aprovado.status_code == 200 and aprovado.json()["status"] == "Aprovado"
    assert cliente.get(f"/api/pontos/{ponto_id}").status_code == 200

    volta = cliente.patch(f"/api/pontos/{ponto_id}/status", json={"status": "Pendente"}, headers=posto)
    assert volta.status_code == 400 and "Não é possível" in volta.json()["detail"]


def test_ponto_fora_de_sao_paulo_e_recusado(cliente):
    novo = {"nome": "Praia", "tipo": "Sombra", "endereco": "Av. Atlântica", "bairro": "Copacabana", "latitude": -22.97, "longitude": -43.18}
    resposta = cliente.post("/api/pontos", json=novo)
    assert resposta.status_code == 400 and resposta.json()["erros"][0]["campo"] == "latitude"


# ---------------------------------------------------------------- estações ---


def test_cadastro_de_estacao(cliente, posto):
    nova = {"codigo": "EST-VM-02", "nome": "Praça da Árvore", "latitude": -23.6107, "longitude": -46.6383}
    assert cliente.post("/api/estacoes", json=nova).status_code == 401
    assert cliente.post("/api/estacoes", json=nova, headers=posto).status_code == 201
    assert cliente.post("/api/estacoes", json=nova, headers=posto).status_code == 409
    assert cliente.post("/api/estacoes", json={**nova, "codigo": "estacao-2"}, headers=posto).status_code == 400


# ------------------------------------------------------- leituras e alertas ---


def test_leitura_calcula_indice_e_nivel(cliente, posto):
    resposta = _leitura(cliente, posto, 34.0, 55.0)
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["indiceCalor"] == pytest.approx(40.2, abs=0.1)
    assert corpo["nivel"] == "Perigo" and corpo["acaoAlerta"] == "Abrir"
    assert corpo["recebidaEm"].endswith("-03:00")


@pytest.mark.parametrize(("temperatura", "umidade", "campo"), [(75, 50, "temperatura"), (30, 120, "umidade")])
def test_leitura_fora_da_faixa_devolve_400(cliente, posto, temperatura, umidade, campo):
    resposta = _leitura(cliente, posto, temperatura, umidade)
    assert resposta.status_code == 400 and resposta.json()["erros"][0]["campo"] == campo


def test_leitura_exige_estacao_valida_e_ativa(cliente, posto):
    assert _leitura(cliente, posto, 30, 50, codigo="EST-XX-99").status_code == 404
    assert _leitura(cliente, posto, 30, 50, codigo="EST-VM-09").status_code == 400
    assert cliente.post("/api/leituras", json={"codigo": "EST-VM-01", "temperatura": 30, "umidade": 50}).status_code == 401


def test_ciclo_de_vida_do_alerta(cliente, posto):
    assert _leitura(cliente, posto, 31.0, 50.0).json()["acaoAlerta"] == "Abrir"  # Alerta
    assert _leitura(cliente, posto, 34.0, 55.0).json()["acaoAlerta"] == "Escalar"  # Perigo
    alertas = cliente.get("/api/alertas").json()
    assert len(alertas) == 1 and alertas[0]["nivel"] == "Perigo" and alertas[0]["estacao"] == "EST-VM-01"
    assert _leitura(cliente, posto, 24.0, 60.0).json()["acaoAlerta"] == "Fechar"
    assert cliente.get("/api/alertas").json() == []
    historico = cliente.get("/api/alertas", params={"ativos": "false"}).json()
    assert len(historico) == 1 and historico[0]["fim"] is not None


def test_risco_agora_e_historico(cliente, posto):
    sem_leitura = cliente.get("/api/risco/agora").json()
    assert sem_leitura == [{"estacao": "EST-VM-01", "nome": "Vila Mariana", "temperatura": None, "umidade": None, "indiceCalor": None, "nivel": None, "recebidaEm": None, "atualizada": False}]
    _leitura(cliente, posto, 28.0, 60.0)
    _leitura(cliente, posto, 31.0, 50.0)
    agora = cliente.get("/api/risco/agora").json()[0]
    assert agora["nivel"] == "Alerta" and agora["atualizada"] is True
    historico = cliente.get("/api/estacoes/1/leituras", params={"limite": 10}).json()
    assert [h["temperatura"] for h in historico] == [31.0, 28.0]


# ---------------------------------------------------------------- previsões ---


def test_previsao_sem_leituras_devolve_422(cliente):
    resposta = cliente.get("/api/previsoes/amanha")
    if resposta.status_code == 503:
        pytest.skip("modelo de IA ainda não gerado em modelo/")
    assert resposta.status_code == 422


def test_previsao_com_leituras_de_hoje(cliente, posto):
    if not cliente.app.state.modelo.disponivel:
        pytest.skip("modelo de IA ainda não gerado em modelo/")
    for temperatura, umidade in [(24, 70), (31, 45), (34, 40), (29, 55)]:
        _leitura(cliente, posto, temperatura, umidade)
    previsao = cliente.get("/api/previsoes/amanha").json()
    assert 0 <= previsao["probabilidade"] <= 1 and previsao["leiturasUsadas"] == 4
    assert previsao["atributos"]["temp_max"] == 34
    if previsao["risco"]:
        origens = [a["origem"] for a in cliente.get("/api/alertas").json()]
        assert "Previsao" in origens
    # Segunda chamada em menos de 10 minutos reaproveita a mesma previsão.
    assert cliente.get("/api/previsoes/amanha").json() == previsao


def test_simulacao_quente_e_amena(cliente):
    if not cliente.app.state.modelo.disponivel:
        pytest.skip("modelo de IA ainda não gerado em modelo/")
    quente = {"tempMax": 34.5, "tempMin": 22.0, "tempMedia": 27.5, "umidMedia": 55, "umidMin": 35, "icMax": 35.5, "dataAlvo": "2027-01-20"}
    amena = {"tempMax": 22.0, "tempMin": 14.0, "tempMedia": 17.5, "umidMedia": 75, "umidMin": 55, "icMax": 21.5, "dataAlvo": "2027-07-20"}
    p_quente = cliente.post("/api/previsoes/simular", json=quente).json()
    p_amena = cliente.post("/api/previsoes/simular", json=amena).json()
    assert p_quente["probabilidade"] > p_amena["probabilidade"]
    assert p_quente["risco"] is True and p_amena["risco"] is False
    incoerente = cliente.post("/api/previsoes/simular", json={**amena, "tempMin": 30})
    assert incoerente.status_code == 400


# -------------------------------------------------------------------- saúde ---


def test_health(cliente):
    resposta = cliente.get("/health")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "ok" and corpo["banco"] == "ok" and corpo["mqtt"] == "desligado"


def test_pagina_publica(cliente):
    resposta = cliente.get("/")
    assert resposta.status_code == 200 and "Oásis" in resposta.text

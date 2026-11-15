// Página pública do Oásis: só lê a API (mesma origem) e monta a tela.
// Todo texto vindo da API entra com textContent, nunca como HTML (evita XSS).

const NOMES_NIVEL = { Normal: "Normal", Atencao: "Atenção", Alerta: "Alerta", Perigo: "Perigo" };
const NOMES_TIPO = { Agua: "Água", Sombra: "Sombra", Climatizado: "Climatizado" };

function el(tag, classe, texto) {
  const e = document.createElement(tag);
  if (classe) e.className = classe;
  if (texto !== undefined && texto !== null) e.textContent = texto;
  return e;
}

function numero(valor, casas = 1) {
  return valor === null || valor === undefined ? "-" : valor.toFixed(casas).replace(".", ",");
}

function hora(iso) {
  return iso ? new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }) : "-";
}

async function buscar(caminho) {
  const resposta = await fetch(caminho, { headers: { Accept: "application/json" } });
  const corpo = await resposta.json().catch(() => null);
  if (!resposta.ok) {
    const erro = new Error(corpo && corpo.detail ? corpo.detail : `Erro ${resposta.status}`);
    erro.status = resposta.status;
    throw erro;
  }
  return corpo;
}

function substituir(alvo, ...filhos) {
  alvo.replaceChildren(...filhos);
}

async function carregarAgora() {
  const alvo = document.getElementById("agora");
  try {
    const estacoes = await buscar("/api/risco/agora");
    if (estacoes.length === 0) return substituir(alvo, el("p", "vazio", "Nenhuma estação ativa."));
    substituir(alvo, ...estacoes.map((e) => {
      const cartao = el("article", "cartao");
      const nivel = e.nivel || "Sem";
      cartao.append(el("h3", null, e.nome), el("span", `nivel nivel-${nivel}`, e.nivel ? NOMES_NIVEL[e.nivel] : "Sem leitura"));
      if (e.recebidaEm) {
        cartao.append(
          el("p", "grande", `${numero(e.indiceCalor)} °C`),
          el("p", "detalhe", `Sensação térmica. Temperatura ${numero(e.temperatura)} °C, umidade ${numero(e.umidade, 0)}%.`),
          el("p", "detalhe", `Leitura das ${hora(e.recebidaEm)}${e.atualizada ? "" : " (desatualizada)"}`)
        );
      } else {
        cartao.append(el("p", "detalhe", "Esta estação ainda não mandou leituras."));
      }
      return cartao;
    }));
  } catch (erro) {
    substituir(alvo, el("p", "erro", `Não foi possível carregar o risco agora: ${erro.message}`));
  }
}

async function carregarAmanha() {
  const alvo = document.getElementById("amanha");
  try {
    const p = await buscar("/api/previsoes/amanha");
    const caixa = el("div", p.risco ? "risco-sim" : "risco-nao");
    const dia = new Date(`${p.dataAlvo}T12:00:00`).toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "2-digit" });
    caixa.append(
      el("p", "grande", p.risco ? "Risco de calor forte" : "Sem risco previsto"),
      el("p", "detalhe", `Previsão para ${dia}: ${Math.min(99, Math.round(p.probabilidade * 100))}% de chance de o índice de calor chegar a 32 °C.`)
    );
    substituir(alvo, caixa);
  } catch (erro) {
    const texto = erro.status === 422 ? "A previsão aparece depois da primeira leitura do dia." : `Previsão indisponível: ${erro.message}`;
    substituir(alvo, el("p", erro.status === 422 ? "vazio" : "erro", texto));
  }
}

async function carregarAlertas() {
  const alvo = document.getElementById("alertas");
  try {
    const alertas = await buscar("/api/alertas?ativos=true");
    if (alertas.length === 0) return substituir(alvo, el("li", "vazio", "Nenhum alerta ativo."));
    substituir(alvo, ...alertas.map((a) => {
      const item = el("li");
      item.append(el("span", `nivel nivel-${a.nivel}`, NOMES_NIVEL[a.nivel]), el("strong", null, a.mensagem), el("span", "detalhe", `Desde ${hora(a.inicio)}`));
      return item;
    }));
  } catch (erro) {
    substituir(alvo, el("li", "erro", `Não foi possível carregar os alertas: ${erro.message}`));
  }
}

async function carregarPontos() {
  const alvo = document.getElementById("pontos");
  try {
    const pontos = await buscar("/api/pontos");
    if (pontos.length === 0) return substituir(alvo, el("li", "vazio", "Nenhum ponto aprovado ainda."));
    substituir(alvo, ...pontos.map((p) => {
      const item = el("li");
      const mapa = el("a", null, "Como chegar");
      mapa.href = `https://www.google.com/maps/search/?api=1&query=${p.latitude},${p.longitude}`;
      mapa.target = "_blank";
      mapa.rel = "noopener noreferrer";
      item.append(
        el("strong", null, `${p.nome} · ${NOMES_TIPO[p.tipo]}`),
        el("span", "detalhe", `${p.endereco}, ${p.bairro}${p.horario ? ` · ${p.horario}` : ""}`),
        el("br"),
        mapa
      );
      return item;
    }));
  } catch (erro) {
    substituir(alvo, el("li", "erro", `Não foi possível carregar os pontos: ${erro.message}`));
  }
}

async function atualizar() {
  await Promise.all([carregarAgora(), carregarAmanha(), carregarAlertas(), carregarPontos()]);
  document.getElementById("atualizado").textContent = new Date().toLocaleTimeString("pt-BR");
}

atualizar();
setInterval(atualizar, 30000);

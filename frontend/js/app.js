/* =========================================================================
   app.js — comunicação do frontend com a API Flask.
   JavaScript puro, sem framework, conforme o escopo do MVP.
   ========================================================================= */

const API = "/api";

// Referências dos elementos da página.
const campoBusca = document.getElementById("campo-busca");
const listaSugestoes = document.getElementById("sugestoes");
const resultadoBusca = document.getElementById("resultado-busca");
const campoTag = document.getElementById("campo-tag");
const campoDescricao = document.getElementById("campo-descricao");
const btnAdicionar = document.getElementById("btn-adicionar");
const aviso = document.getElementById("aviso");
const corpoTabela = document.getElementById("corpo-tabela");
const arvoreEl = document.getElementById("arvore");
const btnCenario = document.getElementById("btn-cenario");
const btnLimpar = document.getElementById("btn-limpar");

/* -------------------------------------------------------------------------
   DEBOUNCE
   Evita disparar uma requisição a cada tecla digitada. A função só é
   executada depois que o usuário para de digitar pelo tempo definido.
   Sem isso, digitar "estrutura" geraria 9 requisições em sequência.
   ------------------------------------------------------------------------- */
function debounce(fn, atraso) {
  let timer = null;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), atraso);
  };
}

// Mostra uma mensagem na área de aviso do formulário.
function mostrarAviso(texto, tipo) {
  aviso.textContent = texto;
  aviso.className = "aviso " + (tipo || "");
}

/* -------------------------------------------------------------------------
   RF05 — AUTOCOMPLETAÇÃO
   Consulta /api/tags/search?q= e monta a lista de sugestões.
   ------------------------------------------------------------------------- */
async function buscarSugestoes(prefixo) {
  if (!prefixo.trim()) {
    listaSugestoes.classList.remove("visivel");
    listaSugestoes.innerHTML = "";
    return;
  }

  try {
    const resp = await fetch(`${API}/tags/search?q=${encodeURIComponent(prefixo)}&limit=10`);
    const dados = await resp.json();
    renderizarSugestoes(dados.suggestions);
  } catch (erro) {
    console.error("Falha na busca por prefixo:", erro);
  }
}

function renderizarSugestoes(sugestoes) {
  listaSugestoes.innerHTML = "";

  if (!sugestoes || sugestoes.length === 0) {
    listaSugestoes.classList.remove("visivel");
    return;
  }

  sugestoes.forEach((item) => {
    const li = document.createElement("li");
    li.innerHTML =
      `${escaparHtml(item.tag)}<span class="contador">${item.usage_count} uso(s)</span>`;
    // Ao clicar na sugestão, preenchemos o campo e mostramos a busca exata.
    li.addEventListener("click", () => {
      campoBusca.value = item.tag;
      listaSugestoes.classList.remove("visivel");
      buscaExata(item.tag);
    });
    listaSugestoes.appendChild(li);
  });

  listaSugestoes.classList.add("visivel");
}

/* -------------------------------------------------------------------------
   RF04 — BUSCA EXATA
   ------------------------------------------------------------------------- */
async function buscaExata(tag) {
  const resp = await fetch(`${API}/tags/${encodeURIComponent(tag)}`);
  if (resp.ok) {
    const dados = await resp.json();
    resultadoBusca.innerHTML =
      `Encontrada: <strong>${escaparHtml(dados.tag.tag)}</strong> — ` +
      `${dados.tag.usage_count} uso(s).`;
  } else {
    resultadoBusca.textContent = "Tag não encontrada.";
  }
}

/* -------------------------------------------------------------------------
   RF01 — CADASTRO DE TAG
   ------------------------------------------------------------------------- */
async function adicionarTag() {
  const tag = campoTag.value.trim();
  const descricao = campoDescricao.value.trim();

  if (!tag) {
    mostrarAviso("Digite uma tag antes de adicionar.", "erro");
    return;
  }

  const resp = await fetch(`${API}/tags`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tag: tag, description: descricao }),
  });

  const dados = await resp.json();

  if (!resp.ok) {
    // Aqui aparecem as violações de regra de negócio (ex.: RN04).
    mostrarAviso(dados.error, "erro");
    return;
  }

  if (dados.created) {
    mostrarAviso(`Tag "${dados.tag.tag}" criada.`, "ok");
  } else {
    // RF08: tag duplicada não cria nó novo, apenas incrementa o contador.
    mostrarAviso(
      `A tag "${dados.tag.tag}" já existia — contador incrementado para ${dados.tag.usage_count}.`,
      "info"
    );
  }

  campoTag.value = "";
  campoDescricao.value = "";
  await atualizarTudo();
}

/* -------------------------------------------------------------------------
   RF06 / RF07 — LISTAGEM E AÇÕES
   ------------------------------------------------------------------------- */
async function carregarTags() {
  const resp = await fetch(`${API}/tags`);
  const dados = await resp.json();

  corpoTabela.innerHTML = "";

  if (dados.tags.length === 0) {
    corpoTabela.innerHTML =
      '<tr><td colspan="4" style="color:#98a3ba">Nenhuma tag cadastrada ainda.</td></tr>';
    return;
  }

  dados.tags.forEach((item) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${escaparHtml(item.tag)}</strong></td>
      <td>${escaparHtml(item.description || "—")}</td>
      <td>${item.usage_count}</td>
      <td class="acoes">
        <button data-acao="use"    data-tag="${escaparHtml(item.tag)}" title="Associar a um novo tópico">+</button>
        <button data-acao="unuse"  data-tag="${escaparHtml(item.tag)}" title="Remover associação de um tópico">−</button>
        <button data-acao="delete" data-tag="${escaparHtml(item.tag)}" class="remover" title="Excluir tag">excluir</button>
      </td>`;
    corpoTabela.appendChild(tr);
  });
}

// Delegação de evento: um único listener para todos os botões da tabela.
corpoTabela.addEventListener("click", async (evento) => {
  const botao = evento.target.closest("button");
  if (!botao) return;

  const { acao, tag } = botao.dataset;

  if (acao === "delete") {
    const resp = await fetch(`${API}/tags/${encodeURIComponent(tag)}`, { method: "DELETE" });
    const dados = await resp.json();
    // Se a RN02 bloquear a remoção, a mensagem do backend aparece aqui.
    mostrarAviso(resp.ok ? `Tag "${tag}" removida.` : dados.error, resp.ok ? "ok" : "erro");
  } else {
    await fetch(`${API}/tags/${encodeURIComponent(tag)}/${acao}`, { method: "POST" });
    mostrarAviso("", "");
  }

  await atualizarTudo();
});

/* -------------------------------------------------------------------------
   RF09 / RF10 — ÁREA ACADÊMICA
   ------------------------------------------------------------------------- */
async function carregarDebug() {
  const [respMetricas, respArvore] = await Promise.all([
    fetch(`${API}/metrics`),
    fetch(`${API}/avl`),
  ]);

  const metricas = await respMetricas.json();
  const arvore = await respArvore.json();

  document.getElementById("m-altura").textContent = metricas.height;
  document.getElementById("m-nos").textContent = metricas.node_count;
  document.getElementById("m-rotacoes").textContent = metricas.rotations;
  document.getElementById("m-balanceada").textContent = metricas.is_balanced ? "OK" : "FALHA";

  arvoreEl.textContent = arvore.text;
}

// Recarrega listagem e área de debug de uma vez só.
async function atualizarTudo() {
  await Promise.all([carregarTags(), carregarDebug()]);
}

// Evita injeção de HTML ao exibir valores vindos da API.
function escaparHtml(texto) {
  return String(texto)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/* -------------------------------------------------------------------------
   EVENTOS
   ------------------------------------------------------------------------- */
// Debounce de 250 ms: rápido o suficiente para parecer instantâneo e
// econômico o suficiente para não inundar o backend.
campoBusca.addEventListener("input", debounce((e) => buscarSugestoes(e.target.value), 250));

campoBusca.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    listaSugestoes.classList.remove("visivel");
    buscaExata(campoBusca.value.trim());
  }
});

// Fecha a lista de sugestões ao clicar fora dela.
document.addEventListener("click", (e) => {
  if (!e.target.closest(".campo-busca")) listaSugestoes.classList.remove("visivel");
});

btnAdicionar.addEventListener("click", adicionarTag);
campoTag.addEventListener("keydown", (e) => { if (e.key === "Enter") adicionarTag(); });

btnCenario.addEventListener("click", async () => {
  // Carrega o cenário obrigatório do levantamento (aula1..aula20).
  await fetch(`${API}/seed`, { method: "POST" });
  mostrarAviso("Cenário aula1..aula20 carregado. Veja a altura na área de debug.", "info");
  await atualizarTudo();
});

btnLimpar.addEventListener("click", async () => {
  await fetch(`${API}/reset`, { method: "POST" });
  mostrarAviso("Dicionário limpo.", "info");
  await atualizarTudo();
});

// Carga inicial da página.
atualizarTudo();

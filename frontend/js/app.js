/* =============================================================================
   app.js — orquestra a interface. Toda a comunicação com o backend passa
   por API (api.js); todo o desenho da árvore passa por Visualizador
   (arvore.js); todo o histórico passa por Logs (logs.js).
   ========================================================================== */

// ---------------- Referências ----------------
const btnMenu = document.getElementById("btn-menu");
const sidebar = document.getElementById("sidebar");
const itensNav = document.querySelectorAll(".item-nav");
const secoes = document.querySelectorAll(".secao");

const statusApiEl = document.getElementById("status-api");
const statusBalanceamentoEl = document.getElementById("status-balanceamento");

const campoBusca = document.getElementById("campo-busca");
const listaSugestoes = document.getElementById("sugestoes");
const resultadoBusca = document.getElementById("resultado-busca");

const campoTag = document.getElementById("campo-tag");
const campoDescricao = document.getElementById("campo-descricao");
const btnAdicionar = document.getElementById("btn-adicionar");
const aviso = document.getElementById("aviso");
const corpoTabela = document.getElementById("corpo-tabela");

const btnCenario = document.getElementById("btn-cenario");
const btnLimpar = document.getElementById("btn-limpar");
const resultadoCenario = document.getElementById("resultado-cenario");

const containerSvg = document.getElementById("container-svg");
const tooltipNo = document.getElementById("tooltip-no");
const avisoRotacao = document.getElementById("aviso-rotacao");

const modalRemover = document.getElementById("modal-remover");
const modalTexto = document.getElementById("modal-texto");
const modalCancelar = document.getElementById("modal-cancelar");
const modalConfirmar = document.getElementById("modal-confirmar");

let ultimasMetricas = null;
let tagPendenteRemocao = null;

Visualizador.iniciar(containerSvg, tooltipNo);
Logs.iniciar(document.getElementById("lista-logs"), document.getElementById("lista-logs-resumo"));

// ---------------- Utilitários ----------------
function debounce(fn, atraso) {
  let timer = null;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), atraso);
  };
}

function escaparHtml(texto) {
  return String(texto)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function mostrarAviso(texto, tipo) {
  aviso.textContent = texto;
  aviso.className = "aviso " + (tipo || "");
}

function definirIndicador(el, estado, textoExtra) {
  el.classList.remove("ok", "erro", "alerta");
  if (estado) el.classList.add(estado);
  if (textoExtra !== undefined) {
    el.innerHTML = `<span class="ponto"></span> <span>${textoExtra}</span>`;
  }
}

// ---------------- Navegação (sidebar / seções) ----------------
function navegarPara(idSecao) {
  secoes.forEach((s) => s.classList.toggle("ativa", s.id === `secao-${idSecao}`));
  itensNav.forEach((item) => {
    const ativo = item.dataset.secao === idSecao;
    item.classList.toggle("ativo", ativo);
    if (ativo) item.setAttribute("aria-current", "page"); else item.removeAttribute("aria-current");
  });
  fecharSidebarMobile();
}

itensNav.forEach((item) => item.addEventListener("click", () => navegarPara(item.dataset.secao)));

document.querySelectorAll("[data-ir-para]").forEach((el) =>
  el.addEventListener("click", () => navegarPara(el.dataset.irPara))
);

function fecharSidebarMobile() {
  sidebar.classList.remove("aberta");
  btnMenu.setAttribute("aria-expanded", "false");
}

btnMenu.addEventListener("click", () => {
  const aberta = sidebar.classList.toggle("aberta");
  btnMenu.setAttribute("aria-expanded", String(aberta));
});

// ---------------- RF05 — Autocompletação ----------------
function destacarPrefixo(tag, prefixo) {
  const indice = tag.toLowerCase().indexOf(prefixo.toLowerCase());
  if (indice === -1) return escaparHtml(tag);
  const antes = escaparHtml(tag.slice(0, indice));
  const meio = escaparHtml(tag.slice(indice, indice + prefixo.length));
  const depois = escaparHtml(tag.slice(indice + prefixo.length));
  return `${antes}<mark>${meio}</mark>${depois}`;
}

async function buscarSugestoes(prefixoBruto) {
  const prefixo = prefixoBruto.trim();

  if (prefixo.length === 0) {
    listaSugestoes.classList.remove("visivel");
    listaSugestoes.innerHTML = "";
    return;
  }
  if (prefixo.length < 2) {
    listaSugestoes.innerHTML = `<li class="sem-resultado">Digite pelo menos 2 caracteres (RN04).</li>`;
    listaSugestoes.classList.add("visivel");
    return;
  }

  listaSugestoes.innerHTML = `<li class="sem-resultado">Buscando…</li>`;
  listaSugestoes.classList.add("visivel");

  const { ok, dados } = await API.buscarSugestoes(prefixo, 10);
  if (!ok || !dados) {
    listaSugestoes.innerHTML = `<li class="sem-resultado">Não foi possível consultar a API.</li>`;
    return;
  }

  renderizarSugestoes(dados.suggestions, prefixo);
}

function renderizarSugestoes(sugestoes, prefixo) {
  listaSugestoes.innerHTML = "";

  if (!sugestoes || sugestoes.length === 0) {
    listaSugestoes.innerHTML = `<li class="sem-resultado">Nenhuma tag encontrada com esse prefixo.</li>`;
    return;
  }

  sugestoes.forEach((item) => {
    const li = document.createElement("li");
    li.setAttribute("role", "option");
    li.tabIndex = 0;
    li.innerHTML = `${destacarPrefixo(item.tag, prefixo)}<span class="contador">${item.usage_count} uso(s)</span>`;
    li.addEventListener("click", () => selecionarSugestao(item.tag));
    li.addEventListener("keydown", (e) => { if (e.key === "Enter") selecionarSugestao(item.tag); });
    listaSugestoes.appendChild(li);
  });
}

function selecionarSugestao(tag) {
  campoBusca.value = tag;
  listaSugestoes.classList.remove("visivel");
  buscaExata(tag);
  Logs.registrar("info", `Sugestão "${escaparHtml(tag)}" selecionada.`);
}

async function buscaExata(tag) {
  if (!tag) return;
  const { ok, dados } = await API.buscarTag(tag);
  if (ok && dados && dados.tag) {
    resultadoBusca.innerHTML = `Encontrada: <strong>${escaparHtml(dados.tag.tag)}</strong> — ${dados.tag.usage_count} uso(s).`;
    Logs.registrar("ok", `Tag "${escaparHtml(dados.tag.tag)}" encontrada.`);
  } else {
    resultadoBusca.textContent = "Tag não encontrada.";
    Logs.registrar("erro", `Busca por "${escaparHtml(tag)}" não encontrou resultado.`);
  }
}

campoBusca.addEventListener("input", debounce((e) => buscarSugestoes(e.target.value), 250));
campoBusca.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    listaSugestoes.classList.remove("visivel");
    buscaExata(campoBusca.value.trim());
  }
});
document.addEventListener("click", (e) => {
  if (!e.target.closest(".campo-busca")) listaSugestoes.classList.remove("visivel");
});

// ---------------- RF01 / RF08 — Inserção de tag ----------------
async function adicionarTag() {
  const tag = campoTag.value.trim();
  const descricao = campoDescricao.value.trim();

  if (!tag) {
    mostrarAviso("Digite uma tag antes de adicionar.", "erro");
    return;
  }

  const { ok, dados } = await API.inserirTag(tag, descricao);

  if (!ok || !dados) {
    const mensagem = (dados && dados.error) || "Não foi possível inserir a tag.";
    mostrarAviso(mensagem, "erro");
    Logs.registrar("erro", escaparHtml(mensagem));
    return;
  }

  if (dados.created) {
    mostrarAviso(`✓ Tag "${dados.tag.tag}" inserida.`, "ok");
    Logs.registrar("ok", `Tag "${escaparHtml(dados.tag.tag)}" inserida.`);
  } else {
    mostrarAviso(`ℹ Tag "${dados.tag.tag}" já existente — contador atualizado para ${dados.tag.usage_count}.`, "info");
    Logs.registrar("info", `Tag "${escaparHtml(dados.tag.tag)}" já existia — uso incrementado.`);
  }

  campoTag.value = "";
  campoDescricao.value = "";
  await atualizarTudo();
}

btnAdicionar.addEventListener("click", adicionarTag);
campoTag.addEventListener("keydown", (e) => { if (e.key === "Enter") adicionarTag(); });

// ---------------- RF06 / RF07 / RF03 — Tabela de tags ----------------
async function carregarTags() {
  const { ok, dados } = await API.listarTags();
  if (!ok || !dados) return;

  corpoTabela.innerHTML = "";

  if (!dados.tags || dados.tags.length === 0) {
    corpoTabela.innerHTML = `<tr><td colspan="4" style="color:var(--text-soft)">Nenhuma tag cadastrada ainda.</td></tr>`;
    return;
  }

  dados.tags.forEach((item) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${escaparHtml(item.tag)}</strong></td>
      <td>${escaparHtml(item.description || "—")}</td>
      <td>${item.usage_count}</td>
      <td class="acoes">
        <button data-acao="use" data-tag="${escaparHtml(item.tag)}" title="Associar a um novo tópico">+</button>
        <button data-acao="unuse" data-tag="${escaparHtml(item.tag)}" title="Remover associação de um tópico">−</button>
        <button data-acao="delete" data-tag="${escaparHtml(item.tag)}" class="remover" title="Excluir tag">excluir</button>
      </td>`;
    corpoTabela.appendChild(tr);
  });
}

corpoTabela.addEventListener("click", async (evento) => {
  const botao = evento.target.closest("button");
  if (!botao) return;
  const { acao, tag } = botao.dataset;

  if (acao === "delete") {
    abrirModalRemocao(tag);
    return;
  }

  const { ok } = acao === "use" ? await API.usarTag(tag) : await API.desusarTag(tag);
  Logs.registrar(ok ? "ok" : "erro", ok
    ? `Uso da tag "${escaparHtml(tag)}" ${acao === "use" ? "incrementado" : "decrementado"}.`
    : `Falha ao atualizar uso de "${escaparHtml(tag)}".`);
  await atualizarTudo();
});

function abrirModalRemocao(tag) {
  tagPendenteRemocao = tag;
  modalTexto.textContent = `Remover a tag "${tag}"? Isso só é permitido quando o contador de uso está zerado (RN02).`;
  modalRemover.hidden = false;
  modalConfirmar.focus();
}

function fecharModalRemocao() {
  modalRemover.hidden = true;
  tagPendenteRemocao = null;
}

modalCancelar.addEventListener("click", fecharModalRemocao);
modalRemover.addEventListener("click", (e) => { if (e.target === modalRemover) fecharModalRemocao(); });

modalConfirmar.addEventListener("click", async () => {
  const tag = tagPendenteRemocao;
  fecharModalRemocao();
  if (!tag) return;

  const { ok, dados } = await API.removerTag(tag);
  if (ok) {
    mostrarAviso(`Tag "${tag}" removida.`, "ok");
    Logs.registrar("ok", `Tag "${escaparHtml(tag)}" removida.`);
  } else {
    const mensagem = (dados && dados.error) || `Não foi possível remover "${tag}".`;
    mostrarAviso(mensagem, "erro");
    Logs.registrar("erro", escaparHtml(mensagem));
  }
  await atualizarTudo();
});

// ---------------- RF09 / RF10 — Métricas e árvore ----------------
function cartaoMetrica(valor, rotulo) {
  return `<div class="metrica"><span>${valor}</span><small>${rotulo}</small></div>`;
}

function renderizarMetricas(metricas) {
  const balanceadaTexto = metricas.is_balanced ? "OK" : "FALHA";

  document.getElementById("metricas-completas").innerHTML = [
    cartaoMetrica(metricas.height, "Altura da AVL"),
    cartaoMetrica(metricas.node_count, "Nós"),
    cartaoMetrica(metricas.rotations, "Rotações (total)"),
    cartaoMetrica(balanceadaTexto, "Balanceamento"),
    cartaoMetrica(metricas.total_usage ?? "N/D", "Uso total"),
  ].join("");

  document.getElementById("metricas-resumo").innerHTML = [
    cartaoMetrica(metricas.height, "Altura"),
    cartaoMetrica(metricas.node_count, "Nós"),
    cartaoMetrica(balanceadaTexto, "Balanceada"),
  ].join("");

  document.getElementById("mini-metricas").innerHTML = [
    cartaoMetrica(metricas.height, "Altura"),
    cartaoMetrica(metricas.node_count, "Nós"),
    cartaoMetrica(metricas.rotations, "Rotações"),
    cartaoMetrica(balanceadaTexto, "Balanceamento"),
  ].join("");

  definirIndicador(statusBalanceamentoEl, metricas.is_balanced ? "ok" : "erro",
    metricas.is_balanced ? "AVL balanceada" : "AVL desbalanceada");

  if (ultimasMetricas && metricas.rotations > ultimasMetricas.rotations) {
    const diferenca = metricas.rotations - ultimasMetricas.rotations;
    avisoRotacao.hidden = false;
    avisoRotacao.textContent = `↻ ${diferenca} rotação(ões) detectada(s) — total agora: ${metricas.rotations}`;
    Logs.registrar("info", `Rotação executada pelo backend (total acumulado: ${metricas.rotations}).`);
    setTimeout(() => { avisoRotacao.hidden = true; }, 6000);
  }

  ultimasMetricas = metricas;
}

async function atualizarArvoreEMetricas() {
  const [respMetricas, respArvore] = await Promise.all([API.metricas(), API.arvore()]);

  if (respMetricas.ok && respMetricas.dados) {
    definirIndicador(statusApiEl, "ok", "API conectada");
    renderizarMetricas(respMetricas.dados);
  } else {
    definirIndicador(statusApiEl, "erro", "API indisponível");
  }

  if (respArvore.ok && respArvore.dados) {
    Visualizador.renderizar(respArvore.dados);
  }
}

async function atualizarTudo() {
  await Promise.all([carregarTags(), atualizarArvoreEMetricas()]);
}

// ---------------- Casos de uso: cenário aula1..aula20 e reset ----------------
btnCenario.addEventListener("click", async () => {
  btnCenario.disabled = true;
  resultadoCenario.textContent = "Carregando cenário aula1..aula20…";
  const { ok, dados } = await API.carregarCenario();
  btnCenario.disabled = false;

  if (ok) {
    resultadoCenario.textContent = "Cenário carregado. Veja a altura e o balanceamento no painel de Métricas.";
    Logs.registrar("ok", "Cenário aula1..aula20 carregado.");
  } else {
    resultadoCenario.textContent = (dados && dados.error) || "Não foi possível carregar o cenário.";
    Logs.registrar("erro", "Falha ao carregar o cenário aula1..aula20.");
  }
  await atualizarTudo();
});

btnLimpar.addEventListener("click", async () => {
  const { ok } = await API.reiniciar();
  Visualizador.limparEstadoConhecido();
  resultadoCenario.textContent = ok ? "Dicionário limpo." : "Não foi possível limpar o dicionário.";
  Logs.registrar(ok ? "info" : "erro", ok ? "Dicionário de tags reiniciado." : "Falha ao reiniciar o dicionário.");
  await atualizarTudo();
});

// ---------------- Carga inicial ----------------
atualizarTudo();
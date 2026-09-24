/* =============================================================================
   logs.js — histórico de operações mostrado na interface.
   A API atual não devolve timestamp de cada operação, então os horários
   aqui são do momento em que o navegador registrou a ação (hora local).
   ========================================================================== */

const Logs = (() => {
  const ICONES = { ok: "✓", erro: "×", info: "ℹ", busca: "⌕", rotacao: "↻" };
  const MAXIMO = 60;

  let listaCompleta = null;
  let listaResumo = null;
  const entradas = [];

  function iniciar(elCompleta, elResumo) {
    listaCompleta = elCompleta;
    listaResumo = elResumo;
  }

  function registrar(tipo, mensagem) {
    const hora = new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    entradas.unshift({ tipo, mensagem, hora });
    if (entradas.length > MAXIMO) entradas.pop();
    renderizar();
  }

  function itemHtml({ tipo, mensagem, hora }) {
    const icone = ICONES[tipo] || "•";
    const classeCor = tipo === "ok" ? "log-ok" : tipo === "erro" ? "log-erro" : "log-info";
    return `<li class="${classeCor}">
      <span class="log-hora">${hora}</span>
      <span class="log-icone">${icone}</span>
      <span class="log-mensagem">${mensagem}</span>
    </li>`;
  }

  function renderizar() {
    if (listaCompleta) listaCompleta.innerHTML = entradas.map(itemHtml).join("") || "<li>Nenhuma atividade ainda.</li>";
    if (listaResumo) listaResumo.innerHTML = entradas.slice(0, 5).map(itemHtml).join("") || "<li>Nenhuma atividade ainda.</li>";
  }

  return { iniciar, registrar };
})();

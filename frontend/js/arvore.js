/* =============================================================================
   arvore.js — desenha a árvore AVL em SVG a partir da estrutura já retornada
   pela API (GET /api/avl). Este arquivo apenas VISUALIZA a árvore: nenhuma
   regra de inserção, remoção ou rotação é recalculada aqui — quem decide
   isso é sempre o backend (avl_tree.py).

   A API atual devolve um texto indentado (campo "text"). Se em algum momento
   ela também expuser a estrutura aninhada (campo "tree", no formato de
   AVLTree.to_dict()), este arquivo desenha o SVG interativo automaticamente;
   caso contrário, cai de volta para o texto, sem inventar dados.
   ========================================================================== */

const Visualizador = (() => {
  const ESPACAMENTO_X = 78;
  const ESPACAMENTO_Y = 92;
  const MARGEM = 46;
  const RAIO = 24;

  let container = null;
  let tooltip = null;
  let chavesConhecidas = new Set();

  function iniciar(containerEl, tooltipEl) {
    container = containerEl;
    tooltip = tooltipEl;
  }

  // Detecta se a API já expõe a estrutura aninhada da árvore.
  function extrairEstrutura(respostaAvl) {
    if (!respostaAvl) return null;
    return respostaAvl.tree || respostaAvl.root || respostaAvl.node || null;
  }

  function coletarPosicoes(node, profundidade, mapa, contador) {
    if (!node) return;
    coletarPosicoes(node.left, profundidade + 1, mapa, contador);
    const x = contador.valor++;
    mapa.set(node, { x, y: profundidade, node });
    coletarPosicoes(node.right, profundidade + 1, mapa, contador);
  }

  function coletarArestas(node, mapa, arestas) {
    if (!node) return;
    const pos = mapa.get(node);
    if (node.left) {
      arestas.push({ pai: pos, filho: mapa.get(node.left) });
      coletarArestas(node.left, mapa, arestas);
    }
    if (node.right) {
      arestas.push({ pai: pos, filho: mapa.get(node.right) });
      coletarArestas(node.right, mapa, arestas);
    }
  }

  function chaveSegura(chave) {
    return String(chave).replace(/[^a-zA-Z0-9_-]/g, "_");
  }

  function renderizarSvg(raiz) {
    const mapa = new Map();
    coletarPosicoes(raiz, 0, mapa, { valor: 0 });
    const arestas = [];
    coletarArestas(raiz, mapa, arestas);

    const posicoes = [...mapa.values()];
    const maxX = Math.max(...posicoes.map((p) => p.x));
    const maxY = Math.max(...posicoes.map((p) => p.y));
    const largura = (maxX + 1) * ESPACAMENTO_X + MARGEM * 2;
    const altura = (maxY + 1) * ESPACAMENTO_Y + MARGEM * 2;

    const px = (p) => p.x * ESPACAMENTO_X + MARGEM + ESPACAMENTO_X / 2;
    const py = (p) => p.y * ESPACAMENTO_Y + MARGEM;

    let svg = `<svg viewBox="0 0 ${largura} ${altura}" width="${largura}" height="${altura}" xmlns="http://www.w3.org/2000/svg">`;

    arestas.forEach(({ pai, filho }) => {
      svg += `<line class="aresta-avl" data-de="${chaveSegura(pai.node.key)}" data-para="${chaveSegura(filho.node.key)}"
        x1="${px(pai)}" y1="${py(pai)}" x2="${px(filho)}" y2="${py(filho)}" />`;
    });

    posicoes.forEach((pos) => {
      const n = pos.node;
      const nova = !chavesConhecidas.has(n.key);
      const classes = ["no-avl"];
      if (nova) classes.push("novo");
      svg += `
        <g class="${classes.join(" ")}" tabindex="0" data-key="${chaveSegura(n.key)}"
           data-tag="${escaparAtributo(n.tag)}" data-altura="${n.height}" data-fb="${n.balance}" data-uso="${n.usage_count}"
           transform="translate(${px(pos)}, ${py(pos)})">
          <circle r="${RAIO}"></circle>
          <text text-anchor="middle" dy="4">${encurtar(n.tag)}</text>
          <text class="fb-texto" text-anchor="middle" dy="${RAIO + 13}">FB ${n.balance >= 0 ? "+" : ""}${n.balance}</text>
        </g>`;
    });

    svg += `</svg>`;
    return svg;
  }

  function encurtar(texto) {
    const t = String(texto);
    return t.length > 10 ? `${escaparAtributo(t.slice(0, 9))}…` : escaparAtributo(t);
  }

  function escaparAtributo(texto) {
    return String(texto)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function anexarInteracoes() {
    container.querySelectorAll(".no-avl").forEach((grupo) => {
      grupo.addEventListener("mouseenter", (ev) => mostrarTooltip(grupo, ev));
      grupo.addEventListener("mousemove", (ev) => posicionarTooltip(ev));
      grupo.addEventListener("mouseleave", esconderTooltip);
      grupo.addEventListener("focus", (ev) => mostrarTooltip(grupo, ev, true));
      grupo.addEventListener("blur", esconderTooltip);
    });
  }

  function mostrarTooltip(grupo, evento, viaFoco) {
    const { tag, altura, fb, uso } = grupo.dataset;
    tooltip.innerHTML = `
      <strong>${tag}</strong>
      <dl>
        <dt>Altura</dt><dd>${altura}</dd>
        <dt>Fator de balanceamento</dt><dd>${fb}</dd>
        <dt>Uso</dt><dd>${uso} tópico(s)</dd>
      </dl>`;
    tooltip.hidden = false;
    if (viaFoco) {
      const retangulo = grupo.getBoundingClientRect();
      const doContainer = container.getBoundingClientRect();
      tooltip.style.left = `${retangulo.left - doContainer.left + 20}px`;
      tooltip.style.top = `${retangulo.top - doContainer.top}px`;
    } else {
      posicionarTooltip(evento);
    }
  }

  function posicionarTooltip(evento) {
    const doContainer = container.getBoundingClientRect();
    tooltip.style.left = `${evento.clientX - doContainer.left + 16}px`;
    tooltip.style.top = `${evento.clientY - doContainer.top + 16}px`;
  }

  function esconderTooltip() {
    tooltip.hidden = true;
  }

  // Ponto de entrada: recebe a resposta bruta de GET /api/avl.
  function renderizar(respostaAvl) {
    const raiz = extrairEstrutura(respostaAvl);

    if (!raiz) {
      // A API atual não expõe a estrutura aninhada — mostramos o texto,
      // sem simular uma árvore gráfica que não corresponde a dados reais.
      const texto = (respostaAvl && respostaAvl.text) || "(árvore vazia)";
      container.innerHTML = `<pre class="fonte-tecnica" style="margin:0;padding:16px;color:var(--text-soft);white-space:pre;overflow:auto;width:100%;">${escaparAtributo(texto)}</pre>`;
      return;
    }

    container.innerHTML = renderizarSvg(raiz);
    anexarInteracoes();

    // Atualiza o conjunto de chaves conhecidas para a próxima renderização
    // saber quais nós são novos (usado só para a animação de entrada).
    const novasChaves = new Set();
    (function coletar(n) {
      if (!n) return;
      novasChaves.add(n.key);
      coletar(n.left);
      coletar(n.right);
    })(raiz);
    chavesConhecidas = novasChaves;
  }

  function limparEstadoConhecido() {
    chavesConhecidas = new Set();
  }

  return { iniciar, renderizar, limparEstadoConhecido };
})();

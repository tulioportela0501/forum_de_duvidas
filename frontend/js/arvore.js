// Visualizador: apenas DESENHA a árvore enviada pelo backend (a AVL real está em backend/avl.py).
// opts: {onSel(no), destaque: 'chave', rotacionados: ['nome', ...], animar: bool}
function desenharArvore(root, box, opts = {}) {
  if (!root) { box.innerHTML = '<div class="empty">Árvore vazia. Publique dúvidas com tags ou crie tags para vê-las aqui.</div>'; return []; }
  const W = 116, V = 92, pos = [];
  let i = 0;
  (function walk(n, d) { if (!n) return; walk(n.l, d + 1); n.x = i++ * W + 62; n.y = d * V + 40; n.d = d; pos.push(n); walk(n.r, d + 1); })(root, 0);
  const w = i * W + 20, h = (Math.max(...pos.map(p => p.d)) + 1) * V + 30;
  const rot = new Set(opts.rotacionados || []);
  let edges = '', nodes = '';
  pos.forEach((n, idx) => {
    [n.l, n.r].forEach(c => {
      if (c) {
        const y1 = n.y + 33, y2 = c.y - 25, my = (y1 + y2) / 2;
        edges += `<path class="edge" pathLength="100" d="M${n.x} ${y1}C${n.x} ${my},${c.x} ${my},${c.x} ${y2}"/>`;
      }
    });
    const cl = Math.abs(n.fb) > 1 ? 'bad' : Math.abs(n.fb) === 1 ? 'warn' : '';
    const nome = n.tag.length > 12 ? n.tag.slice(0, 11) + '…' : n.tag;
    nodes += `<g class="nd ${cl} ${opts.destaque === n.key ? 'novo' : ''} ${rot.has(n.tag) ? 'rot' : ''}" data-i="${idx}">
      <rect x="${n.x - 48}" y="${n.y - 25}" width="96" height="58" rx="8"/>
      <text class="t" x="${n.x}" y="${n.y - 8}" text-anchor="middle">${esc(nome)}</text>
      <text x="${n.x}" y="${n.y + 7}" text-anchor="middle">H:${n.h} FB:${n.fb}</text>
      <text x="${n.x}" y="${n.y + 23}" text-anchor="middle">Uso:${n.uso}</text></g>`;
  });
  box.classList.toggle('still', opts.animar === false);
  box.innerHTML = `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" style="min-width:${w}px" role="img" aria-label="Árvore AVL">${edges}${nodes}</svg>`;
  box.scrollLeft = Math.max(0, root.x - box.clientWidth / 2); // centraliza a raiz na área visível
  const tip = document.getElementById('tip');
  box.querySelectorAll('.nd').forEach(g => {
    const n = pos[+g.dataset.i];
    g.onmousemove = ev => {
      tip.style.display = 'block'; tip.style.left = ev.clientX + 14 + 'px'; tip.style.top = ev.clientY + 14 + 'px';
      tip.innerHTML = `<b>${esc(n.tag)}</b><br>Altura: ${n.h}<br>FB: ${n.fb}<br>Uso: ${n.uso}`;
    };
    g.onmouseleave = () => { tip.style.display = 'none'; };
    g.onclick = () => {
      box.querySelectorAll('.sel').forEach(x => x.classList.remove('sel'));
      g.classList.add('sel');
      if (opts.onSel) opts.onSel(n);
    };
  });
  return pos;
}

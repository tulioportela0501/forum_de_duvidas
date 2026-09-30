/* Fórum AVL — frontend (HTML/CSS/JS puro). Cada view devolve {html, mount}; o roteador só desenha
   se o usuário ainda estiver naquela rota (evita tela "trocada" quando as respostas chegam fora de ordem). */
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const $ = s => document.querySelector(s);
const view = () => $('#view');
const fmtData = iso => { const d = new Date(iso); return isNaN(d) ? '' : d.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }); };
const wait = ms => new Promise(r => setTimeout(r, ms));

const P = {
  home: 'M3 10l9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z',
  tag: 'M20.6 13.4l-7.2 7.2a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8z',
  users: 'M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z',
  tree: 'M12 3v6M12 9H5v6M12 9h7v6M3 15h4v4H3zM17 15h4v4h-4zM10 3h4v4h-4z',
  list: 'M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01',
  dash: 'M3 3h7v9H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 16h7v5H3z',
  msg: 'M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z',
  gear: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM12 2v3M12 19v3M2 12h3M19 12h3',
};
const ic = k => `<svg class="ic" viewBox="0 0 24 24"><path d="${P[k]}"/></svg>`;
const MEM = [['#/', 'home', 'Início'], ['#/tags', 'tag', 'Tags'], ['#/membros', 'users', 'Membros']];
const ADM = [['#/admin', 'dash', 'Dashboard'], ['#/admin/avl', 'tree', 'Árvore AVL'], ['#/admin/tags', 'tag', 'Tags'],
  ['#/admin/topicos', 'msg', 'Tópicos'], ['#/admin/membros', 'users', 'Membros'], ['#/admin/logs', 'list', 'Logs']];

function toast(msg, erro) {
  const t = document.createElement('div');
  t.className = 'toast' + (erro ? ' e' : '');
  t.textContent = msg;
  document.body.append(t);
  setTimeout(() => t.remove(), 3500);
}

// ------------------------------------------------------------------ layout / roteador
function shell(adm, rt) {
  const menu = adm ? ADM : MEM;
  $('#side').innerHTML = `<div class="logo"><i></i>Fórum AVL</div>
    ${menu.map(x => `<a class="nav ${rt === x[0] ? 'on' : ''}" href="${x[0]}">${ic(x[1])}${x[2]}</a>`).join('')}
    <a class="nav" href="${adm ? '#/' : '#/admin'}">${ic(adm ? 'home' : 'gear')}${adm ? 'Área de membros' : 'Área administrativa'}</a>
    <div class="user"><div class="av">${adm ? 'A' : 'M'}</div><div>${adm ? 'Administrador' : 'Membro'}<br>
    ${adm && Auth.get() ? '<a href="#" id="out">Sair</a>' : adm ? '<a href="admin-cadastro.html">Entrar / cadastrar</a>' : ''}</div></div>`;
  const out = $('#out');
  if (out) out.onclick = e => { e.preventDefault(); Auth.clear(); location.hash = '#/'; };
}

const loginPrompt = () => ({
  html: '<div class="empty">Acesso restrito a administradores.<br><br><a class="btn" href="admin-cadastro.html">Entrar como administrador</a></div>',
});
const skel = () => { view().innerHTML = '<div class="sk"></div><div class="sk"></div><div class="sk"></div>'; };

let navId = 0;
async function route() {
  const id = ++navId;
  const rt = location.hash || '#/';
  const adm = rt.startsWith('#/admin');
  $('#side').classList.remove('open');
  shell(adm, rt);
  let r;
  if (adm && !Auth.get()) {
    r = loginPrompt();
  } else {
    skel();
    try {
      r = await (VIEWS[rt] || VIEWS['#/'])();
    } catch (e) {
      if (id !== navId) return;
      if (e.status === 401 && adm) { Auth.clear(); shell(adm, rt); r = loginPrompt(); }
      else r = { html: `<div class="err">Não foi possível carregar os dados.<br><small>${esc(e.message)}</small><br><br><button class="btn ghost" id="retry">Tentar novamente</button></div>`, mount: () => { $('#retry').onclick = route; } };
    }
  }
  if (id !== navId) return;
  view().innerHTML = r.html;
  if (r.mount) r.mount();
}
$('#bg').onclick = () => $('#side').classList.toggle('open');
addEventListener('hashchange', route);

// ------------------------------------------------------------------ componentes
const kpi = (l, v) => `<div class="card kpi"><b>${esc(v ?? 'N/D')}</b><span>${esc(l)}</span></div>`;

function postCard(t) {
  const tags = (t.tags || []).map(x => `<span class="tag">${esc(x)}</span>`).join('');
  return `<div class="card post"><div class="meta">${t.autor ? `<div class="av" style="width:24px;height:24px;font-size:11px">${esc(t.autor[0].toUpperCase())}</div>${esc(t.autor)}` : '<span>Anônimo</span>'}<span>${esc(fmtData(t.criado_em))}</span></div>
    <h3>${esc(t.titulo)}</h3><div class="sub">${esc(t.descricao || '')}</div><div style="margin-top:8px">${tags}</div>
    <div class="meta"><span>${t.respostas ?? 0} respostas</span><span>${t.visualizacoes ?? 0} visualizações</span></div></div>`;
}

// Modal "Nova dúvida" com autocomplete (consulta a AVL no backend enquanto digita)
function novaDuvida() {
  const tags = [];
  let sugestoes = [], idx = -1, timer = null, seq = 0;
  const m = document.createElement('div');
  m.className = 'modal';
  m.innerHTML = `<div class="card" role="dialog" aria-modal="true" aria-label="Nova dúvida"><h2>Nova dúvida</h2>
    <input id="au" maxlength="60" placeholder="Seu nome ou codinome (opcional)" autocomplete="off">
    <input id="ti" maxlength="150" placeholder="Título" autocomplete="off">
    <textarea id="de" rows="4" maxlength="2000" placeholder="Descreva sua dúvida"></textarea>
    <div class="chips" id="ch"></div>
    <input id="tg" placeholder="Tags: digite 2+ letras, escolha uma sugestão ou aperte Enter" autocomplete="off">
    <div class="sug" id="sg" style="display:none"></div>
    <div class="btnrow"><button class="btn ghost" id="cx">Cancelar</button><button class="btn" id="ok">PUBLICAR DÚVIDA</button></div></div>`;
  document.body.append(m);
  const onEsc = e => { if (e.key === 'Escape') fechar(); };
  const fechar = () => { m.remove(); document.removeEventListener('keydown', onEsc); };
  document.addEventListener('keydown', onEsc);
  m.onclick = e => { if (e.target === m) fechar(); };
  const q = s => m.querySelector(s);
  q('#au').value = localStorage.getItem('autor') || '';
  q('#ti').focus();

  const desenhaChips = () => { q('#ch').innerHTML = tags.map((t, i) => `<span class="tag" data-i="${i}" style="cursor:pointer" title="Remover">${esc(t)} ✕</span>`).join(''); };
  const fechaSug = () => { sugestoes = []; idx = -1; q('#sg').style.display = 'none'; };
  const add = t => {
    t = t.trim().replace(/\s+/g, ' ');
    if (t && !tags.some(x => x.toLowerCase() === t.toLowerCase())) tags.push(t);
    q('#tg').value = ''; fechaSug(); desenhaChips();
  };
  const desenhaSug = texto => {
    const s = q('#sg');
    s.innerHTML = sugestoes.length
      ? sugestoes.map((t, i) => `<div class="${i === idx ? 'on' : ''}" data-i="${i}">${esc(t.display_name)} <span class="mut">${t.usage_count} usos</span></div>`).join('')
      : `<div class="mut">Sem resultados — Enter cria a tag "${esc(texto)}"</div>`;
    s.style.display = 'block';
  };
  q('#ch').onclick = e => { if (e.target.dataset.i) { tags.splice(+e.target.dataset.i, 1); desenhaChips(); } };
  q('#sg').onmousedown = e => { const d = e.target.closest('[data-i]'); if (d) { e.preventDefault(); add(sugestoes[+d.dataset.i].display_name); q('#tg').focus(); } };
  q('#tg').oninput = e => {
    const texto = e.target.value.trim();
    clearTimeout(timer);
    if (texto.length < 2) { fechaSug(); return; }
    timer = setTimeout(async () => {
      const mine = ++seq;
      try {
        const r = await req(`${EP.autocomplete}?q=${encodeURIComponent(texto)}&limit=6`);
        if (mine !== seq) return;
        sugestoes = r; idx = -1; desenhaSug(texto);
      } catch { fechaSug(); }
    }, 150);
  };
  q('#tg').onkeydown = e => {
    if (e.key === 'ArrowDown' && sugestoes.length) { e.preventDefault(); idx = (idx + 1) % sugestoes.length; desenhaSug(e.target.value); }
    else if (e.key === 'ArrowUp' && sugestoes.length) { e.preventDefault(); idx = (idx - 1 + sugestoes.length) % sugestoes.length; desenhaSug(e.target.value); }
    else if (e.key === 'Enter') { e.preventDefault(); add(idx >= 0 ? sugestoes[idx].display_name : e.target.value); }
  };
  q('#cx').onclick = fechar;
  q('#ok').onclick = async () => {
    if (q('#tg').value.trim()) add(q('#tg').value);
    const b = q('#ok'); b.disabled = true;
    try {
      const autor = q('#au').value.trim();
      localStorage.setItem('autor', autor);
      await post(EP.topicos, { titulo: q('#ti').value, descricao: q('#de').value, autor, tags });
      fechar(); toast('Dúvida publicada!'); route();
    } catch (e) { toast(e.message, true); b.disabled = false; }
  };
}

// ------------------------------------------------------------------ views
async function homeView() {
  const t = await req(EP.topicos);
  return {
    html: `<h1>Comunidade</h1><p class="sub">Tire dúvidas e ajude colegas.</p>
      <div class="card ask"><div class="av">M</div><div class="fake" id="ask">O que você gostaria de perguntar?</div><button class="btn" id="nb">+ Criar nova dúvida</button></div>
      ${t.map(postCard).join('') || '<div class="empty">Nenhuma dúvida ainda. Seja o primeiro a perguntar!</div>'}`,
    mount() { $('#ask').onclick = $('#nb').onclick = novaDuvida; },
  };
}

async function tagsView(adm) {
  const carregar = async () => (await req(EP.tags)).map(x => ({ n: x.display_name, k: x.key, u: x.usage_count, d: x.description }));
  let tags = await carregar();
  return {
    html: `<h1>Tags</h1><p class="sub">Dicionário de tags armazenado na árvore AVL.</p>
      ${adm ? `<div class="card" style="margin:12px 0"><h2>Nova tag</h2><div style="display:flex;gap:10px;flex-wrap:wrap"><input id="nn" placeholder="Nome da tag" style="flex:1;min-width:160px;margin:0" maxlength="40"><input id="nd" placeholder="Descrição (opcional)" style="flex:2;min-width:200px;margin:0" maxlength="200"><button class="btn" id="na">Adicionar</button></div></div>` : ''}
      <div style="display:flex;gap:10px;margin-top:12px"><input id="q" placeholder="Pesquisar tag..."><select id="o" style="width:180px"><option value="n">A–Z</option><option value="u">Mais usadas</option></select></div>
      <div class="grid" id="ls"></div>`,
    mount() {
      const desenha = () => {
        const q = $('#q').value.toLowerCase(), o = $('#o').value;
        const r = tags.filter(x => x.n.toLowerCase().includes(q)).sort(o === 'u' ? (a, b) => b.u - a.u || a.n.localeCompare(b.n) : (a, b) => a.n.localeCompare(b.n));
        $('#ls').innerHTML = r.map(x => `<div class="card"><span class="tag">${esc(x.n)}</span><div class="mut">${x.u} usos</div>${x.d ? `<div class="sub">${esc(x.d)}</div>` : ''}${adm ? `<button class="btn ghost danger" data-k="${esc(x.k)}" style="margin-top:8px;padding:4px 10px">Remover</button>` : ''}</div>`).join('')
          || '<div class="empty" style="grid-column:1/-1">Nenhuma tag encontrada.</div>';
      };
      $('#q').oninput = $('#o').onchange = desenha;
      desenha();
      if (!adm) return;
      $('#na').onclick = async () => {
        const b = $('#na'); b.disabled = true;
        try { await post(EP.tags, { nome: $('#nn').value, descricao: $('#nd').value }); toast('Tag criada!'); route(); }
        catch (e) { toast(e.message, true); b.disabled = false; }
      };
      $('#ls').onclick = async e => {
        const k = e.target.dataset && e.target.dataset.k;
        if (!k || !confirm(`Remover a tag "${k}" da árvore AVL?`)) return;
        try { await del(`${EP.tags}/${encodeURIComponent(k)}`); toast('Tag removida.'); tags = await carregar(); desenha(); }
        catch (err) { toast(err.message, true); }
      };
    },
  };
}

async function membrosView() {
  const m = await req(EP.membros);
  return {
    html: `<h1>Membros</h1><input id="q" placeholder="Pesquisar membro..."><div class="grid" id="ls"></div>`,
    mount() {
      const desenha = () => {
        const q = $('#q').value.toLowerCase();
        $('#ls').innerHTML = m.filter(x => x.nome.toLowerCase().includes(q)).map(x => `<div class="card" style="display:flex;gap:12px"><div class="av">${esc(x.nome[0])}</div><div><b>${esc(x.nome)}</b><div class="mut">${esc(x.funcao || '')}</div><div class="mut">${x.n_duvidas} dúvidas</div></div></div>`).join('')
          || '<div class="empty" style="grid-column:1/-1">Nenhum membro encontrado.</div>';
      };
      $('#q').oninput = desenha; desenha();
    },
  };
}

async function topicosAdminView() {
  const t = await req(EP.topicos);
  return { html: `<h1>Tópicos</h1>${t.map(postCard).join('') || '<div class="empty">Nenhum tópico cadastrado.</div>'}` };
}

async function logsView() {
  const l = await req(EP.logs);
  return {
    html: `<h1>Logs</h1>${l.length ? `<div class="card scroll"><table><tr><th>Data</th><th>Usuário</th><th>Ação</th><th>Resultado</th></tr>
      ${l.map(x => `<tr><td>${esc(fmtData(x.data))}</td><td>${esc(x.usuario)}</td><td>${esc(x.acao)}</td><td>${esc(x.resultado)}</td></tr>`).join('')}</table></div>` : '<div class="empty">Nenhum log registrado ainda.</div>'}`,
  };
}

async function dashboardView() {
  const d = await req(EP.dashboard);
  const pu = d.tags ? d.tags_usadas / d.tags * 100 : null;
  return {
    html: `<h1>Dashboard</h1><p class="sub">Estudante → dúvida → tags → backend → AVL → contador/nó/rotação → interface</p>
      <div class="grid" style="margin-top:14px">${kpi('Membros', d.membros)}${kpi('Tópicos', d.topicos)}${kpi('Tags', d.tags)}${kpi('Tags utilizadas', d.tags_usadas)}${kpi('Altura da AVL', d.altura)}${kpi('Rotações', d.rotacoes.total)}</div>
      <div class="two"><div class="card"><h2>Utilização das tags</h2>${pu == null ? '<div class="empty">Sem tags ainda</div>' : `<div style="display:flex;gap:18px;align-items:center">
        <svg width="120" height="120" viewBox="0 0 42 42"><circle cx="21" cy="21" r="15.9" fill="none" stroke="#24324A" stroke-width="6"/><circle cx="21" cy="21" r="15.9" fill="none" stroke="#22D3EE" stroke-width="6" stroke-dasharray="${pu} ${100 - pu}" transform="rotate(-90 21 21)"/></svg>
        <div>Utilizadas: <b>${pu.toFixed(1)}%</b><br>Não utilizadas: <b>${(100 - pu).toFixed(1)}%</b><br><span class="mut">${d.tags_usadas} de ${d.tags} tags</span></div></div>`}</div>
      <div class="card"><h2>Tags mais utilizadas</h2>${d.top_tags.map((x, i) => `<div class="row"><span>${i + 1}. ${esc(x.tag)}</span><b>${x.usage_count}</b></div>`).join('') || '<div class="empty">Sem dados ainda</div>'}</div></div>`,
  };
}

async function avlView() {
  const d = await req(EP.avl);
  const root = treeRoot(d);
  const rot = d.rotacoes;
  return {
    html: `<h1>Árvore AVL</h1><p class="sub">Visualização dos dados reais do backend (fonte da verdade).</p>
      <div class="btnrow" style="justify-content:flex-start;margin:12px 0"><button class="btn" id="tt">EXECUTAR TESTE aula1 → aula20</button><button class="btn ghost" id="rl" style="display:none">Voltar à árvore real</button><button class="btn ghost" id="tx">Ver em texto</button></div>
      <div class="cap" id="cap"></div><div class="grid" id="mt"></div>
      <div class="two" style="grid-template-columns:2fr 1fr"><div class="treebox" id="tb"></div>
      <div class="card"><h2 id="nt">Nó</h2><div id="dt" class="sub">Clique em um nó.</div><div class="side2"><h2>Rotações</h2><div id="rt"></div></div></div></div>
      <pre class="txt" id="tex" style="display:none">${esc(d.texto)}</pre>`,
    mount() {
      const porTipo = t => ['LL', 'RR', 'LR', 'RL'].map(k => `<div class="row"><span>${k}</span><b>${t[k] ?? 0}</b></div>`).join('');
      const mostra = (r, o = {}) => {
        const pos = desenharArvore(r, $('#tb'), {
          ...o, onSel: n => {
            $('#nt').textContent = n.tag;
            $('#dt').innerHTML = [['Altura', n.h], ['FB', n.fb], ['Uso', n.uso], ['Filho esq.', n.l && n.l.tag], ['Filho dir.', n.r && n.r.tag]]
              .map(x => `<div class="row"><span>${x[0]}</span><b>${esc(x[1] ?? '—')}</b></div>`).join('');
          },
        });
        const f = pos.map(n => n.fb);
        $('#mt').innerHTML = [['Altura', r ? r.h : 0], ['Nós', pos.length], ['Rotações', o.rotTotal ?? rot.total], ['Maior FB', f.length ? Math.max(...f) : 0], ['Menor FB', f.length ? Math.min(...f) : 0]].map(x => kpi(x[0], x[1])).join('');
      };
      mostra(root); $('#rt').innerHTML = porTipo(rot.por_tipo);
      $('#tx').onclick = () => { const p = $('#tex'); p.style.display = p.style.display === 'none' ? 'block' : 'none'; };
      $('#rl').onclick = () => { $('#cap').textContent = ''; $('#rl').style.display = 'none'; $('#rt').innerHTML = porTipo(rot.por_tipo); mostra(root); };
      $('#tt').onclick = async () => {
        const b = $('#tt'); b.disabled = true;
        try {
          const r = await post(EP.teste);
          let acum = { LL: 0, RR: 0, LR: 0, RL: 0 }, total = 0;
          for (const [i, p] of r.passos.entries()) {
            if (!document.body.contains(b)) return; // usuário saiu da tela durante a animação
            p.rotacoes.forEach(x => { acum[x.tipo]++; total++; });
            mostra(treeRoot(p.arvore), { destaque: p.inserida.toLowerCase(), rotacionados: p.rotacoes.map(x => x.no), animar: i === 0, rotTotal: total });
            $('#cap').innerHTML = `Inserindo <b>${esc(p.inserida)}</b> (${i + 1}/${r.passos.length})` + (p.rotacoes.length ? ` — rotação <b>${p.rotacoes.map(x => esc(x.tipo) + ' em ' + esc(x.no)).join(', ')}</b>` : ' — sem rotação');
            $('#rt').innerHTML = porTipo(acum);
            await wait(650);
          }
          const s = r.resumo;
          $('#cap').innerHTML = `Teste concluído: <b>${s.nos}</b> nós, altura <b>${s.altura}</b>, <b>${s.rotacoes}</b> rotações — árvore ${s.balanceada ? 'balanceada ✔' : 'DESBALANCEADA ✘'}. (Teste em árvore temporária: seus dados reais não foram alterados.)`;
          $('#rl').style.display = 'inline-block';
          toast('Teste executado');
        } catch (e) { toast(e.message, true); }
        b.disabled = false;
      };
    },
  };
}

const VIEWS = {
  '#/': homeView, '#/tags': () => tagsView(false), '#/membros': membrosView,
  '#/admin': dashboardView, '#/admin/avl': avlView, '#/admin/tags': () => tagsView(true),
  '#/admin/topicos': topicosAdminView, '#/admin/membros': membrosView, '#/admin/logs': logsView,
};
route();

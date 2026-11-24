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
  cap: 'M22 10 12 5 2 10l10 5 10-5zM6 12v5c3 2 9 2 12 0v-5',
  grp: 'M16 11a3 3 0 1 0 0-6M8 11a3 3 0 1 0 0-6M2 20v-1a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v1M16 15h2a4 4 0 0 1 4 4v1',
  bell: 'M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0',
  search: 'M21 21l-4.3-4.3M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14z',
  heart: 'M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 0 0-7.8 7.8l1 1.1L12 21l7.8-7.5 1-1.1a5.5 5.5 0 0 0 0-7.8z',
  reply: 'M9 14L4 9l5-5M4 9h10a6 6 0 0 1 6 6v3',
  eye: 'M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12zM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z',
  repost: 'M17 1l4 4-4 4M3 11V9a4 4 0 0 1 4-4h14M7 23l-4-4 4-4M21 13v2a4 4 0 0 1-4 4H3',
  gear: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM12 2v3M12 19v3M2 12h3M19 12h3',
};
const ic = k => `<svg class="ic" viewBox="0 0 24 24"><path d="${P[k]}"/></svg>`;
const ESTADO = new Map();                               // 'topico:1' / 'resposta:7' -> objeto exibido (curtidas, curtiu)
const likeBtn = (o, tipo, id) => `<button class="like ${o.curtiu ? 'on' : ''}" data-like="${tipo}:${id}" type="button" aria-pressed="${!!o.curtiu}" title="Curtir">${ic('heart')}<b>${o.curtidas || 0}</b></button>`;
const pinta = (k, o) => document.querySelectorAll(`[data-like="${k}"]`).forEach(b => {
  b.classList.toggle('on', !!o.curtiu); b.setAttribute('aria-pressed', !!o.curtiu); b.querySelector('b').textContent = o.curtidas || 0;
  if (o.curtiu) { b.classList.remove('beat'); void b.offsetWidth; b.classList.add('beat'); }
});
document.addEventListener('click', async e => {         // fase de captura: o clique no coração não abre a dúvida
  const b = e.target.closest('[data-like]'); if (!b) return;
  e.stopPropagation();
  const k = b.dataset.like, o = ESTADO.get(k); if (!o) return;
  const [tipo, id] = k.split(':'), antes = { c: o.curtidas || 0, v: !!o.curtiu };
  o.curtiu = !antes.v; o.curtidas = antes.c + (o.curtiu ? 1 : -1); pinta(k, o);
  try { const r = await post(`/api/${tipo === 'topico' ? 'topicos' : 'respostas'}/${id}/curtir`); o.curtiu = r.curtiu; o.curtidas = r.curtidas; }
  catch (err) { o.curtiu = antes.v; o.curtidas = antes.c; toast(err.message, true); }
  pinta(k, o);
}, true);
const repostBtn = o => `<button class="like rt ${o.repostou ? 'on' : ''}" data-rt="${o.id}" type="button" aria-pressed="${!!o.repostou}" title="Repostar">${ic('repost')}<b>${o.reposts || 0}</b></button>`;
document.addEventListener('click', async e => {
  const b = e.target.closest('[data-rt]'); if (!b) return;
  e.stopPropagation();
  const o = ESTADO.get('topico:' + b.dataset.rt); if (!o) return;
  const antes = { c: o.reposts || 0, v: !!o.repostou };
  const pinta2 = () => document.querySelectorAll(`[data-rt="${o.id}"]`).forEach(x => { x.classList.toggle('on', !!o.repostou); x.setAttribute('aria-pressed', !!o.repostou); x.querySelector('b').textContent = o.reposts || 0; });
  o.repostou = !antes.v; o.reposts = antes.c + (o.repostou ? 1 : -1); pinta2();
  try { Object.assign(o, await post(`/api/topicos/${o.id}/repostar`)); toast(o.repostou ? 'Dúvida repostada.' : 'Repost removido.'); }
  catch (err) { o.repostou = antes.v; o.reposts = antes.c; toast(err.message, true); }
  pinta2();
}, true);

// mini preview do perfil: aparece ao passar o mouse sobre um nome com data-u (id do usuário)
const PREV = new Map(); let hcTimer, hcHide, hcAlvo;
const hcEl = () => { let el = $('#hc'); if (!el) { el = document.createElement('div'); el.id = 'hc'; document.body.append(el); el.onmouseenter = () => clearTimeout(hcHide); el.onmouseleave = () => hcEsconde(); } return el; };
const hcEsconde = () => { clearTimeout(hcTimer); hcHide = setTimeout(() => { const el = $('#hc'); if (el) el.classList.remove('on'); hcAlvo = null; }, 180); };
const lerBlob = b => new Promise(ok => { const fr = new FileReader(); fr.onload = () => ok(fr.result); fr.onerror = () => ok(''); fr.readAsDataURL(b); });
async function hcMostra(w) {
  const id = +w.dataset.u; let p = PREV.get(id);
  if (!p || Date.now() - p._t > 60000) {
    try {
      p = { ...(await req(`/api/perfis/${id}`)), _t: Date.now(), foto: '' };
      if (p.tem_foto) { const r = await fetch(`/api/perfis/${id}/foto`, { credentials: 'same-origin', cache: 'no-cache' }); if (r.ok) p.foto = await lerBlob(await r.blob()); }
      PREV.set(id, p);
    } catch { return; }
  }
  if (!w.isConnected || !w.matches(':hover')) return;
  const el = hcEl();
  el.innerHTML = `<div class="hc-top b-${p.perfil}"></div><div class="hc-body"><div class="hc-head">${avatar({ nome: p.nome, foto: p.foto }, 56)}<div><b>${esc(p.nome)}</b>${p.verificado ? VERIF : ''}<div><span class="badge b-${p.perfil}">${ROTULO[p.perfil] || ''}</span></div></div></div>
    ${p.biografia ? `<p class="hc-bio">${esc(p.biografia)}</p>` : ''}${p.formacao || p.especialidade ? `<div class="mut">${esc([p.formacao, p.especialidade].filter(Boolean).join(' · '))}</div>` : ''}
    <div class="hc-stats"><span><b>${p.duvidas}</b> dúvidas</span><span><b>${p.respostas}</b> respostas</span></div>${p.verificado ? `<a href="#/professor/${p.id}" class="hc-link">Ver perfil completo</a>` : ''}</div>`;
  el.style.visibility = 'hidden'; el.classList.add('on');
  const r = w.getBoundingClientRect(), h = el.offsetHeight, wd = el.offsetWidth;
  el.style.left = Math.max(8, Math.min(r.left, innerWidth - wd - 8)) + 'px';
  el.style.top = (r.bottom + 8 + h > innerHeight && r.top - h - 8 > 0 ? r.top - h - 8 : r.bottom + 8) + 'px';
  el.style.visibility = ''; hcAlvo = w;
}
document.addEventListener('mouseover', e => {
  const w = e.target.closest && e.target.closest('[data-u]'); if (!w) return;
  clearTimeout(hcHide); if (hcAlvo === w) return;
  clearTimeout(hcTimer); hcTimer = setTimeout(() => hcMostra(w), 350);
});
document.addEventListener('mouseout', e => { if (e.target.closest && e.target.closest('[data-u]')) hcEsconde(); });
const ROTULO = { admin: 'Administrador', professor: 'Professor', aluno: 'Aluno' };
let EU = null;                                           // usuário logado (vem de /api/auth/eu)
const pode = (...perfis) => !!EU && perfis.includes(EU.perfil);   // SÓ para esconder botões: quem decide é o backend
const MENU = [['#/', 'home', 'Início'], ['#/tags', 'tag', 'Tags'], ['#/professores', 'users', 'Professores'], ['#/grupos', 'users', 'Grupos'], ['#/notificacoes', 'bell', 'Notificações', ['aluno', 'professor']],
  ['#/avl', 'tree', 'Árvore AVL', ['admin', 'professor']],
  ['#/usuarios', 'users', 'Usuários', ['admin']], ['#/logs', 'list', 'Logs', ['admin']],
  ['#/conta', 'gear', 'Minha conta']];

function toast(msg, erro) {
  let box = $('#toasts');
  if (!box) { box = document.createElement('div'); box.id = 'toasts'; document.body.append(box); }
  const t = document.createElement('div');
  t.className = 'toast' + (erro ? ' e' : '');
  t.setAttribute('role', erro ? 'alert' : 'status');
  t.textContent = msg;
  box.append(t);
  setTimeout(() => { t.classList.add('out'); setTimeout(() => t.remove(), 220); }, 3500);
}

// ------------------------------------------------------------------ layout / roteador
function shell(rt) {
  $('#side').innerHTML = `<div class="logo"><i></i>Fórum AVL<small class="area-tag">${{ admin: 'Administração', professor: 'Professor', aluno: 'Aluno' }[EU.perfil]}</small></div>
    ${MENU.filter(x => !x[3] || pode(...x[3])).map(x => `<a class="nav ${(rt === x[0] || (rt === '#/professor' && x[0] === '#/professores') || (rt === '#/grupo' && x[0] === '#/grupos')) ? 'on' : ''}" href="${x[0]}">${ic(x[1])}${x[2]}${x[0] === '#/notificacoes' ? '<span class="nbadge" id="nbadge" hidden></span>' : ''}</a>`).join('')}
    <button class="btn side-cta" id="nd" type="button">+ Nova dúvida</button>
    <div class="user">${avatar(EU, 34)}<div><b>${esc(EU.nome)}</b><br>
    <span class="badge b-${EU.perfil}">${ROTULO[EU.perfil]}</span> <button class="out" id="out" type="button">Sair</button></div></div>`;
  document.body.classList.toggle('adm', EU.perfil === 'admin');
  document.body.classList.remove('role-aluno', 'role-professor', 'role-admin'); document.body.classList.add('role-' + EU.perfil);
  const GRP = { '#/': EU.perfil === 'admin' ? 'Gestão' : 'Comunidade', '#/avl': 'Ferramentas', '#/usuarios': 'Administração' };
  $('#side').querySelectorAll('a.nav').forEach(a => { const g = GRP[a.getAttribute('href')]; if (g) a.insertAdjacentHTML('beforebegin', `<div class="nav-grp">${g}</div>`); });
  $('#nd').onclick = novaDuvida;
  {                                                       // logo fixo | navegação rolável | rodapé fixo
    const sd = $('#side'), nav = document.createElement('div'), foot = document.createElement('div');
    nav.className = 'side-nav'; foot.className = 'side-foot';
    sd.querySelector('.nav-grp, a.nav').before(nav);
    sd.querySelectorAll(':scope > a.nav, :scope > .nav-grp').forEach(x => nav.append(x));
    foot.append($('#nd'), sd.querySelector('.user')); sd.append(foot);
  }
  $('#out').onclick = async () => {
    try { await post(EP.logout); } catch { /* sessão já encerrada */ }
    Sessao.csrf = null; location.replace('login.html');
  };
}

const avatar = (u, px = 34) => {
  const st = `width:${px}px;height:${px}px`, fs = Math.round(px / 2.6), ini = esc(((u && u.nome) || '?')[0].toUpperCase());
  if (u && u.foto && /^data:image\//.test(u.foto)) return `<img class="av" src="${esc(u.foto)}" alt="" style="${st};object-fit:cover">`;
  const id = u && u.id;
  if (id && (u.tem_foto || u.autor_foto)) return `<img class="av" src="/api/perfis/${id}/foto" alt="" loading="lazy" data-ini="${ini}" data-fs="${fs}" style="${st};object-fit:cover">`;
  return `<div class="av" style="${st};font-size:${fs}px">${ini}</div>`;
};
document.addEventListener('error', e => {               // foto removida/indisponível: volta para a inicial
  const i = e.target; if (!i || i.tagName !== 'IMG' || !i.dataset.ini) return;
  const d = document.createElement('div'); d.className = 'av'; d.style.cssText = `${i.style.width ? `width:${i.style.width};height:${i.style.height};` : ''}font-size:${i.dataset.fs}px`; d.textContent = i.dataset.ini; i.replaceWith(d);
}, true);
const SELO = '<span class="badge b-prof" title="Professor verificado">✔ Verificado</span>';

// contador de notificações no menu (só aluno/professor); atualizado a cada 30 s e ao trocar de página
const badgeNotif = n => { const b = $('#nbadge'); if (b) { b.textContent = n > 99 ? '99+' : n; b.hidden = !n; } };
async function atualizaNotif() {
  if (!pode('aluno', 'professor')) return;
  try { badgeNotif((await req(`${EP.notif}/contagem`)).nao_lidas); } catch { /* sem rede: mantém o último valor */ }
}

const semPermissao = () => ({ html: '<div class="empty">Você não tem permissão para acessar esta área.</div>' });
const skel = () => { view().innerHTML = '<div class="sk sk-h"></div><div class="sk"></div><div class="sk"></div><div class="sk"></div>'; };
const bar = on => { let b = $('#bar'); if (!b) { b = document.createElement('div'); b.id = 'bar'; document.body.append(b); } b.className = ''; if (on) { void b.offsetWidth; b.className = 'on'; } else b.className = 'done'; };

let navId = 0;
async function route() {
  const id = ++navId;
  bar(true);
  const mp = /^#\/professor\/(\d+)$/.exec(location.hash), mg = /^#\/grupo\/(\d+)$/.exec(location.hash);
  const rt = mg ? '#/grupo' : mp ? '#/professor' : VIEWS[location.hash || '#/'] ? (location.hash || '#/') : '#/';
  window.ROTA_ID = mp ? +mp[1] : mg ? +mg[1] : null;
  drawer(false);
  shell(rt);
  const [fn, perfis] = VIEWS[rt];
  let r;
  if (perfis && !pode(...perfis)) {
    r = semPermissao();
  } else {
    skel();
    try {
      r = await fn();
    } catch (e) {
      if (id !== navId) return;
      if (e.status === 401) return;                      // api.js já mandou para o login
      r = e.status === 403 ? semPermissao()
        : { html: `<div class="err">Não foi possível carregar os dados.<br><small>${esc(e.message)}</small><br><br><button class="btn ghost" id="retry">Tentar novamente</button></div>`, mount: () => { $('#retry').onclick = route; } };
    }
  }
  if (id !== navId) return;
  view().innerHTML = r.html;
  view().classList.remove('page-in'); void view().offsetWidth; view().classList.add('page-in');
  bar(false);
  if (r.mount) r.mount();
  atualizaNotif();
}
document.body.insertAdjacentHTML('beforeend', '<div id="scrim"></div>');
const drawer = on => { $('#side').classList.toggle('open', on); document.body.classList.toggle('drawer', on); $('#bg').setAttribute('aria-expanded', on); };
$('#bg').onclick = () => drawer(!$('#side').classList.contains('open'));
document.addEventListener('click', e => { if (e.target.id === 'scrim') drawer(false); });
addEventListener('keydown', e => { if (e.key === 'Escape') drawer(false); });
addEventListener('hashchange', route);

// ------------------------------------------------------------------ componentes
const kpi = (l, v) => `<div class="card kpi"><b>${esc(v ?? 'N/D')}</b><span>${esc(l)}</span></div>`;

const VERIF = '<svg class="vf" viewBox="0 0 24 24" aria-label="Professor verificado"><title>Professor verificado</title><circle cx="12" cy="12" r="11"/><path d="M7 12.5l3.2 3.2L17 9"/></svg>';
function postCard(t) {
  ESTADO.set('topico:' + t.id, t);
  const tags = (t.tags || []).map(x => `<span class="tag">${esc(String(x).replace(/^#+/, ''))}</span>`).join('');
  return `<article class="card tw post" data-t="${t.id}">${avatar({ nome: t.autor || '?', id: t.autor_id, tem_foto: t.autor_foto }, 44)}
    <div class="tw-b">${t.repostou ? `<div class="rt-by">${ic('repost')} Você repostou</div>` : ''}<div class="tw-h"><b class="who" ${t.autor_id ? `data-u="${t.autor_id}"` : ''}>${esc(t.autor || 'Anônimo')}</b><span class="mut">· ${esc(fmtData(t.criado_em))}</span></div>
    <h3>${esc(t.titulo)}</h3><div class="tw-t">${esc(t.descricao || '')}</div>${tags ? `<div style="margin-top:6px">${tags}</div>` : ''}
    <div class="tw-a"><span title="Respostas">${ic('msg')} ${t.respostas ?? 0}</span>${likeBtn(t, 'topico', t.id)}${repostBtn(t)}</div></div></article>`;
}

// árvore de respostas: cada resposta aceita resposta (parent_id); abaixo de 3 níveis o recuo para de crescer
function arvore(rs, ehNova) {
  const por = new Map(), ids = new Set(rs.map(r => r.id));
  rs.forEach(r => { const k = r.parent_id && ids.has(r.parent_id) ? r.parent_id : 0; if (!por.has(k)) por.set(k, []); por.get(k).push(r); });
  const no = (r, d) => {
    ESTADO.set('resposta:' + r.id, r);
    const filhos = por.get(r.id) || [];
    return `<div class="tw re ${ehNova(r) ? 'novo' : ''}" data-role="${esc(r.autor_perfil || 'aluno')}">${avatar({ nome: r.autor, id: r.autor_id, tem_foto: r.autor_foto }, 40)}<div class="tw-b"><div class="tw-h"><b class="who" ${r.autor_id ? `data-u="${r.autor_id}"` : ''}>${r.autor_id && r.autor_verificado ? `<a href="#/professor/${r.autor_id}" data-x>${esc(r.autor)}</a>` : esc(r.autor)}</b>${r.autor_verificado ? VERIF : ''}${r.autor_perfil === 'admin' ? '<span class="badge b-admin">Admin</span>' : r.autor_perfil === 'professor' ? '<span class="badge b-professor">Professor</span>' : ''}<span class="mut">· ${esc(fmtData(r.criado_em))}</span></div>
      <div class="tw-t">${esc(r.conteudo)}</div>
      <div class="tw-a">${likeBtn(r, 'resposta', r.id)}<button class="rp" data-rp="${r.id}" type="button">${ic('reply')} Responder</button></div>
      <div class="re-compose" id="rpc-${r.id}" hidden><textarea rows="2" maxlength="5000" placeholder="Responder a ${esc(r.autor)}"></textarea><div class="btnrow"><button class="btn pill" data-send="${r.id}" type="button">Responder</button></div></div></div></div>${filhos.length ? `<div class="re-kids ${d >= 2 ? 'flat' : ''}">${filhos.map(k => no(k, d + 1)).join('')}</div>` : ''}`;
  };
  return (por.get(0) || []).map(r => no(r, 0)).join('');
}

// Modal "Nova dúvida" com autocomplete (consulta a AVL no backend enquanto digita)
function novaDuvida() {
  const tags = [];
  let sugestoes = [], idx = -1, timer = null, seq = 0;
  const m = document.createElement('div');
  m.className = 'modal';
  m.innerHTML = `<div class="card" role="dialog" aria-modal="true" aria-label="Nova dúvida"><h2>Nova dúvida</h2>
    <p class="sub">Publicando como <b>${esc(EU.nome)}</b></p>
    <input id="ti" maxlength="150" placeholder="Título" autocomplete="off">
    <textarea id="de" rows="4" maxlength="2000" placeholder="Descreva sua dúvida"></textarea>
    <div class="chips" id="ch"></div>
    <input id="tg" placeholder="Tags: digite 2+ letras, escolha uma sugestão ou aperte Enter" autocomplete="off">
    <div class="sug" id="sg" style="display:none"></div>
    <div class="btnrow"><button class="btn ghost" id="cx">Cancelar</button><button class="btn" id="ok">Publicar dúvida</button></div></div>`;
  document.body.append(m);
  const onEsc = e => { if (e.key === 'Escape') fechar(); };
  const fechar = () => { m.remove(); document.removeEventListener('keydown', onEsc); };
  document.addEventListener('keydown', onEsc);
  m.onclick = e => { if (e.target === m) fechar(); };
  const q = s => m.querySelector(s);
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
      await post(EP.topicos, { titulo: q('#ti').value, descricao: q('#de').value, tags });
      fechar(); toast('Dúvida publicada!'); route();
    } catch (e) { toast(e.message, true); b.disabled = false; }
  };
}

// Modal da dúvida em formato de conversa (estilo rede social): post, caixa de resposta e respostas em fio
async function abrirDuvida(t) {
  if (!t) return;
  ESTADO.set('topico:' + t.id, t);
  const m = document.createElement('div');
  m.className = 'modal';
  m.innerHTML = '<div class="card thread" role="dialog" aria-modal="true"></div>';
  document.body.append(m);
  const onEsc = e => { if (e.key === 'Escape') fechar(); };
  const fechar = () => { m.remove(); document.removeEventListener('keydown', onEsc); };
  document.addEventListener('keydown', onEsc);
  m.onclick = e => { if (e.target === m) fechar(); };
  const box = m.firstChild;
  const vistos = new Set(); let primeira = true;
  const carregar = async () => {
    let rs = [];
    try { rs = await req(`${EP.topicos}/${t.id}/respostas`); } catch (e) { toast(e.message, true); }
    box.innerHTML = `<div class="th-top"><button class="icon-btn" id="rx" type="button" aria-label="Fechar">←</button><b>Dúvida</b></div>
      <div class="th-post is-root"><div class="tw-h">${avatar({ nome: t.autor || '?', id: t.autor_id, tem_foto: t.autor_foto }, 44)}<div><b class="who" ${t.autor_id ? `data-u="${t.autor_id}"` : ''}>${esc(t.autor || 'Anônimo')}</b><div class="mut">${esc(fmtData(t.criado_em))}</div></div></div>
        <h2 class="th-title">${esc(t.titulo)}</h2><div class="th-desc">${esc(t.descricao || '')}</div>${(t.tags || []).map(x => `<span class="tag">${esc(String(x).replace(/^#+/, ''))}</span>`).join('')}
        <div class="tw-a"><span><b>${rs.length}</b> respostas</span>${likeBtn(t, 'topico', t.id)}${repostBtn(t)}</div></div>
      <div class="th-compose">${avatar(EU, 40)}<div style="flex:1"><textarea id="rc" rows="2" maxlength="5000" placeholder="Poste sua resposta"></textarea>
        <div class="th-foot"><span class="mut" id="cnt">0/5000</span><button class="btn pill" id="rk" type="button" disabled>Responder</button></div></div></div>
      <div class="th-list th-tree">${arvore(rs, r => !primeira && !vistos.has(r.id)) || '<div class="empty" style="border:0">Ainda sem respostas. Seja o primeiro a responder.</div>'}</div>`;
    rs.forEach(r => vistos.add(r.id)); primeira = false;
    const ta = box.querySelector('#rc'), bt = box.querySelector('#rk');
    box.querySelector('#rx').onclick = fechar;
    box.onclick = async e => {                           // responder a uma resposta (qualquer perfil)
      const rp = e.target.closest('[data-rp]');
      if (rp) { const el = box.querySelector(`#rpc-${rp.dataset.rp}`), abre = el.hidden; box.querySelectorAll('.re-compose').forEach(x => x.hidden = true); el.hidden = !abre; if (abre) el.querySelector('textarea').focus(); return; }
      const sd = e.target.closest('[data-send]');
      if (!sd) return;
      const ta2 = box.querySelector(`#rpc-${sd.dataset.send} textarea`);
      if (!ta2.value.trim()) return;
      sd.disabled = true;
      try {
        const r = await post(`${EP.topicos}/${t.id}/respostas`, { conteudo: ta2.value, pai_id: +sd.dataset.send });
        toast(r.status === 'pendente' ? 'Resposta enviada para moderação.' : 'Resposta publicada!');
        await carregar();
      } catch (err) { toast(err.message, true); sd.disabled = false; }
    };
    box.querySelectorAll('[data-x]').forEach(a => a.addEventListener('click', fechar));
    ta.oninput = () => { bt.disabled = !ta.value.trim(); box.querySelector('#cnt').textContent = `${ta.value.length}/5000`; ta.style.height = 'auto'; ta.style.height = ta.scrollHeight + 'px'; };
    bt.onclick = async () => {
      bt.disabled = true;
      try {
        const r = await post(`${EP.topicos}/${t.id}/respostas`, { conteudo: ta.value });
        toast(r.status === 'pendente' ? 'Resposta enviada para moderação.' : 'Resposta publicada!');
        await carregar();
      } catch (e) { toast(e.message, true); bt.disabled = false; }
    };
  };
  await carregar();
}

// ------------------------------------------------------------------ views
async function homeView() {
  const t = await req(EP.topicos);
  let aba = 'recentes', q = '';
  const abas = [['recentes', 'Recentes'], ['curtidas', 'Mais curtidas'], ['abertas', 'Sem resposta'], ['reposts', 'Reposts']];
  const filtra = () => {
    let r = t.filter(x => !q || `${x.titulo} ${x.descricao || ''} ${(x.tags || []).join(' ')} ${x.autor || ''}`.toLowerCase().includes(q));
    if (aba === 'curtidas') r = [...r].sort((a, b) => (b.curtidas || 0) - (a.curtidas || 0) || b.id - a.id);
    if (aba === 'abertas') r = r.filter(x => !x.respostas);
    if (aba === 'reposts') r = r.filter(x => x.repostou);
    return r;
  };
  const rail = async () => {
    const [tg, pr, gr] = await Promise.allSettled([req(EP.tags), req(EP.professores), req(EP.grupos)]);
    const ok = x => x.status === 'fulfilled', set = (id, h) => { const el = $(id); if (el) el.innerHTML = h || '<div class="mut" style="padding:6px 0 10px">Nada por aqui ainda.</div>'; };
    set('#rt1', ok(tg) && [...tg.value].sort((a, b) => b.usage_count - a.usage_count).slice(0, 5).map((x, i) => `<button class="rk" data-tag="${esc(x.display_name)}" type="button"><span class="n">${i + 1}</span><span><b>${esc(String(x.display_name).replace(/^#+/, ''))}</b><small>${x.usage_count} ${x.usage_count === 1 ? 'uso' : 'usos'}</small></span></button>`).join(''));
    set('#rt2', ok(pr) && pr.value.slice(0, 3).map(p => `<a class="rk" href="#/professor/${p.id}">${avatar(p, 38)}<span><b>${esc(p.nome)}</b><small>${esc(p.especialidade || 'Professor')}</small></span></a>`).join(''));
    set('#rt3', ok(gr) && gr.value.slice(0, 3).map(x => `<a class="rk" href="#/grupo/${x.id}"><span class="stat-ic" style="--c:#2F7BFF">${ic('grp')}</span><span><b>${esc(x.nome)}</b><small>${x.participantes} participante(s)</small></span></a>`).join(''));
  };
  return {
    html: `<h1>Comunidade</h1><p class="sub">Tire dúvidas e ajude colegas.</p>
      <div class="home"><div class="feed-col">
        <div class="card ask">${avatar(EU, 44)}<div class="fake" id="ask">O que você gostaria de perguntar?</div><button class="btn" id="nb">+ Criar nova dúvida</button></div>
        <section class="feed"><div class="tabs" role="tablist">${abas.map(([k, l]) => `<button class="tab ${k === aba ? 'on' : ''}" data-aba="${k}" role="tab" type="button">${l}</button>`).join('')}</div><div id="fd"></div></section></div>
      <aside class="rail">
        <div class="search">${ic('search')}<input id="fq" placeholder="Buscar dúvidas" aria-label="Buscar dúvidas" autocomplete="off"></div>
        <section class="card rail-c"><h2>Tags em alta</h2><div id="rt1"><div class="sk" style="height:40px"></div></div></section>
        <section class="card rail-c"><h2>Professores</h2><div id="rt2"><div class="sk" style="height:40px"></div></div></section>
        <section class="card rail-c"><h2>Grupos de estudo</h2><div id="rt3"><div class="sk" style="height:40px"></div></div></section>
      </aside></div>`,
    mount() {
      const desenha = () => { $('#fd').innerHTML = filtra().map(postCard).join('') || `<div class="empty" style="border:0">${t.length ? aba === 'reposts' && !q ? 'Você ainda não repostou nenhuma dúvida.' : 'Nenhuma dúvida encontrada.' : 'Nenhuma dúvida ainda. Seja o primeiro a perguntar!'}</div>`; };
      $('#ask').onclick = $('#nb').onclick = novaDuvida;
      document.querySelectorAll('.tab').forEach(b => b.onclick = () => { aba = b.dataset.aba; document.querySelectorAll('.tab').forEach(x => x.classList.toggle('on', x === b)); desenha(); });
      $('#fq').oninput = e => { q = e.target.value.trim().toLowerCase(); desenha(); };
      view().onclick = e => {
        const g = e.target.closest('[data-tag]');
        if (g) { $('#fq').value = g.dataset.tag.replace(/^#+/, ''); q = $('#fq').value.toLowerCase(); desenha(); return; }
        const c = e.target.closest('[data-t]'); if (c) abrirDuvida(t.find(x => x.id === +c.dataset.t));
      };
      desenha(); rail();
    },
  };
}

async function tagsView() {
  const criar = pode('admin', 'professor'), remover = pode('admin');
  const carregar = async () => (await req(EP.tags)).map(x => ({ n: x.display_name, k: x.key, u: x.usage_count, d: x.description }));
  let tags = await carregar();
  return {
    html: `<h1>Tags</h1><p class="sub">Dicionário de tags armazenado na árvore AVL.</p>
      ${criar ? `<div class="card" style="margin:12px 0"><h2>Nova tag</h2><div style="display:flex;gap:10px;flex-wrap:wrap"><input id="nn" placeholder="Nome da tag" style="flex:1;min-width:160px;margin:0" maxlength="40"><input id="nd" placeholder="Descrição (opcional)" style="flex:2;min-width:200px;margin:0" maxlength="200"><button class="btn" id="na">Adicionar</button></div></div>` : ''}
      <div style="display:flex;gap:10px;margin-top:12px"><input id="q" placeholder="Pesquisar tag..."><select id="o" style="width:180px"><option value="n">A–Z</option><option value="u">Mais usadas</option></select></div>
      <div class="grid" id="ls"></div>`,
    mount() {
      const desenha = () => {
        const q = $('#q').value.toLowerCase(), o = $('#o').value;
        const r = tags.filter(x => x.n.toLowerCase().includes(q)).sort(o === 'u' ? (a, b) => b.u - a.u || a.n.localeCompare(b.n) : (a, b) => a.n.localeCompare(b.n));
        $('#ls').innerHTML = r.map(x => `<div class="card"><span class="tag">${esc(x.n)}</span><div class="mut">${x.u} usos</div>${x.d ? `<div class="sub">${esc(x.d)}</div>` : ''}${pode('admin') ? `<button class="btn ghost" data-edit-tag="${esc(x.k)}" style="margin-top:8px;padding:4px 10px">Editar descrição</button>` : ''}${remover ? `<button class="btn ghost danger" data-k="${esc(x.k)}" style="margin-top:8px;padding:4px 10px">Remover</button>` : ''}</div>`).join('')
          || '<div class="empty" style="grid-column:1/-1">Nenhuma tag encontrada.</div>';
      };
      $('#q').oninput = $('#o').onchange = desenha;
      desenha();
      if (!criar) return;
      $('#na').onclick = async () => {
        const b = $('#na'); b.disabled = true;
        try { await post(EP.tags, { nome: $('#nn').value, descricao: $('#nd').value }); toast('Tag criada!'); route(); }
        catch (e) { toast(e.message, true); b.disabled = false; }
      };
      if (pode('admin')) $('#ls').addEventListener('click', async e => { const k=e.target.dataset.editTag; if(k){const atual=tags.find(x=>x.k===k); const n=prompt('Nome da tag:',atual?.n||k); if(n===null)return; const d=prompt('Descrição da tag:',atual?.d||''); if(d===null)return; try{await patch(`${EP.tags}/${encodeURIComponent(k)}`,{nome:n,descricao:d});toast('Tag atualizada.');tags=await carregar();desenha()}catch(err){toast(err.message,true)}} });
      if (remover) $('#ls').onclick = async e => {
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

// Visão geral do painel: KPIs com ícone, uso das tags (rosca), ranking, alerta de moderação e atividade recente
const kpiCard = (icone, rotulo, valor, cor) => `<div class="card stat" style="--c:${cor}"><span class="stat-ic">${ic(icone)}</span><div><b>${esc(valor ?? 'N/D')}</b><span>${esc(rotulo)}</span></div></div>`;
function dashHtml(d) {
  const pu = d.tags ? d.tags_usadas / d.tags * 100 : null, top = d.top_tags || [], max = Math.max(1, ...top.map(x => x.usage_count));
  return `${d.pendentes ? `<div class="aviso alerta"><span><b>${d.pendentes}</b> item(ns) aguardando moderação.</span><button class="btn" data-go="moderacao" type="button">Revisar</button></div>` : ''}
    <div class="grid stats">${kpiCard('users', 'Usuários', d.usuarios, '#2F7BFF')}${kpiCard('msg', 'Dúvidas', d.topicos, '#22D3EE')}${kpiCard('list', 'Respostas', d.respostas, '#00B2FF')}${kpiCard('cap', 'Professores', d.professores, '#38BDF8')}${kpiCard('grp', 'Grupos', d.grupos, '#6366F1')}${kpiCard('tag', 'Tags', d.tags, '#60A5FA')}</div>
    <div class="two">
      <div class="card"><h2>Uso das tags</h2>${pu == null ? '<div class="empty">Sem tags ainda</div>' : `<div class="donut-wrap"><svg width="120" height="120" viewBox="0 0 42 42"><circle cx="21" cy="21" r="15.9" fill="none" stroke="#24324A" stroke-width="5"/><circle cx="21" cy="21" r="15.9" fill="none" stroke="#22D3EE" stroke-width="5" stroke-linecap="round" stroke-dasharray="${pu} ${100 - pu}" transform="rotate(-90 21 21)"/><text x="21" y="23.5" text-anchor="middle" fill="#F1F5F9" font-size="8" font-weight="700">${pu.toFixed(0)}%</text></svg>
        <div><div class="row"><span>Utilizadas</span><b>${d.tags_usadas}</b></div><div class="row"><span>Não utilizadas</span><b>${d.tags - d.tags_usadas}</b></div><div class="row"><span>Altura da AVL</span><b>${d.altura ?? 'N/D'}</b></div><div class="row"><span>Rotações</span><b>${d.rotacoes ? d.rotacoes.total : 'N/D'}</b></div></div></div>`}</div>
      <div class="card"><h2>Tags mais utilizadas</h2>${top.map((x, i) => `<div class="rank"><span>${i + 1}. ${esc(x.tag)}</span><div class="bar"><i style="width:${x.usage_count / max * 100}%"></i></div><b>${x.usage_count}</b></div>`).join('') || '<div class="empty">Sem dados ainda</div>'}</div>
    </div>
    <div class="card" style="margin-top:14px"><h2>Atividade recente</h2>${(d.atividades || []).map(x => `<div class="row"><span>${esc(x.usuario)} — ${esc(x.acao)}<div class="mut">${esc(fmtData(x.data))}</div></span><span class="badge ${/^ok/.test(x.resultado) ? 'b-ok' : 'b-warn'}">${esc(x.resultado)}</span></div>`).join('') || '<div class="empty">Sem atividades recentes.</div>'}</div>`;
}

async function painelAdminView() {
  const tabs = [['dashboard','Visão geral'],['professores','Professores'],['topicos','Tópicos'],['respostas','Respostas'],['moderacao','Moderação'],['palavras-restritas','Palavras restritas'],['grupos','Grupos'],['configuracoes','Configurações']];
  return { html:`<h1>Painel administrativo</h1><p class="sub">Gestão e diagnóstico do Fórum AVL.</p>
    <div class="btnrow" id="adminTabs" style="justify-content:flex-start;flex-wrap:wrap">${tabs.map((t,i)=>`<button class="btn ${i?'ghost':''}" data-tab="${t[0]}">${t[1]}</button>`).join('')}</div><section id="adminArea"></section>`,
    mount(){
      const area=$('#adminArea'); let active='dashboard';
      const run=async (path,opts={})=>req(`${EP.admin}/${path}`,opts);
      const action=async (method,path,data)=>req(`${EP.admin}/${path}`,{method,body:JSON.stringify(data||{})});
      async function load(tab){ active=tab; $('#adminTabs').querySelectorAll('button').forEach(b=>b.classList.toggle('ghost',b.dataset.tab!==tab)); area.innerHTML='<div class="sk"></div>';
        try {
          if(tab==='dashboard') { const d=await req(EP.dashboard); area.innerHTML=dashHtml(d); area.querySelectorAll('[data-go]').forEach(b=>b.onclick=()=>load(b.dataset.go)); }
          if(tab==='professores'){const a=await run(tab);area.innerHTML=`<div class="card scroll"><table><tr><th>Professor</th><th>Formação</th><th>Especialidade</th><th>Descrição profissional</th><th>Ação</th></tr>${a.map(x=>`<tr><td>${esc(x.nome)}</td><td><input data-f="formacao" data-id="${x.id}" value="${esc(x.formacao)}"></td><td><input data-f="especialidade" data-id="${x.id}" value="${esc(x.especialidade)}"></td><td><textarea data-f="descricao_profissional" data-id="${x.id}">${esc(x.descricao_profissional)}</textarea></td><td><button class="btn" data-save-prof="${x.id}">Salvar</button></td></tr>`).join('')}</table></div>`;area.querySelectorAll('[data-save-prof]').forEach(b=>b.onclick=async()=>{const id=b.dataset.saveProf, d={};area.querySelectorAll(`[data-id="${id}"]`).forEach(i=>d[i.dataset.f]=i.value);try{await action('PATCH',`professores/${id}`,d);toast('Professor atualizado.')}catch(e){toast(e.message,true)}});}
          if(tab==='topicos'){const a=await run('topicos');area.innerHTML=`<div class="card scroll"><table><tr><th>Tópico</th><th>Autor</th><th>Estado</th><th>Ações</th></tr>${a.map(x=>`<tr><td><input data-title="${x.id}" value="${esc(x.titulo)}"><textarea data-desc="${x.id}">${esc(x.descricao)}</textarea></td><td>${esc(x.autor)}</td><td>${x.oculto?'Oculto':esc(x.status_moderacao||'aprovado')}</td><td><button class="btn" data-edit-topic="${x.id}">Salvar</button> <button class="btn ghost" data-hide="${x.id}">${x.oculto?'Exibir':'Ocultar'}</button> <button class="btn ghost danger" data-delete-topic="${x.id}">Excluir</button></td></tr>`).join('')}</table></div>`;area.querySelectorAll('[data-edit-topic]').forEach(b=>b.onclick=async()=>{const id=b.dataset.editTopic;try{await action('PATCH',`topicos/${id}`,{titulo:area.querySelector(`[data-title="${id}"]`).value,descricao:area.querySelector(`[data-desc="${id}"]`).value});toast('Tópico atualizado.')}catch(e){toast(e.message,true)}});area.querySelectorAll('[data-hide]').forEach(b=>b.onclick=async()=>{try{await action('POST',`topicos/${b.dataset.hide}/${b.textContent==='Exibir'?'mostrar':'ocultar'}`);load(tab)}catch(e){toast(e.message,true)}});area.querySelectorAll('[data-delete-topic]').forEach(b=>b.onclick=async()=>{if(confirm('Excluir tópico e respostas?'))try{await action('DELETE',`topicos/${b.dataset.deleteTopic}`);load(tab)}catch(e){toast(e.message,true)}});}
          if(tab==='respostas'){const a=await run(tab);area.innerHTML=`<div class="card scroll"><table><tr><th>ID</th><th>Tópico</th><th>Autor</th><th>Resposta</th><th></th></tr>${a.map(x=>`<tr><td>${x.id}</td><td>${x.topico_id}</td><td>${esc(x.autor)}</td><td>${esc(x.conteudo)}</td><td><button class="btn ghost danger" data-del-reply="${x.id}">Excluir</button></td></tr>`).join('')}</table></div>`;area.querySelectorAll('[data-del-reply]').forEach(b=>b.onclick=async()=>{if(confirm('Excluir resposta?')){await action('DELETE',`respostas/${b.dataset.delReply}`);load(tab)}})}
          if(tab==='moderacao'){const a=await run(tab);area.innerHTML=`<div class="card scroll"><table><tr><th>Tipo / item</th><th>Motivo</th><th>Status</th><th>Ações</th></tr>${a.map(x=>`<tr><td>${esc(x.tipo)} #${x.item_id}<div class="sub">${esc(x.conteudo||'(conteúdo removido)')}</div></td><td>${esc(x.motivo)}</td><td>${esc(x.status)}</td><td>${x.status==='pendente'?`<button class="btn" data-approve="${x.id}">Aprovar</button> <button class="btn ghost danger" data-reject="${x.id}">Excluir</button>`:''}</td></tr>`).join('')}</table></div>`;area.querySelectorAll('[data-approve]').forEach(b=>b.onclick=async()=>{await action('POST',`moderacao/${b.dataset.approve}/aprovar`);load(tab)});area.querySelectorAll('[data-reject]').forEach(b=>b.onclick=async()=>{if(confirm('Excluir conteúdo sinalizado?')){await action('POST',`moderacao/${b.dataset.reject}/excluir`);load(tab)}})}
          if(tab==='palavras-restritas'){const a=await run(tab);area.innerHTML=`<div class="card"><h2>Adicionar palavra</h2><input id="newWord" placeholder="Palavra ou expressão"><button class="btn" id="addWord">Cadastrar</button></div><div class="card">${a.map(x=>`<div class="row"><input data-word="${x.id}" value="${esc(x.palavra)}"><label><input type="checkbox" data-active="${x.id}" ${x.ativo?'checked':''}> Ativa</label><button class="btn" data-save-word="${x.id}">Salvar</button><button class="btn ghost danger" data-del-word="${x.id}">Remover</button></div>`).join('')}</div>`;$('#addWord').onclick=async()=>{try{await action('POST',tab,{palavra:$('#newWord').value});load(tab)}catch(e){toast(e.message,true)}};area.querySelectorAll('[data-save-word]').forEach(b=>b.onclick=async()=>{const id=b.dataset.saveWord;await action('PATCH',`${tab}/${id}`,{palavra:area.querySelector(`[data-word="${id}"]`).value,ativo:area.querySelector(`[data-active="${id}"]`).checked});load(tab)});area.querySelectorAll('[data-del-word]').forEach(b=>b.onclick=async()=>{await action('DELETE',`${tab}/${b.dataset.delWord}`);load(tab)})}
          if(tab==='grupos'){const a=await run(tab);area.innerHTML=`<div class="card"><h2>Novo grupo</h2><input id="groupName" placeholder="Nome"><input id="groupDesc" placeholder="Descrição"><button class="btn" id="addGroup">Criar grupo</button></div><div class="card">${a.map(x=>`<div class="row"><div style="flex:1"><input data-gname="${x.id}" value="${esc(x.nome)}"><input data-gdesc="${x.id}" value="${esc(x.descricao)}"><span class="mut">${x.membros} membros</span></div><button class="btn ghost" data-members="${x.id}">Consultar membros</button><button class="btn ghost" data-add-member="${x.id}">Adicionar por ID</button><button class="btn" data-save-group="${x.id}">Salvar</button><button class="btn ghost danger" data-del-group="${x.id}">Excluir</button></div>`).join('')}</div>`;$('#addGroup').onclick=async()=>{try{await action('POST',tab,{nome:$('#groupName').value,descricao:$('#groupDesc').value});load(tab)}catch(e){toast(e.message,true)}};area.querySelectorAll('[data-save-group]').forEach(b=>b.onclick=async()=>{const id=b.dataset.saveGroup;await action('PATCH',`${tab}/${id}`,{nome:area.querySelector(`[data-gname="${id}"]`).value,descricao:area.querySelector(`[data-gdesc="${id}"]`).value});load(tab)});area.querySelectorAll('[data-del-group]').forEach(b=>b.onclick=async()=>{if(confirm('Excluir grupo?')){await action('DELETE',`${tab}/${b.dataset.delGroup}`);load(tab)}});area.querySelectorAll('[data-members]').forEach(b=>b.onclick=async()=>{try{const ms=await run(`grupos/${b.dataset.members}/membros`);alert(ms.map(m=>`${m.id} · ${m.nome} (${m.perfil})`).join('\n')||'Grupo sem membros.')}catch(e){toast(e.message,true)}});area.querySelectorAll('[data-add-member]').forEach(b=>b.onclick=async()=>{const uid=prompt('ID do usuário para adicionar ao grupo:');if(!uid)return;try{await action('POST',`grupos/${b.dataset.addMember}/membros`,{usuario_id:Number(uid)});load(tab)}catch(e){toast(e.message,true)}})}
          if(tab==='configuracoes'){const d=await run(tab);area.innerHTML=`<div class="card"><h2>Sistema</h2><div class="row"><span>Aplicação</span><b>${esc(d.sistema.app)}</b></div><div class="row"><span>Ambiente</span><b>${esc(d.sistema.modo)}</b></div><h2>Banco de dados</h2><div class="row"><span>Conectado</span><b>${d.banco.conectado?'Sim':'Não'}</b></div><div class="row"><span>Modo</span><b>${esc(d.banco.modo||'—')}</b></div><div class="row"><span>Versão</span><b>${esc(d.banco.versao||'—')}</b></div><div class="row"><span>Esquema</span><b>${d.banco.esquema_ok?'Completo':'Pendente'}</b></div></div>`;}
        }catch(e){area.innerHTML=`<div class="err">${esc(e.message)}</div>`}
      }
      $('#adminTabs').onclick=e=>{const t=e.target.dataset.tab;if(t)load(t)};load(active);
    }};
}

async function avlView() {
  const d = await req(EP.avl);
  const root = treeRoot(d);
  const rot = d.rotacoes;
  return {
    html: `<h1>Árvore AVL</h1><p class="sub">Visualização dos dados reais do backend (fonte da verdade).</p>
      <div class="btnrow" style="justify-content:flex-start;margin:12px 0"><button class="btn" id="tt">Executar teste aula1 → aula20</button><button class="btn ghost" id="rl" style="display:none">Voltar à árvore real</button><button class="btn ghost" id="tx">Ver em texto</button></div>
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

// ------------------------------------------------------------------ usuários (admin)
const badgesUsuario = u => [
  u.principal ? '<span class="badge b-info">Principal</span>' : '',
  `<span class="badge ${u.status === 'ativo' ? 'b-ok' : 'b-err'}">${u.status === 'ativo' ? 'Ativo' : 'Bloqueado'}</span>`,
  u.perfil === 'professor' ? (u.verificado ? '<span class="badge b-ok">Verificado</span>' : '<span class="badge b-warn">Aguardando verificação</span>') : '',
].join('');

function acoesUsuario(u) {
  const eu = u.id === EU.id, a = [];
  if (!u.principal || eu) a.push(['editar', 'Editar', '']);
  if (u.perfil === 'professor') a.push(u.verificado ? ['revogar-verificacao', 'Revogar verificação', 'ghost'] : ['verificar', 'Verificar professor', '']);
  if (!u.principal && !eu) {
    a.push(u.status === 'ativo' ? ['bloquear', 'Bloquear', 'ghost'] : ['desbloquear', 'Desbloquear', 'ghost']);
    a.push(['excluir', 'Excluir', 'ghost danger']);
  }
  return a.map(([k, t, c]) => `<button class="btn ${c}" data-a="${k}" data-id="${u.id}" type="button">${t}</button>`).join('');
}

function formUsuario(u, ok) {
  const novo = !u, eu = u && u.id === EU.id;
  const m = document.createElement('div');
  m.className = 'modal';
  m.innerHTML = `<form class="card" role="dialog" aria-modal="true" aria-label="${novo ? 'Novo usuário' : 'Editar usuário'}" novalidate>
    <h2>${novo ? 'Novo usuário' : 'Editar usuário'}</h2>
    <label for="u-nome">Nome</label><input id="u-nome" maxlength="100" value="${esc(u ? u.nome : '')}" required>
    <label for="u-email">E-mail</label><input id="u-email" type="email" autocomplete="off" value="${esc(u ? u.email : '')}" required>
    <label for="u-perfil">Perfil</label>
    <select id="u-perfil" ${eu ? 'disabled' : ''}>${Object.entries(ROTULO).map(([k, v]) => `<option value="${k}" ${u && u.perfil === k ? 'selected' : ''}>${v}</option>`).join('')}</select>
    <p class="mut" id="u-dica" style="margin:-4px 0 10px">Professores só conseguem entrar depois de verificados por um administrador.</p>
    ${eu ? '' : `<label for="u-senha">${novo ? 'Senha inicial' : 'Nova senha (deixe em branco para manter)'} <span class="mut">mín. 10 caracteres, com letras e números</span></label>
    <input id="u-senha" type="password" autocomplete="new-password" maxlength="128" ${novo ? 'required' : ''}>`}
    <p class="msg" id="u-msg" role="alert"></p>
    <div class="btnrow"><button class="btn ghost" type="button" id="u-cx">Cancelar</button><button class="btn" type="submit">${novo ? 'Cadastrar' : 'Salvar'}</button></div></form>`;
  document.body.append(m);
  const q = x => m.querySelector(x);
  const fechar = () => { m.remove(); document.removeEventListener('keydown', onEsc); };
  const onEsc = e => { if (e.key === 'Escape') fechar(); };
  document.addEventListener('keydown', onEsc);
  q('#u-cx').onclick = fechar;
  const dica = () => { q('#u-dica').style.display = q('#u-perfil').value === 'professor' ? '' : 'none'; };
  q('#u-perfil').onchange = dica; dica();
  q('#u-nome').focus();
  m.querySelector('form').onsubmit = async ev => {
    ev.preventDefault();
    const b = q('button[type=submit]'); b.disabled = true; q('#u-msg').textContent = '';
    const corpo = { nome: q('#u-nome').value, email: q('#u-email').value };
    if (!eu) corpo.perfil = q('#u-perfil').value;
    if (q('#u-senha') && (novo || q('#u-senha').value)) corpo.senha = q('#u-senha').value;
    try {
      if (novo) await post(EP.usuarios, corpo); else await patch(`${EP.usuarios}/${u.id}`, corpo);
      fechar(); toast(novo ? 'Usuário cadastrado.' : 'Alterações salvas.'); ok();
    } catch (e) { q('#u-msg').textContent = e.message.replace(/ \(\/api\/[^)]*\)$/, ''); b.disabled = false; }
  };
}

async function usuariosView() {
  let lista = await req(EP.usuarios);
  const recarregar = async () => { lista = await req(EP.usuarios); desenha(); };
  let desenha = () => {};
  const pend = () => lista.filter(u => u.perfil === 'professor' && !u.verificado && u.status === 'ativo').length;
  return {
    html: `<h1>Usuários</h1><p class="sub">Somente administradores cadastram contas. Cada ação é conferida no servidor.</p>
      <div id="avisoPend"></div>
      <div class="toolbar"><input id="q" placeholder="Pesquisar nome ou e-mail..." aria-label="Pesquisar">
        <select id="fp" aria-label="Filtrar por perfil"><option value="">Todos os perfis</option>${Object.entries(ROTULO).map(([k, v]) => `<option value="${k}">${v}</option>`).join('')}</select>
        <select id="fs" aria-label="Filtrar por situação"><option value="">Todas as situações</option><option value="ativo">Ativos</option><option value="bloqueado">Bloqueados</option><option value="pendente">Professores aguardando verificação</option></select>
        <button class="btn" id="novo" type="button">+ Novo usuário</button></div>
      <div class="card scroll"><table><thead><tr><th>Nome</th><th>Perfil</th><th>Situação</th><th>Último acesso</th><th>Ações</th></tr></thead><tbody id="tb"></tbody></table></div>`,
    mount() {
      desenha = () => {
        const q = $('#q').value.toLowerCase(), fp = $('#fp').value, fs = $('#fs').value;
        const r = lista.filter(u => (!q || (u.nome + ' ' + u.email).toLowerCase().includes(q)) && (!fp || u.perfil === fp)
          && (!fs || (fs === 'pendente' ? u.perfil === 'professor' && !u.verificado : u.status === fs)));
        $('#tb').innerHTML = r.map(u => `<tr><td><b>${esc(u.nome)}</b><br><span class="mut">${esc(u.email)}</span></td><td>${ROTULO[u.perfil]}</td>
          <td>${badgesUsuario(u)}</td><td class="nowrap">${u.ultimo_login ? esc(fmtData(u.ultimo_login)) : '<span class="mut">nunca</span>'}</td>
          <td><div class="acoes">${acoesUsuario(u)}</div></td></tr>`).join('') || '<tr><td colspan="5" class="mut">Nenhum usuário encontrado.</td></tr>';
        const n = pend();
        $('#avisoPend').innerHTML = n ? `<div class="aviso">${n} professor(es) aguardando verificação administrativa — eles ainda não conseguem entrar.</div>` : '';
      };
      $('#q').oninput = $('#fp').onchange = $('#fs').onchange = desenha;
      $('#novo').onclick = () => formUsuario(null, recarregar);
      $('#tb').onclick = async e => {
        const b = e.target.closest('button[data-a]');
        if (!b) return;
        const u = lista.find(x => x.id === +b.dataset.id), a = b.dataset.a;
        if (!u) return;
        if (a === 'editar') return formUsuario(u, recarregar);
        const textos = { excluir: `Excluir a conta de ${u.nome}? Esta ação não pode ser desfeita.`, bloquear: `Bloquear ${u.nome}? As sessões abertas serão encerradas.`,
          'revogar-verificacao': `Revogar a verificação de ${u.nome}? Ele não poderá entrar até ser verificado de novo.` };
        if (textos[a] && !confirm(textos[a])) return;
        b.disabled = true;
        try {
          if (a === 'excluir') await del(`${EP.usuarios}/${u.id}`); else await post(`${EP.usuarios}/${u.id}/${a}`);
          toast('Feito.'); await recarregar();
        } catch (err) { toast(err.message.replace(/ \(\/api\/[^)]*\)$/, ''), true); b.disabled = false; }
      };
      desenha();
    },
  };
}

// ------------------------------------------------------------------ minha conta
const respGrupo = g => g.responsavel_nome
  ? `${g.responsavel_verificado ? `<a href="#/professor/${g.responsavel_id}">${esc(g.responsavel_nome)}</a> ${SELO}` : esc(g.responsavel_nome)}` : '—';

async function gruposView() {
  const l = await req(EP.grupos), cria = pode('admin', 'professor');
  return {
    html: `<h1>Grupos de estudo</h1><p class="sub">Participe de grupos conduzidos por professores.</p>
      ${cria ? '<div class="card" style="margin:12px 0"><h2>Novo grupo</h2><input id="gn" maxlength="80" placeholder="Nome do grupo"><textarea id="gd" rows="2" maxlength="1000" placeholder="Descrição"></textarea><button class="btn" id="gc">Criar grupo</button></div>' : ''}
      <div class="grid">${l.map(x => `<a href="#/grupo/${x.id}" class="card" style="color:inherit;text-decoration:none"><b>${esc(x.nome)}</b> ${x.participando ? '<span class="badge b-ok">Participando</span>' : ''}<div class="sub">${esc((x.descricao || '').slice(0, 140))}</div><div class="mut">Responsável: ${esc(x.responsavel_nome || '—')}</div><div class="mut">${x.participantes} participante(s)</div></a>`).join('') || '<div class="empty" style="grid-column:1/-1">Nenhum grupo ainda.</div>'}</div>`,
    mount() {
      if (!cria) return;
      $('#gc').onclick = async ev => {
        ev.target.disabled = true;
        try { const g = await post(EP.grupos, { nome: $('#gn').value, descricao: $('#gd').value }); toast('Grupo criado!'); location.hash = `#/grupo/${g.id}`; }
        catch (e) { toast(e.message.replace(/ \(\/api\/[^)]*\)$/, ''), true); ev.target.disabled = false; }
      };
    },
  };
}

async function grupoView() {
  const g = await req(`${EP.grupos}/${window.ROTA_ID}`), aluno = EU.perfil === 'aluno';
  return {
    html: `<a href="#/grupos">← Grupos</a><div class="card" style="margin:14px 0;max-width:720px"><h1 style="margin:0">${esc(g.nome)}</h1>
      <p class="sub" style="white-space:pre-wrap">${esc(g.descricao || 'Sem descrição.')}</p>
      <div class="row"><span>Responsável</span><b>${respGrupo(g)}</b></div>
      ${g.responsavel ? `<div style="display:flex;gap:12px;align-items:center;margin:10px 0">${avatar(g.responsavel, 48)}<div><b>${esc(g.responsavel.especialidade || '')}</b><div class="mut">${esc(g.responsavel.formacao || '')}</div></div></div>` : ''}
      <div class="row"><span>Participantes</span><b>${g.participantes}</b></div>
      <div class="acoes" style="margin-top:10px">${aluno ? `<button class="btn ${g.participando ? 'ghost' : ''}" id="gp">${g.participando ? 'Sair do grupo' : 'Participar'}</button>` : ''}
      ${g.pode_gerenciar ? '<button class="btn ghost" id="ge">Editar</button><button class="btn ghost danger" id="gx">Excluir</button>' : ''}</div></div>
      <div class="card" style="max-width:720px"><h2>Participantes</h2>${g.membros.map(m => `<div class="row" style="align-items:center"><span style="display:flex;gap:10px;align-items:center">${avatar(m, 28)}${esc(m.nome)}</span>${g.pode_gerenciar ? `<button class="btn ghost danger" data-rm="${m.id}">Remover</button>` : ''}</div>`).join('') || '<div class="empty">Ninguém entrou ainda.</div>'}</div>`,
    mount() {
      const base = `${EP.grupos}/${g.id}`, ok = fn => async () => { try { await fn(); } catch (e) { toast(e.message.replace(/ \(\/api\/[^)]*\)$/, ''), true); } };
      if (aluno) $('#gp').onclick = ok(async () => { await post(`${base}/${g.participando ? 'sair' : 'entrar'}`); route(); });
      if (!g.pode_gerenciar) return;
      $('#ge').onclick = ok(async () => {
        const n = prompt('Nome do grupo:', g.nome); if (n === null) return;
        const d = prompt('Descrição:', g.descricao || ''); if (d === null) return;
        await patch(base, { nome: n, descricao: d }); toast('Grupo atualizado.'); route();
      });
      $('#gx').onclick = ok(async () => { if (!confirm('Excluir este grupo?')) return; await del(base); toast('Grupo excluído.'); location.hash = '#/grupos'; });
      view().querySelectorAll('[data-rm]').forEach(b => b.onclick = ok(async () => { await del(`${base}/membros/${b.dataset.rm}`); route(); }));
    },
  };
}

async function notificacoesView() {
  let d = await req(EP.notif);
  const lista = () => d.itens.map(n => `<div class="tw notif ${n.lida ? '' : 'nova'}" data-n="${n.id}" data-t="${n.topico_id}" style="cursor:pointer"><span class="stat-ic" style="--c:#38BDF8">${ic('msg')}</span><div class="tw-b"><div class="tw-h"><b>${esc(n.autor_nome)}</b>${VERIF}<span class="mut">respondeu sua dúvida · ${esc(fmtData(n.criado_em))}</span></div><div class="mut">${esc(n.titulo)}</div><div class="tw-t">${esc(n.previa)}</div></div>${n.lida ? '' : '<i class="dot"></i>'}</div>`).join('') || '<div class="empty" style="border:0">Nenhuma notificação ainda. Você será avisado quando um professor responder suas dúvidas.</div>';
  return {
    html: `<h1>Notificações</h1><p class="sub">Respostas de professores às suas dúvidas.</p><div class="btnrow" style="justify-content:flex-start;margin-bottom:12px"><button class="btn ghost" id="nl" type="button">Marcar todas como lidas</button></div><div class="card" id="nls" style="padding:0">${lista()}</div>`,
    mount() {
      const desenha = () => { $('#nls').innerHTML = lista(); badgeNotif(d.nao_lidas); };
      const iv = setInterval(async () => {
        if (!document.body.contains($('#nls'))) return clearInterval(iv);
        try { d = await req(EP.notif); desenha(); } catch { /* tenta no próximo ciclo */ }
      }, 30000);
      $('#nl').onclick = async () => { try { await post(`${EP.notif}/lidas`); d.itens.forEach(n => n.lida = true); d.nao_lidas = 0; desenha(); } catch (e) { toast(e.message, true); } };
      $('#nls').onclick = async e => {
        const c = e.target.closest('[data-n]'); if (!c) return;
        try { d.nao_lidas = (await post(`${EP.notif}/${c.dataset.n}/lida`)).nao_lidas; d.itens.find(n => n.id === +c.dataset.n).lida = true; desenha(); } catch { /* segue abrindo */ }
        const t = (await req(EP.topicos)).find(x => x.id === +c.dataset.t);
        if (t) abrirDuvida(t); else toast('Esta dúvida não está mais disponível.', true);
      };
    },
  };
}

async function professoresView() {
  const l = await req(EP.professores);
  return {
    html: `<h1>Professores</h1><p class="sub">Professores verificados da comunidade.</p><input id="q" placeholder="Pesquisar por nome ou especialidade..."><div class="grid" id="ls"></div>`,
    mount() {
      const desenha = () => {
        const q = $('#q').value.toLowerCase();
        $('#ls').innerHTML = l.filter(p => (p.nome + ' ' + p.especialidade).toLowerCase().includes(q)).map(p => `<a href="#/professor/${p.id}" class="card" style="display:flex;gap:12px;color:inherit;text-decoration:none">${avatar(p, 56)}<div><b>${esc(p.nome)}</b> ${SELO}<div class="mut">${esc(p.formacao || '')}</div><div><span class="tag">${esc(p.especialidade || 'Sem especialidade')}</span></div><div class="sub">${esc((p.biografia || '').slice(0, 140))}</div></div></a>`).join('') || '<div class="empty" style="grid-column:1/-1">Nenhum professor encontrado.</div>';
      };
      $('#q').oninput = desenha; desenha();
    },
  };
}

async function professorView() {
  const p = await req(`${EP.professores}/${window.ROTA_ID}`);
  return {
    html: `<a href="#/professores">← Professores</a><div class="card" style="margin:14px 0;max-width:720px"><div style="display:flex;gap:16px;align-items:center">${avatar(p, 88)}<div><h1 style="margin:0">${esc(p.nome)}</h1>${SELO}</div></div>
      <div class="row"><span>Formação</span><b>${esc(p.formacao || '—')}</b></div><div class="row"><span>Especialidade</span><b>${esc(p.especialidade || '—')}</b></div>
      ${p.descricao_profissional ? `<h2>Descrição profissional</h2><p class="sub" style="white-space:pre-wrap">${esc(p.descricao_profissional)}</p>` : ''}
      ${p.biografia ? `<h2>Biografia</h2><p class="sub" style="white-space:pre-wrap">${esc(p.biografia)}</p>` : ''}</div>`,
  };
}

// reduz a foto para 256px JPEG no navegador (o servidor ainda valida formato e tamanho)
const lerFoto = f => new Promise((ok, no) => {
  const img = new Image(), url = URL.createObjectURL(f);
  img.onload = () => {
    const k = Math.min(1, 256 / Math.max(img.width, img.height)), c = document.createElement('canvas');
    c.width = Math.round(img.width * k); c.height = Math.round(img.height * k);
    c.getContext('2d').drawImage(img, 0, 0, c.width, c.height); URL.revokeObjectURL(url);
    ok(c.toDataURL('image/jpeg', 0.8));
  };
  img.onerror = () => no(new Error('Imagem inválida.'));
  img.src = url;
});

async function contaView() {
  const pf = await req(EP.perfil), prof = EU.perfil === 'professor';
  return {
    html: `<h1>Minha conta</h1>
      <form class="card" id="fp" style="margin:14px 0;max-width:520px" novalidate><h2>Meu perfil</h2>
        <div style="display:flex;gap:12px;align-items:center;margin-bottom:8px"><span id="pv">${avatar(pf, 64)}</span><div><input id="pf" type="file" accept="image/*" style="margin:0"><button class="btn ghost" type="button" id="pr">Remover foto</button></div></div>
        <input id="pn" maxlength="80" placeholder="Nome" value="${esc(pf.nome)}">
        <textarea id="pi" rows="2" maxlength="500" placeholder="Informações pessoais (visíveis só para você)">${esc(pf.informacoes)}</textarea>
        <textarea id="pb" rows="3" maxlength="1000" placeholder="Biografia">${esc(pf.biografia)}</textarea>
        ${prof ? `<input id="pfo" maxlength="180" placeholder="Formação" value="${esc(pf.formacao)}"><input id="pe" maxlength="180" placeholder="Especialidade" value="${esc(pf.especialidade)}"><textarea id="pd" rows="3" maxlength="2000" placeholder="Descrição profissional">${esc(pf.descricao_profissional)}</textarea>` : ''}
        <button class="btn" type="submit">Salvar perfil</button></form>
      <div class="card" style="margin:14px 0;max-width:520px"><div class="row"><span>Nome</span><b>${esc(EU.nome)}</b></div>
        <div class="row"><span>E-mail</span><b>${esc(EU.email)}</b></div>
        <div class="row"><span>Perfil</span><b>${ROTULO[EU.perfil]}${EU.principal ? ' (principal)' : ''}</b>${EU.verificado ? SELO : ''}</div></div>
      <form class="card" id="fs" style="max-width:520px" novalidate><h2>Trocar senha</h2>
        <input type="text" autocomplete="username" value="${esc(EU.email)}" hidden>
        <input id="sa" type="password" autocomplete="current-password" placeholder="Senha atual" required>
        <input id="sn" type="password" autocomplete="new-password" placeholder="Nova senha (mín. 10, letras e números)" maxlength="128" required>
        <input id="sc" type="password" autocomplete="new-password" placeholder="Repita a nova senha" required>
        <p class="sub">Ao trocar a senha, os outros dispositivos conectados são desconectados.</p>
        <button class="btn" type="submit">Salvar nova senha</button></form>`,
    mount() {
      let foto;                                            // undefined = não mexeu na foto
      $('#pf').onchange = async e => {
        const f = e.target.files[0];
        if (!f) return;                                    // diálogo cancelado: mantém a foto atual
        if (!/^image\//.test(f.type)) { toast('Escolha um arquivo de imagem.', true); e.target.value = ''; return; }
        try { foto = await lerFoto(f); $('#pv').innerHTML = avatar({ nome: pf.nome, foto }, 64); }
        catch (x) { toast(x.message, true); }
        e.target.value = '';
      };
      $('#pr').onclick = () => { foto = ''; $('#pv').innerHTML = avatar({ nome: pf.nome }, 64); };
      $('#fp').onsubmit = async ev => {
        ev.preventDefault();
        const d = { nome: $('#pn').value, informacoes: $('#pi').value, biografia: $('#pb').value };
        if (foto !== undefined) d.foto = foto;
        if (prof) Object.assign(d, { formacao: $('#pfo').value, especialidade: $('#pe').value, descricao_profissional: $('#pd').value });
        try { const r = await patch(EP.perfil, d); EU.nome = r.nome; EU.tem_foto = !!r.foto; $('#pv').innerHTML = avatar(r, 64); shell(location.hash); toast('Perfil atualizado.'); }
        catch (e) { toast(e.message.replace(/ \(\/api\/[^)]*\)$/, ''), true); }
      };
      $('#fs').onsubmit = async ev => {
        ev.preventDefault();
        if ($('#sn').value !== $('#sc').value) return toast('As senhas não coincidem.', true);
        const b = ev.target.querySelector('button'); b.disabled = true;
        try {
          await post(EP.senha, { senha_atual: $('#sa').value, nova_senha: $('#sn').value });
          ev.target.reset(); toast('Senha alterada.');
        } catch (e) { toast(e.message.replace(/ \(\/api\/[^)]*\)$/, ''), true); }
        b.disabled = false;
      };
    },
  };
}

// rota -> [tela, perfis permitidos (só para o menu/UX; o servidor é quem barra de verdade)]
const VIEWS = {
  '#/': [() => (pode('admin') ? painelAdminView() : homeView())], '#/tags': [tagsView], '#/conta': [contaView], '#/professores': [professoresView], '#/professor': [professorView], '#/grupos': [gruposView], '#/notificacoes': [notificacoesView, ['aluno', 'professor']], '#/grupo': [grupoView],
  '#/painel': [painelAdminView, ['admin']], '#/avl': [avlView, ['admin', 'professor']],
  '#/usuarios': [usuariosView, ['admin']], '#/logs': [logsView, ['admin']],
};

(async () => {
  try {
    const d = await req(EP.eu);
    EU = d.usuario; Sessao.csrf = d.csrf;
  } catch (e) {
    if (e.status === 401) { location.replace('login.html'); return; }
    view().innerHTML = `<div class="err">${esc(e.message)}<br><br><a class="btn" href="login.html">Ir para o login</a></div>`;
    return;
  }
  route();
})();

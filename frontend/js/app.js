const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const P={home:'M3 10l9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z',tag:'M20.6 13.4l-7.2 7.2a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8z',users:'M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z',
tree:'M12 3v6M12 9H5v6M12 9h7v6M3 15h4v4H3zM17 15h4v4h-4zM10 3h4v4h-4z',list:'M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01',dash:'M3 3h7v9H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 16h7v5H3z',msg:'M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z',gear:'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM12 2v3M12 19v3M2 12h3M19 12h3'};
const ic=k=>`<svg class="ic" viewBox="0 0 24 24"><path d="${P[k]}"/></svg>`;
const MEM=[['#/','home','Início'],['#/tags','tag','Tags'],['#/membros','users','Membros']];
const ADM=[['#/admin','dash','Dashboard'],['#/admin/avl','tree','Árvore AVL'],['#/admin/tags','tag','Tags'],['#/admin/topicos','msg','Tópicos'],['#/admin/membros','users','Membros'],['#/admin/logs','list','Logs']];
const $=s=>document.querySelector(s),V=()=>$('#view');
function toast(m,e){const t=document.createElement('div');t.className='toast'+(e?' e':'');t.textContent=m;document.body.append(t);setTimeout(()=>t.remove(),3200)}
const skel=()=>V().innerHTML='<div class="sk"></div><div class="sk"></div><div class="sk"></div>';
const fail=e=>V().innerHTML=`<div class="err">Não foi possível carregar os dados.<br><small>${esc(e.message)}</small><br><small>Confira as rotas em js/api.js.</small></div>`;
const nd=v=>v==null?'N/D':v;
function shell(adm,rt){const m=adm?ADM:MEM;
  $('#side').innerHTML=`<div class="logo"><i></i>Fórum AVL</div>${m.map(x=>`<a class="nav ${rt===x[0]?'on':''}" href="${x[0]}">${ic(x[1])}${x[2]}</a>`).join('')}
  <a class="nav" href="${adm?'#/':'#/admin'}">${ic(adm?'home':'gear')}${adm?'Área de membros':'Área administrativa'}</a>
  <div class="user"><div class="av">${adm?'A':'M'}</div><div>${adm?'Administrador':'Membro'}<br>${adm&&localStorage.admin_token?'<a href="#" id="out">Sair</a>':adm?'<a href="admin-cadastro.html">Entrar / cadastrar</a>':''}</div></div>`;
  const o=$('#out');if(o)o.onclick=e=>{e.preventDefault();localStorage.removeItem('admin_token');location.hash='#/'}}
async function route(){const rt=location.hash||'#/',adm=rt.startsWith('#/admin');$('#side').classList.remove('open');shell(adm,rt);
  if(adm&&!localStorage.admin_token){V().innerHTML='<div class="empty">Acesso restrito.<br><br><a class="btn" href="admin-cadastro.html">Entrar como administrador</a></div>';return}
  skel();try{await(VIEWS[rt]||VIEWS['#/'])()}catch(e){if(/401|403|token|autoriz/i.test(e.message)&&adm){localStorage.removeItem('admin_token')}fail(e)}}
$('#bg').onclick=()=>$('#side').classList.toggle('open');addEventListener('hashchange',route);
const tagName=t=>typeof t==='string'?t:pick(t,'display_name','tag','nome','key');
function post_(t){const tg=(pick(t,'tags')||[]).map(x=>`<span class="tag">${esc(tagName(x))}</span>`).join('');
  const a=pick(t,'autor','usuario','codinome'),d=pick(t,'data','created_at','criado_em'),r=pick(t,'respostas','n_respostas'),v=pick(t,'visualizacoes','views');
  return`<div class="card post"><div class="meta">${a?`<div class="av" style="width:24px;height:24px;font-size:11px">${esc(a[0])}</div>${esc(a)}`:''}${d?`<span>${esc(d)}</span>`:''}</div><h3>${esc(pick(t,'titulo','title'))}</h3><div class="sub">${esc(pick(t,'descricao','resumo','description')||'')}</div><div style="margin-top:8px">${tg}</div><div class="meta">${r!=null?`<span>${r} respostas</span>`:''}${v!=null?`<span>${v} visualizações</span>`:''}</div></div>`}
async function novaDuvida(){let tags=[],all=[];try{all=lista(await req(EP.tags)).map(tagName)}catch{}
  const m=document.createElement('div');m.className='modal';m.innerHTML=`<div class="card"><h2>Nova dúvida</h2><input id="ti" placeholder="Título"><textarea id="de" rows="4" placeholder="Descreva sua dúvida"></textarea><div class="chips" id="ch"></div><input id="tg" placeholder="Tags (digite 2+ letras e Enter)" autocomplete="off"><div class="sug" id="sg" style="display:none"></div><div style="display:flex;gap:8px;justify-content:flex-end"><button class="btn ghost" id="cx">Cancelar</button><button class="btn" id="ok">PUBLICAR DÚVIDA</button></div></div>`;document.body.append(m);
  const draw=()=>$('#ch').innerHTML=tags.map((t,i)=>`<span class="tag" data-i="${i}" style="cursor:pointer">${esc(t)} ✕</span>`).join('');
  const add=t=>{t=t.trim();if(t.length>=1&&!tags.some(x=>x.toLowerCase()===t.toLowerCase()))tags.push(t);$('#tg').value='';$('#sg').style.display='none';draw()};
  $('#ch').onclick=e=>{if(e.target.dataset.i){tags.splice(+e.target.dataset.i,1);draw()}};
  $('#tg').oninput=e=>{const q=e.target.value.trim().toLowerCase(),s=$('#sg');if(q.length<2){s.style.display='none';return}
    const r=all.filter(t=>t.toLowerCase().includes(q)).slice(0,6);s.innerHTML=r.map(t=>`<div>${esc(t)}</div>`).join('')||`<div class="mut">Sem resultados — Enter cria "${esc(e.target.value)}"</div>`;s.style.display='block';s.onclick=ev=>ev.target.textContent&&!ev.target.classList.contains('mut')&&add(ev.target.textContent)};
  $('#tg').onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();add(e.target.value)}};
  $('#cx').onclick=()=>m.remove();
  $('#ok').onclick=async()=>{const b=$('#ok');b.disabled=true;try{await post(EP.topicos,{titulo:$('#ti').value,descricao:$('#de').value,tags});m.remove();toast('Dúvida publicada!');route()}catch(e){toast(e.message,1);b.disabled=false}}}
const VIEWS={
'#/':async()=>{const t=lista(await req(EP.topicos));V().innerHTML=`<h1>Comunidade</h1><p class="sub">Tire dúvidas e ajude colegas.</p><div class="card ask"><div class="av">M</div><div class="fake" id="ask">O que você gostaria de perguntar?</div><button class="btn" id="nb">+ Criar nova dúvida</button></div>${t.map(post_).join('')||'<div class="empty">Nenhuma dúvida encontrada.</div>'}`;$('#ask').onclick=$('#nb').onclick=novaDuvida},
'#/tags':async()=>tagsView(false),'#/membros':async()=>membrosView(),
'#/admin/tags':async()=>tagsView(true),'#/admin/membros':async()=>membrosView(),
'#/admin/topicos':async()=>{const t=lista(await req(EP.topicos));V().innerHTML=`<h1>Tópicos</h1>${t.map(post_).join('')||'<div class="empty">Nenhum dado disponível.</div>'}`},
'#/admin/logs':async()=>{const l=lista(await req(EP.logs));V().innerHTML=`<h1>Logs</h1>${l.length?`<div class="card scroll"><table><tr><th>Data</th><th>Usuário</th><th>Ação</th><th>Resultado</th></tr>${l.map(x=>`<tr><td>${esc(nd(pick(x,'data','timestamp','horario')))}</td><td>${esc(nd(pick(x,'usuario','user')))}</td><td>${esc(nd(pick(x,'acao','operacao','action')))}</td><td>${esc(nd(pick(x,'resultado','result')))}</td></tr>`).join('')}</table></div>`:'<div class="empty">Nenhum log disponível no backend.</div>'}`},
'#/admin':async()=>{const [t,g,m,a]=await Promise.all([req(EP.topicos).catch(()=>null),req(EP.tags).catch(()=>null),req(EP.membros).catch(()=>null),req(EP.avl).catch(()=>null)]);
  const tg=g&&lista(g).map(x=>({n:tagName(x),u:pick(x,'usage_count','uso','contador_uso')})),root=a&&treeRoot(a),rot=await rotInfo();
  const tot=tg?tg.length:null,usadas=tg&&tg.every(x=>x.u!=null)?tg.filter(x=>x.u>0).length:null,pu=usadas!=null&&tot?usadas/tot*100:null;
  const K=(l,v)=>`<div class="card kpi"><b>${nd(v)}</b><span>${l}</span></div>`;
  V().innerHTML=`<h1>Dashboard</h1><p class="sub">Estudante → dúvida → tags → backend → AVL → contador/nó/rotação → interface</p><div class="grid" style="margin-top:14px">${K('Membros',m&&lista(m).length)}${K('Tópicos',t&&lista(t).length)}${K('Tags',tot)}${K('Tags utilizadas',usadas)}${K('Altura da AVL',root?H(root):null)}${K('Rotações',rot.total)}</div>
  <div class="two"><div class="card"><h2>Utilização das tags</h2>${pu==null?'<div class="empty">Dados insuficientes</div>':`<div style="display:flex;gap:18px;align-items:center"><svg width="120" height="120" viewBox="0 0 42 42"><circle cx="21" cy="21" r="15.9" fill="none" stroke="#24324A" stroke-width="6"/><circle cx="21" cy="21" r="15.9" fill="none" stroke="#22D3EE" stroke-width="6" stroke-dasharray="${pu} ${100-pu}" transform="rotate(-90 21 21)"/></svg><div>Utilizadas: <b>${pu.toFixed(1)}%</b><br>Não utilizadas: <b>${(100-pu).toFixed(1)}%</b><br><span class="mut">${usadas} de ${tot} tags</span></div></div>`}</div>
  <div class="card"><h2>Tags mais utilizadas</h2>${tg&&tg.some(x=>x.u!=null)?tg.filter(x=>x.u!=null).sort((a,b)=>b.u-a.u).slice(0,8).map((x,i)=>`<div class="row"><span>${i+1}. ${esc(x.n)}</span><b>${x.u}</b></div>`).join(''):'<div class="empty">Dados insuficientes</div>'}</div></div>`},
'#/admin/avl':async()=>{const d=await req(EP.avl),root=treeRoot(d),rot=await rotInfo();
  V().innerHTML=`<h1>Árvore AVL</h1><p class="sub">Visualização dos dados do backend (fonte da verdade).</p><div style="margin:12px 0"><button class="btn" id="tt">EXECUTAR TESTE aula1 → aula20</button></div><div class="grid" id="mt"></div><div class="two" style="grid-template-columns:2fr 1fr"><div class="treebox" id="tb"></div><div class="card" id="pn"><h2>Nó</h2><span class="sub">Clique em um nó.</span><div class="side2"><h2>Rotações</h2>${['LL','RR','LR','RL'].map(k=>`<div class="row"><span>${k}</span><b>${nd(rot.por[k])}</b></div>`).join('')}</div></div></div>`;
  const show=r=>{const pos=desenharArvore(r,$('#tb'),n=>{$('#pn').firstElementChild.outerHTML=`<h2>${esc(n.tag)}</h2>`;$('#pn').querySelector('.sub')&&($('#pn').querySelector('.sub').outerHTML=`<div id="dt"></div>`);
    $('#dt').innerHTML=[['Altura',n.h],['FB',FB(n)],['Uso',n.uso],['Filho esq.',n.l&&n.l.tag],['Filho dir.',n.r&&n.r.tag]].map(x=>`<div class="row"><span>${x[0]}</span><b>${esc(nd(x[1]))}</b></div>`).join('')});
    const f=pos?pos.map(FB):[];$('#mt').innerHTML=[['Altura',r?H(r):null],['Nós',pos?pos.length:null],['Rotações',rot.total],['Maior FB',f.length?Math.max(...f):null],['Menor FB',f.length?Math.min(...f):null]].map(x=>`<div class="card kpi"><b>${nd(x[1])}</b><span>${x[0]}</span></div>`).join('')};show(root);
  $('#tt').onclick=async()=>{const b=$('#tt');b.disabled=true;try{const r=await post(EP.teste);const passos=r&&r.passos;if(Array.isArray(passos))for(const p of passos){show(treeRoot(p.arvore||p.tree||p));await new Promise(s=>setTimeout(s,600))}else show(treeRoot(r)||treeRoot(await req(EP.avl)));toast('Teste executado')}catch(e){toast(e.message,1)}b.disabled=false}}};
async function rotInfo(){try{const d=await req(EP.rotacoes),por={};
  if(Array.isArray(d))d.forEach(x=>{const k=pick(x,'tipo','type');if(k)por[k]=(por[k]||0)+1});else if(d){['LL','RR','LR','RL'].forEach(k=>{if(d[k]!=null)por[k]=d[k]});if(d.por_tipo)Object.assign(por,d.por_tipo)}
  const tot=(d&&d.total)??(Object.keys(por).length?Object.values(por).reduce((a,b)=>a+b,0):null);return{por,total:tot}}catch{return{por:{},total:null}}}
async function tagsView(adm){const t=lista(await req(EP.tags)).map(x=>({n:tagName(x),u:pick(x,'usage_count','uso','contador_uso')}));
  V().innerHTML=`<h1>Tags</h1><div style="display:flex;gap:10px"><input id="q" placeholder="Pesquisar tag..."><select id="o" style="width:180px"><option value="n">A–Z</option><option value="u">Mais usadas</option></select></div><div class="grid" id="ls"></div>`;
  const dr=()=>{const q=$('#q').value.toLowerCase(),o=$('#o').value;let r=t.filter(x=>String(x.n).toLowerCase().includes(q));r.sort(o==='u'?(a,b)=>(b.u||0)-(a.u||0):(a,b)=>String(a.n).localeCompare(b.n));
    $('#ls').innerHTML=r.map(x=>`<div class="card"><span class="tag">${esc(x.n)}</span><div class="mut">${x.u!=null?x.u+' usos':''}</div></div>`).join('')||'<div class="empty" style="grid-column:1/-1">Nenhuma tag cadastrada.</div>'};$('#q').oninput=$('#o').onchange=dr;dr()}
async function membrosView(){const m=lista(await req(EP.membros));
  V().innerHTML=`<h1>Membros</h1><input id="q" placeholder="Pesquisar membro..."><div class="grid" id="ls"></div>`;
  const dr=()=>{const q=$('#q').value.toLowerCase();$('#ls').innerHTML=m.filter(x=>String(pick(x,'nome','codinome','name')).toLowerCase().includes(q)).map(x=>{const n=pick(x,'nome','codinome','name')||'?';return`<div class="card" style="display:flex;gap:12px"><div class="av">${esc(n[0])}</div><div><b>${esc(n)}</b><div class="mut">${esc(pick(x,'funcao','role')||'')}</div><div class="mut">${pick(x,'n_duvidas','duvidas')!=null?pick(x,'n_duvidas','duvidas')+' dúvidas ':''}${pick(x,'n_respostas','respostas')!=null?pick(x,'n_respostas','respostas')+' respostas':''}</div></div></div>`}).join('')||'<div class="empty" style="grid-column:1/-1">Nenhum dado disponível.</div>'};$('#q').oninput=dr;dr()}
route();

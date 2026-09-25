// ⚠ ÚNICO lugar para ajustar as rotas do seu backend Flask (routes.py). Os caminhos abaixo são SUPOSIÇÕES.
const API_BASE = window.API_BASE || '';
const EP = {topicos:'/api/topicos',tags:'/api/tags',membros:'/api/membros',avl:'/api/avl',rotacoes:'/api/avl/rotacoes',logs:'/api/logs',teste:'/api/avl/teste',
  adminLogin:'/api/admin/login',adminRegistro:'/api/admin/registro'};
async function req(path,opt={}){const t=localStorage.getItem('admin_token');
  const r=await fetch(API_BASE+path,{headers:{'Content-Type':'application/json',...(t?{Authorization:'Bearer '+t}:{})},...opt});
  let d=null;try{d=await r.json()}catch{}
  if(!r.ok)throw new Error((d&&(d.erro||d.error||d.message))||'Erro HTTP '+r.status);return d}
const post=(p,b)=>req(p,{method:'POST',body:JSON.stringify(b||{})});
const lista=d=>Array.isArray(d)?d:(d&&(d.items||d.data||d.tags||d.topicos||d.membros||d.logs))||[];
const pick=(o,...k)=>{for(const x of k)if(o&&o[x]!=null)return o[x];return null};
function normNode(n){if(!n)return null;return{tag:pick(n,'display_name','tag','key'),key:pick(n,'key','tag'),h:pick(n,'height','altura'),uso:pick(n,'usage_count','uso','contador_uso'),
  desc:pick(n,'description','descricao'),l:normNode(pick(n,'left','esquerda','ponteiroEsquerda')),r:normNode(pick(n,'right','direita','ponteiroDireita'))}}
const treeRoot=d=>normNode(d&&(d.root||d.raiz||d.tree||d.arvore||(d.key||d.tag?d:null)));
const H=n=>n?(n.h??1+Math.max(H(n.l),H(n.r))):0; // usa a altura do backend; só recalcula se ela não vier
const FB=n=>n?H(n.l)-H(n.r):null;

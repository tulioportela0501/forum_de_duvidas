// Cliente da API. Funciona de 3 formas, sem configurar nada:
//  1) front aberto pelo Flask (http://127.0.0.1:5000)  -> usa o mesmo endereço;
//  2) front aberto pelo Go Live / Live Server (:5500)   -> acha o backend em http://127.0.0.1:5000;
//  3) backend em outro endereço -> defina antes: window.API_BASE = 'http://meu-servidor:porta'
const EP = {
  topicos: '/api/topicos', tags: '/api/tags', autocomplete: '/api/tags/autocomplete', membros: '/api/membros',
  avl: '/api/avl', rotacoes: '/api/avl/rotacoes', teste: '/api/avl/teste', logs: '/api/logs', dashboard: '/api/dashboard',
  adminLogin: '/api/admin/login', adminRegistro: '/api/admin/registro',
};

class ApiError extends Error {
  constructor(msg, status) { super(msg); this.status = status; }
}

const Auth = {
  get: () => localStorage.getItem('admin_token'),
  set: t => localStorage.setItem('admin_token', t),
  clear: () => localStorage.removeItem('admin_token'),
};

let _baseOk = null;
async function _testa(base) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), 2500);
  try {
    const r = await fetch(base + '/api/health', { cache: 'no-store', signal: ctrl.signal });
    return r.ok && (await r.json()).status === 'ok';
  } catch { return false; } finally { clearTimeout(t); }
}
// Descobre onde o backend está (o resultado só é guardado quando dá certo, então "Tentar novamente" funciona
// depois que você iniciar o servidor).
async function apiBase() {
  if (_baseOk !== null) return _baseOk;
  const cand = window.API_BASE ? [window.API_BASE.replace(/\/$/, '')]
    : [...(location.protocol.startsWith('http') ? [''] : []), 'http://127.0.0.1:5000', 'http://localhost:5000'];
  for (const c of cand) if (await _testa(c)) return (_baseOk = c);
  throw new ApiError('Backend não encontrado. Abra um terminal na pasta backend, rode "python app.py" e clique em "Tentar novamente".', 0);
}

async function req(path, opt = {}) {
  const base = await apiBase();
  const token = Auth.get();
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 15000);
  let r;
  try {
    r = await fetch(base + path, {
      ...opt, signal: ctrl.signal,
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: 'Bearer ' + token } : {}) },
    });
  } catch (e) {
    _baseOk = null;
    throw new ApiError(e.name === 'AbortError'
      ? 'O servidor demorou demais para responder.'
      : 'Conexão com o backend perdida. Verifique se "python app.py" continua rodando.', 0);
  } finally { clearTimeout(timer); }
  let d = null;
  try { d = await r.json(); } catch { /* resposta sem corpo */ }
  if (!r.ok) throw new ApiError(((d && (d.erro || d.error || d.message)) || 'Erro HTTP ' + r.status) + ` (${path})`, r.status);
  return d;
}
const post = (p, b) => req(p, { method: 'POST', body: JSON.stringify(b || {}) });
const del = p => req(p, { method: 'DELETE' });

// Nó da árvore como o backend envia: {key, display_name, description, usage_count, height, balance, left, right}
function normNode(n) {
  if (!n) return null;
  return { key: n.key, tag: n.display_name, desc: n.description, uso: n.usage_count, h: n.height, fb: n.balance,
           l: normNode(n.left), r: normNode(n.right) };
}
const treeRoot = d => normNode(d && d.root);

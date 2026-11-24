// Cliente da API. Sem configurar nada:
//  1) Vercel ou Flask local (http://127.0.0.1:5000): mesma origem (/api/...);
//  2) front aberto por outro servidor estático (ex.: Live Server :5500): acha o Flask em http://127.0.0.1:5000;
//  3) backend em outro endereço -> defina antes: window.API_BASE = 'https://meu-servidor'
const EP = {
  topicos: '/api/topicos', tags: '/api/tags', autocomplete: '/api/tags/autocomplete', membros: '/api/membros',
  avl: '/api/avl', rotacoes: '/api/avl/rotacoes', teste: '/api/avl/teste', logs: '/api/logs', dashboard: '/api/dashboard',
  estado: '/api/auth/estado', setup: '/api/auth/setup', login: '/api/auth/login', logout: '/api/auth/logout',
  eu: '/api/auth/eu', senha: '/api/auth/senha', usuarios: '/api/usuarios', admin: '/api/admin', perfil: '/api/perfil', professores: '/api/professores', grupos: '/api/grupos', notif: '/api/notificacoes',
};

class ApiError extends Error {
  constructor(msg, status) { super(msg); this.status = status; }
}

// A sessão vive num cookie HttpOnly gravado pelo servidor (o JavaScript não consegue lê-lo nem roubá-lo).
// Aqui fica só o token CSRF, EM MEMÓRIA, que o servidor devolve em /api/auth/eu e que vai no cabeçalho
// X-CSRF-Token das requisições que alteram dados. Nada de token em localStorage.
const Sessao = { csrf: null };
const SEM_REDIRECT = [EP.login, EP.setup, EP.estado, EP.eu];

let _baseOk = null;
async function _testa(base) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), 2500);
  try {
    const r = await fetch(base + '/api/health', { cache: 'no-store', signal: ctrl.signal });
    // Basta o servidor responder o /api/health com JSON: se o banco estiver com problema, o erro detalhado
    // (503) aparece na chamada seguinte em vez de uma mensagem enganosa de "backend não encontrado".
    return (await r.json()).status !== undefined;
  } catch { return false; } finally { clearTimeout(t); }
}
// Descobre onde o backend está (o resultado só é guardado quando dá certo, então "Tentar novamente" funciona
// depois que você iniciar o servidor).
async function apiBase() {
  if (_baseOk !== null) return _baseOk;
  const cand = window.API_BASE ? [window.API_BASE.replace(/\/$/, '')]
    // o cookie de sessão só acompanha chamadas para o MESMO site: tente primeiro o mesmo nome de host da página
    : [...(location.protocol.startsWith('http') ? [''] : []), `http://${location.hostname || '127.0.0.1'}:5000`,
       'http://127.0.0.1:5000', 'http://localhost:5000'];
  for (const c of cand) if (await _testa(c)) return (_baseOk = c);
  throw new ApiError('Backend não encontrado. Rode "python run_local.py" na pasta do projeto e clique em "Tentar novamente".', 0);
}

async function req(path, opt = {}) {
  const base = await apiBase();
  const metodo = (opt.method || 'GET').toUpperCase();
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 15000);
  let r;
  try {
    r = await fetch(base + path, {
      ...opt, signal: ctrl.signal, credentials: 'include',
      headers: { 'Content-Type': 'application/json',
                 ...(metodo !== 'GET' && Sessao.csrf ? { 'X-CSRF-Token': Sessao.csrf } : {}) },
    });
  } catch (e) {
    _baseOk = null;
    throw new ApiError(e.name === 'AbortError'
      ? 'O servidor demorou demais para responder.'
      : 'Conexão com o backend perdida. Verifique sua internet ou se "python run_local.py" continua rodando.', 0);
  } finally { clearTimeout(timer); }
  let d = null;
  try { d = await r.json(); } catch { /* resposta sem corpo */ }
  if (r.status === 401 && !SEM_REDIRECT.includes(path.split('?')[0]) && !location.pathname.endsWith('login.html')) {
    Sessao.csrf = null;
    location.replace('login.html');          // sessão expirada/revogada: volta para o login
  }
  if (!r.ok) throw new ApiError(((d && (d.erro || d.error || d.message)) || 'Erro HTTP ' + r.status) + ` (${path})`, r.status);
  return d;
}
const post = (p, b) => req(p, { method: 'POST', body: JSON.stringify(b || {}) });
const patch = (p, b) => req(p, { method: 'PATCH', body: JSON.stringify(b || {}) });
const del = p => req(p, { method: 'DELETE' });

// Nó da árvore como o backend envia: {key, display_name, description, usage_count, height, balance, left, right}
function normNode(n) {
  if (!n) return null;
  return { key: n.key, tag: n.display_name, desc: n.description, uso: n.usage_count, h: n.height, fb: n.balance,
           l: normNode(n.left), r: normNode(n.right) };
}
const treeRoot = d => normNode(d && d.root);

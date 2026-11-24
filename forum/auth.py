"""Autenticação, sessões e autorização (perfis: admin, professor, aluno).

Como funciona
* SESSÃO NO SERVIDOR: o login gera um identificador aleatório (256 bits) entregue em cookie HttpOnly +
  SameSite=Strict (+ Secure em HTTPS). O banco guarda apenas o HMAC dele (tabela `sessoes`): quem lê o banco
  não consegue se passar por ninguém. Expira por tempo absoluto (SESSION_MAX_AGE) e por inatividade
  (SESSION_IDLE) e pode ser revogada na hora (bloqueio, exclusão, troca de senha/perfil).
* NEGAR POR PADRÃO: um único `before_app_request` exige sessão válida em TODA rota /api/ que não esteja em
  PUBLICAS. Perfil, status e verificação do usuário são relidos do banco a cada requisição — nunca confiamos
  em dados guardados no cookie. O decorador `@perfis(...)` apenas declara quem pode chamar a rota; quem
  aplica a regra é o `before_app_request`.
* CSRF: toda requisição que altera dados exige o cabeçalho X-CSRF-Token (valor da sessão) e, quando o navegador
  manda `Origin`, ela precisa ser do mesmo site (ou de uma origem liberada em CORS_ORIGINS / localhost em dev).
* Senhas: hash scrypt com sal (Werkzeug). Login em tempo parecido para e-mail existente/inexistente, mesma
  mensagem de erro, limite de tentativas por IP e por e-mail (tabela `limites`, compartilhada entre instâncias).
* Primeiro acesso: enquanto não existir nenhum usuário, POST /api/auth/setup cria o administrador principal.
  Depois disso a rota responde 409 e só administradores cadastram usuários (ver usuarios.py).
"""
import hashlib
import hmac
import re
import secrets
import time
from urllib.parse import urlparse

from flask import Blueprint, current_app, g, jsonify, make_response, request
from werkzeug.security import check_password_hash, generate_password_hash

from forum.repo import agora as _agora

bp = Blueprint('auth', __name__, url_prefix='/api/auth')

PERFIS = ('admin', 'professor', 'aluno')
COOKIE = 'forum_sid'
COOKIE_PATH = '/api'
UNSAFE = {'POST', 'PUT', 'PATCH', 'DELETE'}
# Únicos endpoints acessíveis sem sessão
PUBLICAS = {'api.health', 'auth.estado', 'auth.setup', 'auth.login'}

ESCOPO_IP, ESCOPO_EMAIL = 'auth_falha', 'auth_falha_email'
JANELA, MAX_FALHAS_IP, MAX_FALHAS_EMAIL = 900, 8, 20

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
_LOCAL = re.compile(r'^https?://(localhost|127\.0\.0\.1)(:\d+)?$')
_dummy_hash = None


# ---------------------------------------------------------------- utilidades
def ip_cliente():
    """Na Vercel o IP real vem em cabeçalhos do edge; fora dela vale o endereço da conexão."""
    if current_app.config.get('IS_VERCEL'):
        h = request.headers
        return (h.get('x-vercel-forwarded-for') or h.get('x-real-ip')
                or (h.get('x-forwarded-for') or '').split(',')[0].strip() or request.remote_addr or '?')
    return request.remote_addr or '?'


def _repo():
    return current_app.extensions['repo']


def _sid(token):
    return hmac.new(current_app.config['SECRET_KEY'].encode(), token.encode(), hashlib.sha256).hexdigest()


def _https():
    forcado = current_app.config.get('COOKIE_SECURE')
    if forcado is not None:
        return forcado
    return (request.is_secure or current_app.config.get('IS_VERCEL')
            or request.headers.get('x-forwarded-proto', '').split(',')[0].strip() == 'https')


def origem_permitida(origem):
    """Origens que podem fazer chamadas à API a partir de outro endereço (CORS e checagem anti-CSRF)."""
    cfg = current_app.config
    return origem in cfg['CORS_ORIGINS'] or (not cfg.get('IS_VERCEL') and bool(_LOCAL.match(origem)))


def usuario_publico(u):
    return {'id': u['id'], 'nome': u['nome'], 'email': u['email'], 'perfil': u['perfil'],
            'status': u['status'], 'verificado': bool(u['verificado']), 'principal': bool(u['principal'])}


# ---------------------------------------------------------------- validação de dados
def normalizar_email(v):
    return str(v or '').strip().lower()


def validar_dados_conta(nome=None, email=None):
    """Devolve mensagem de erro ou None."""
    if nome is not None and not (2 <= len(nome) <= 100):
        return 'Nome deve ter de 2 a 100 caracteres.'
    if nome is not None and any(ord(c) < 32 for c in nome):
        return 'Nome contém caracteres inválidos.'
    if email is not None and (len(email) > 254 or not _EMAIL_RE.match(email)):
        return 'E-mail inválido.'
    return None


def validar_senha(senha, nome='', email=''):
    if not isinstance(senha, str) or len(senha) < 10:
        return 'A senha deve ter no mínimo 10 caracteres.'
    if len(senha) > 128:
        return 'A senha pode ter no máximo 128 caracteres.'
    if not (re.search(r'[A-Za-z]', senha) and re.search(r'\d', senha)):
        return 'A senha deve conter letras e números.'
    baixa = senha.lower()
    if baixa == (email or '').lower() or baixa == (nome or '').lower().strip():
        return 'A senha não pode ser igual ao nome ou ao e-mail.'
    return None


def hash_senha(senha):
    return generate_password_hash(senha)


def _senha_confere(usuario, senha):
    """Verifica a senha gastando tempo parecido quando o usuário não existe (evita enumerar e-mails)."""
    global _dummy_hash
    if usuario:
        return check_password_hash(usuario['senha'], senha)
    if _dummy_hash is None:
        _dummy_hash = generate_password_hash(secrets.token_hex(8))
    check_password_hash(_dummy_hash, senha)
    return False


# ---------------------------------------------------------------- sessão / cookie
def _abrir_sessao(uid, resp_builder):
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(24)
    cfg = current_app.config
    _repo().criar_sessao(_sid(token), uid, csrf, time.time() + cfg['SESSION_MAX_AGE'], ip_cliente(),
                         request.headers.get('User-Agent'))
    resp = resp_builder(csrf)
    resp.set_cookie(COOKIE, token, max_age=cfg['SESSION_MAX_AGE'], httponly=True, samesite='Strict',
                    secure=_https(), path=COOKIE_PATH)
    return resp


def _limpar_cookie(resp):
    resp.delete_cookie(COOKIE, path=COOKIE_PATH, httponly=True, samesite='Strict', secure=_https())
    return resp


def _negado(msg, codigo, limpar=False):
    resp = make_response(jsonify(erro=msg), codigo)
    return _limpar_cookie(resp) if limpar else resp


def perfis(*permitidos):
    """Declara quais perfis podem chamar a rota (aplicado centralmente em `_guarda`)."""
    assert permitidos and set(permitidos) <= set(PERFIS)

    def marcar(f):
        f.perfis_permitidos = frozenset(permitidos)
        return f
    return marcar


@bp.before_app_request
def _guarda():
    g.usuario = g.sessao_id = g.csrf = None
    if not request.path.startswith('/api/') or request.method == 'OPTIONS':
        return None
    if request.method in UNSAFE:
        origem = request.headers.get('Origin')
        if origem and urlparse(origem).netloc != request.host and not origem_permitida(origem):
            return _negado('Origem não permitida.', 403)
    ep = request.endpoint
    if ep is None or ep in PUBLICAS:               # rota inexistente -> 404/405 JSON; pública -> segue
        return None

    token = request.cookies.get(COOKIE, '')
    if not token:
        return _negado('Não autenticado. Entre para continuar.', 401)
    sid = _sid(token)
    repo, cfg, agora = _repo(), current_app.config, time.time()
    s = repo.obter_sessao(sid)
    if (not s or s['expira_em'] < agora or agora - s['ultimo_uso'] > cfg['SESSION_IDLE']):
        if s:
            repo.encerrar_sessao(sid)
        return _negado('Sessão expirada ou inválida. Entre novamente.', 401, limpar=True)
    if s['status'] != 'ativo':
        repo.encerrar_sessao(sid)
        return _negado('Conta bloqueada. Procure um administrador.', 403, limpar=True)
    if s['perfil'] == 'professor' and not s['verificado']:
        repo.encerrar_sessao(sid)
        return _negado('Conta de professor aguardando verificação administrativa.', 403, limpar=True)
    if request.method in UNSAFE and not hmac.compare_digest(request.headers.get('X-CSRF-Token', ''), s['csrf']):
        return _negado('Token CSRF ausente ou inválido.', 403)

    permitidos = getattr(current_app.view_functions[ep], 'perfis_permitidos', None)
    if permitidos and s['perfil'] not in permitidos:
        return _negado('Você não tem permissão para esta ação.', 403)

    if agora - s['ultimo_uso'] > min(300, cfg['SESSION_IDLE'] / 4):
        repo.tocar_sessao(sid)
    g.usuario, g.sessao_id, g.csrf = s, sid, s['csrf']
    return None


# ---------------------------------------------------------------- rotas
def _falha(email, msg, codigo=400):
    r = _repo()
    r.registrar_limite(ESCOPO_IP, ip_cliente())
    if email:
        r.registrar_limite(ESCOPO_EMAIL, email[:254])
    return jsonify(erro=msg), codigo


def _bloqueado_por_tentativas(email=''):
    r = _repo()
    return (r.limite_atingido(ESCOPO_IP, ip_cliente(), JANELA, MAX_FALHAS_IP)
            or bool(email and r.limite_atingido(ESCOPO_EMAIL, email[:254], JANELA, MAX_FALHAS_EMAIL)))


@bp.get('/estado')
def estado():
    """Diz ao front se o primeiro acesso (criação do administrador principal) ainda está pendente."""
    return jsonify(configurado=_repo().contar_usuarios() > 0)


@bp.post('/setup')
def setup():
    if _bloqueado_por_tentativas():
        return jsonify(erro='Muitas tentativas. Aguarde 15 minutos.'), 429
    repo = _repo()
    if repo.contar_usuarios() > 0:
        return jsonify(erro='O sistema já foi configurado. Peça a um administrador para criar sua conta.'), 409
    d = request.get_json(silent=True) or {}
    nome, email = ' '.join(str(d.get('nome') or '').split()), normalizar_email(d.get('email'))
    senha = d.get('senha')
    erro = validar_dados_conta(nome, email) or validar_senha(senha, nome, email)
    if erro:
        return _falha('', erro)
    uid = repo.criar_principal(nome, email, hash_senha(senha))
    if uid is None:                                # alguém criou entre a checagem e o INSERT
        return jsonify(erro='O sistema já foi configurado. Peça a um administrador para criar sua conta.'), 409
    repo.registrar_log(email, 'setup', 'administrador principal criado')
    repo.atualizar_usuario(uid, {'ultimo_login': _agora()})
    u = usuario_publico(repo.obter_usuario(uid))
    return _abrir_sessao(uid, lambda csrf: jsonify(usuario=u, csrf=csrf)), 201


@bp.post('/login')
def login():
    d = request.get_json(silent=True) or {}
    email, senha = normalizar_email(d.get('email'))[:254], d.get('senha')
    if _bloqueado_por_tentativas(email):
        return jsonify(erro='Muitas tentativas. Aguarde 15 minutos.'), 429
    repo = _repo()
    senha = senha if isinstance(senha, str) and len(senha) <= 128 else ''
    u = repo.obter_usuario_por_email(email)
    if not _senha_confere(u, senha):
        repo.registrar_log(email, 'login', 'falhou')
        return _falha(email, 'E-mail ou senha incorretos.', 401)
    # a senha está certa: agora é seguro explicar por que a conta não pode entrar
    if u['status'] != 'ativo':
        repo.registrar_log(email, 'login', 'recusado (conta bloqueada)')
        return jsonify(erro='Conta bloqueada. Procure um administrador.'), 403
    if u['perfil'] == 'professor' and not u['verificado']:
        repo.registrar_log(email, 'login', 'recusado (professor não verificado)')
        return jsonify(erro='Conta de professor aguardando verificação administrativa.'), 403
    repo.atualizar_usuario(u['id'], {'ultimo_login': _agora()})
    repo.registrar_log(email, 'login', 'ok')
    pub = usuario_publico(u)
    return _abrir_sessao(u['id'], lambda csrf: jsonify(usuario=pub, csrf=csrf))


@bp.post('/logout')
def logout():
    _repo().encerrar_sessao(g.sessao_id)
    return _limpar_cookie(jsonify(ok=True))


@bp.get('/eu')
def eu():
    p = _repo().perfil_proprio(g.usuario['id'])
    return jsonify(usuario={**usuario_publico(g.usuario), 'tem_foto': bool(p and p['foto'])}, csrf=g.csrf)


@bp.post('/senha')
def trocar_senha():
    d = request.get_json(silent=True) or {}
    repo, eu_ = _repo(), g.usuario
    if _bloqueado_por_tentativas(eu_['email']):
        return jsonify(erro='Muitas tentativas. Aguarde 15 minutos.'), 429
    completo = repo.obter_usuario_por_email(eu_['email'])
    atual = d.get('senha_atual')
    if not isinstance(atual, str) or not check_password_hash(completo['senha'], atual):
        return _falha(eu_['email'], 'Senha atual incorreta.', 403)
    nova = d.get('nova_senha')
    erro = validar_senha(nova, eu_['nome'], eu_['email'])
    if erro:
        return jsonify(erro=erro), 400
    repo.atualizar_usuario(eu_['id'], {'senha': hash_senha(nova)})
    repo.encerrar_sessoes_do_usuario(eu_['id'], exceto=g.sessao_id)     # derruba os outros dispositivos
    repo.registrar_log(eu_['email'], 'trocar senha', 'ok')
    return jsonify(ok=True)

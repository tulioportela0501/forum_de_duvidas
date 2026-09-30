"""Cadastro/login de administradores.

Quem souber o CODIGO_ADMIN pode criar a própria conta (nome, e-mail e senha à escolha).
O código NÃO fica no código-fonte: vem da variável de ambiente/.env ou é gerado na primeira
execução (backend/data/codigo_admin.txt) e exibido no console ao iniciar o servidor.

Proteja rotas administrativas com @admin_required.
"""
import hmac
import re
import time
from functools import wraps

from flask import Blueprint, current_app, g, jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

bp = Blueprint('admin_auth', __name__, url_prefix='/api/admin')

_falhas = {}
_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def _serializador():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt='admin')


def _ip():
    return request.remote_addr or 'desconhecido'


def _bloqueado():
    agora = time.time()
    _falhas[_ip()] = [t for t in _falhas.get(_ip(), []) if agora - t < 900]
    return len(_falhas[_ip()]) >= 8


def _falha(msg, codigo=400):
    _falhas.setdefault(_ip(), []).append(time.time())
    return jsonify(erro=msg), codigo


def _token(admin):
    return _serializador().dumps({'id': admin['id'], 'email': admin['email']})


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization', '').removeprefix('Bearer ').strip()
        try:
            dados = _serializador().loads(token, max_age=current_app.config['TOKEN_MAX_AGE'])
        except (BadSignature, SignatureExpired):
            return jsonify(erro='Não autorizado (token inválido ou expirado). Entre novamente.'), 401
        g.admin_email = dados.get('email')
        return f(*args, **kwargs)
    return wrapper


@bp.post('/registro')
def registro():
    if _bloqueado():
        return jsonify(erro='Muitas tentativas. Aguarde 15 minutos.'), 429
    d = request.get_json(silent=True) or {}
    email, nome, senha, codigo = (str(d.get(k) or '').strip() for k in ('email', 'nome', 'senha', 'codigo'))
    if not nome or not _EMAIL_RE.match(email) or len(senha) < 10:
        return _falha('Dados inválidos (nome, e-mail válido e senha de no mínimo 10 caracteres).')
    if not hmac.compare_digest(codigo.encode(), current_app.config['CODIGO_ADMIN'].encode()):
        current_app.extensions['repo'].registrar_log(email, 'admin_registro', 'código incorreto')
        return _falha('Código de acesso administrativo incorreto.', 403)
    repo = current_app.extensions['repo']
    admin_id = repo.criar_admin(email.lower(), nome, generate_password_hash(senha))
    if admin_id is None:
        return _falha('E-mail já cadastrado.', 409)
    repo.registrar_log(email, 'admin_registro', 'conta criada')
    return jsonify(token=_token({'id': admin_id, 'email': email.lower()}))


@bp.post('/login')
def login():
    if _bloqueado():
        return jsonify(erro='Muitas tentativas. Aguarde 15 minutos.'), 429
    d = request.get_json(silent=True) or {}
    email = str(d.get('email') or '').strip().lower()
    repo = current_app.extensions['repo']
    admin = repo.obter_admin(email)
    if not admin or not check_password_hash(admin['senha'], str(d.get('senha') or '')):
        repo.registrar_log(email, 'admin_login', 'falhou')
        return _falha('E-mail ou senha incorretos.', 401)
    repo.registrar_log(email, 'admin_login', 'ok')
    return jsonify(token=_token(admin))

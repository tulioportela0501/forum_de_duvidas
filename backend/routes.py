"""Rotas da API. Públicas: leitura de tags/tópicos/membros, autocomplete e criação de dúvidas.
Protegidas (@admin_required): árvore AVL, rotações, logs, dashboard, teste de carga e gestão de tags."""
import time

from flask import Blueprint, current_app, g, jsonify, request

from admin_auth import admin_required
from service import Conflito, ErroValidacao

bp = Blueprint('api', __name__, url_prefix='/api')
_posts = {}


def _svc():
    return current_app.extensions['servico']


def _repo():
    return current_app.extensions['repo']


def _admin():
    return getattr(g, 'admin_email', None)


def _limite_posts(max_por_min=20):
    ip, agora = request.remote_addr or '?', time.time()
    _posts[ip] = [t for t in _posts.get(ip, []) if agora - t < 60]
    if len(_posts[ip]) >= max_por_min:
        return True
    _posts[ip].append(agora)
    return False


@bp.get('/health')
def health():
    return jsonify(status='ok')


# ---------------------------------------------------------------- tags
@bp.get('/tags')
def listar_tags():
    return jsonify(_svc().listar_tags())


@bp.get('/tags/autocomplete')
def autocompletar():
    q = request.args.get('q', '')
    try:
        limite = max(1, min(int(request.args.get('limit', 8)), 20))
    except ValueError:
        limite = 8
    return jsonify(_svc().autocompletar(q, limite))


@bp.post('/tags')
@admin_required
def criar_tag():
    d = request.get_json(silent=True) or {}
    try:
        tag, rot = _svc().criar_tag(d.get('nome') or d.get('tag'), d.get('descricao', ''))
    except ErroValidacao as e:
        return jsonify(erro=str(e)), 400
    except Conflito as e:
        return jsonify(erro=str(e)), 409
    _repo().registrar_log(_admin(), f"criar tag '{tag['display_name']}'", f'ok ({len(rot)} rotação(ões))')
    return jsonify(tag=tag, rotacoes=rot), 201


@bp.delete('/tags/<path:nome>')
@admin_required
def remover_tag(nome):
    if not _svc().remover_tag(nome):
        return jsonify(erro='Tag não encontrada.'), 404
    _repo().registrar_log(_admin(), f"remover tag '{nome}'", 'ok')
    return jsonify(ok=True)


# ---------------------------------------------------------------- tópicos
@bp.get('/topicos')
def listar_topicos():
    return jsonify(_repo().listar_topicos())


@bp.post('/topicos')
def criar_topico():
    if _limite_posts():
        return jsonify(erro='Muitas dúvidas em pouco tempo. Aguarde um minuto.'), 429
    d = request.get_json(silent=True) or {}
    try:
        t = _svc().criar_topico(d.get('titulo'), d.get('descricao'), d.get('autor'), d.get('tags'))
    except ErroValidacao as e:
        return jsonify(erro=str(e)), 400
    _repo().registrar_log(t['autor'] or 'anônimo', f"nova dúvida '{t['titulo']}'", f"ok ({len(t['tags'])} tag(s))")
    return jsonify(t), 201


# ---------------------------------------------------------------- membros
@bp.get('/membros')
def listar_membros():
    return jsonify(_repo().listar_membros())


# ---------------------------------------------------------------- administração
@bp.get('/avl')
@admin_required
def avl():
    return jsonify(_svc().snapshot())


@bp.get('/avl/rotacoes')
@admin_required
def rotacoes():
    return jsonify(_repo().resumo_rotacoes())


@bp.post('/avl/teste')
@admin_required
def teste():
    r = _svc().teste_carga('aula', 20)
    _repo().registrar_log(_admin(), 'teste de carga aula1→aula20',
                          f"ok ({r['resumo']['rotacoes']} rotações, altura {r['resumo']['altura']})")
    return jsonify(r)


@bp.get('/logs')
@admin_required
def logs():
    return jsonify(_repo().listar_logs())


@bp.get('/dashboard')
@admin_required
def dashboard():
    return jsonify(_svc().dashboard())

"""Perfis: edição do próprio perfil e diretório de professores verificados.
Perfil/verificação/status/e-mail NUNCA são aceitos aqui (só admin, em usuarios.py)."""
import base64
import re

from flask import Blueprint, Response, current_app, g, jsonify, request

from forum.auth import perfis, validar_dados_conta

bp = Blueprint('perfis', __name__, url_prefix='/api')
PROIBIDOS = {'perfil', 'verificado', 'status', 'principal', 'email', 'senha', 'id', 'verificado_em', 'verificado_por'}
LIMITES = {'informacoes': 500, 'biografia': 1000}
LIMITES_PROF = {'formacao': 180, 'especialidade': 180, 'descricao_profissional': 2000}
FOTO = re.compile(r'^data:image/(jpeg|png|webp);base64,[A-Za-z0-9+/]+=*$')
FOTO_MAX = 200_000


def _repo():
    return current_app.extensions['repo']


def _pub(u):
    return {**u, 'verificado': bool(u['verificado'])}


@bp.get('/perfil')
def meu_perfil():
    return jsonify(_pub(_repo().perfil_proprio(g.usuario['id'])))


@bp.get('/perfis/<int:uid>')
def preview(uid):
    """Resumo público para o cartão que aparece ao passar o mouse sobre o nome (sem e-mail nem dados privados)."""
    db = _repo().db
    r = db.execute('SELECT id, nome, perfil, verificado, foto, biografia, formacao, especialidade FROM usuarios WHERE id=?', (uid,)).rows
    if not r:
        return jsonify(erro='Usuário não encontrado.'), 404
    u = r[0]
    n = lambda sql: db.execute(sql, (uid,)).rows[0]['n']
    prof = u['perfil'] == 'professor'
    return jsonify(id=u['id'], nome=u['nome'], perfil=u['perfil'], verificado=bool(u['verificado'] and prof),
                   tem_foto=bool(u['foto']), biografia=(u['biografia'] or '')[:300],
                   formacao=(u['formacao'] or '') if prof else '', especialidade=(u['especialidade'] or '') if prof else '',
                   duvidas=n("SELECT COUNT(*) n FROM topicos WHERE autor_id=? AND oculto=0 AND status_moderacao='aprovado'"),
                   respostas=n("SELECT COUNT(*) n FROM respostas WHERE autor_id=? AND status='publicada'"))


@bp.get('/perfis/<int:uid>/foto')
def foto_usuario(uid):
    """Entrega a foto como imagem (cache com revalidação), para não repetir o base64 em cada dúvida/resposta."""
    r = _repo().db.execute('SELECT foto FROM usuarios WHERE id=?', (uid,)).rows
    f = r[0]['foto'] if r else ''
    if not f or not FOTO.match(f):
        return jsonify(erro='Sem foto.'), 404
    cab, dados = f.split(',', 1)
    resp = Response(base64.b64decode(dados), mimetype=cab[5:cab.index(';')])
    resp.headers['Cache-Control'] = 'private, no-cache'
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.add_etag()
    return resp.make_conditional(request)


@bp.patch('/perfil')
def editar_perfil():
    d = request.get_json(silent=True) or {}
    if PROIBIDOS & set(d):
        return jsonify(erro='Tipo de conta, verificação, status e e-mail só podem ser alterados por um administrador.'), 403
    campos = {}
    if 'nome' in d:
        nome = ' '.join(str(d['nome'] or '').split())
        erro = validar_dados_conta(nome=nome)
        if erro:
            return jsonify(erro=erro), 400
        campos['nome'] = nome
    for k, lim in LIMITES.items():
        if k in d:
            campos[k] = str(d[k] or '').strip()[:lim]
    if 'foto' in d:
        foto = str(d['foto'] or '')
        if foto and (len(foto) > FOTO_MAX or not FOTO.match(foto)):
            return jsonify(erro='Foto inválida (JPEG, PNG ou WebP, até ~150 KB).'), 400
        campos['foto'] = foto
    if g.usuario['perfil'] == 'professor':
        for k, lim in LIMITES_PROF.items():
            if k in d:
                campos[k] = str(d[k] or '').strip()[:lim]
    elif set(d) & set(LIMITES_PROF):
        return jsonify(erro='Somente professores editam dados profissionais.'), 403
    if not campos:
        return jsonify(erro='Nenhuma alteração informada.'), 400
    _repo().atualizar_usuario(g.usuario['id'], campos)
    _repo().registrar_log(g.usuario['email'], 'editar próprio perfil', 'ok (' + ', '.join(sorted(campos)) + ')')
    return jsonify(_pub(_repo().perfil_proprio(g.usuario['id'])))


@bp.get('/professores')
def diretorio():
    return jsonify([_pub(p) for p in _repo().listar_professores()])


@bp.get('/professores/<int:uid>')
def professor(uid):
    p = _repo().obter_professor(uid)
    return jsonify(_pub(p)) if p else (jsonify(erro='Professor não encontrado.'), 404)


# ---------------------------------------------------------------- notificações (somente aluno e professor)
@bp.get('/notificacoes')
@perfis('aluno', 'professor')
def notificacoes():
    db, uid = _repo().db, g.usuario['id']
    itens = db.execute(
        'SELECT n.id, n.topico_id, n.autor_nome, n.lida, n.criado_em, t.titulo, substr(r.conteudo,1,140) AS previa '
        'FROM notificacoes n JOIN topicos t ON t.id=n.topico_id JOIN respostas r ON r.id=n.resposta_id '
        "WHERE n.usuario_id=? AND r.status='publicada' AND t.oculto=0 ORDER BY n.id DESC LIMIT 50", (uid,)).rows
    return jsonify(itens=[{**i, 'lida': bool(i['lida'])} for i in itens], nao_lidas=_nao_lidas(uid))


def _nao_lidas(uid):
    return _repo().db.execute('SELECT COUNT(*) AS n FROM notificacoes WHERE usuario_id=? AND lida=0', (uid,)).rows[0]['n']


@bp.get('/notificacoes/contagem')
@perfis('aluno', 'professor')
def contagem_notificacoes():
    return jsonify(nao_lidas=_nao_lidas(g.usuario['id']))


@bp.post('/notificacoes/lidas')
@perfis('aluno', 'professor')
def marcar_todas():
    _repo().db.execute('UPDATE notificacoes SET lida=1 WHERE usuario_id=?', (g.usuario['id'],))
    return jsonify(nao_lidas=0)


@bp.post('/notificacoes/<int:nid>/lida')
@perfis('aluno', 'professor')
def marcar_uma(nid):
    _repo().db.execute('UPDATE notificacoes SET lida=1 WHERE id=? AND usuario_id=?', (nid, g.usuario['id']))
    return jsonify(nao_lidas=_nao_lidas(g.usuario['id']))

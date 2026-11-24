"""Rotas do fórum. Só /api/health é pública; todas as demais exigem sessão (ver auth.py) e algumas restringem
o perfil com @perfis:

  qualquer perfil logado : ler tags/tópicos/membros, autocomplete, criar dúvida
  admin + professor      : criar tag, árvore AVL, rotações, dashboard, teste de carga
  admin                  : remover tag, logs (e gestão de usuários em usuarios.py)
"""
from flask import Blueprint, current_app, g, jsonify, request

from forum.auth import perfis
from forum.db import DbError
from forum.service import Conflito, ErroValidacao

bp = Blueprint('api', __name__, url_prefix='/api')


def _svc():
    return current_app.extensions['servico']


def _repo():
    return current_app.extensions['repo']


def _quem():
    return g.usuario['email']


@bp.get('/health')
def health():
    """Testa a conexão com o banco (SQLite local ou Turso) e a existência das tabelas."""
    try:
        info = _repo().saude()
    except DbError as e:
        return jsonify(status='erro', db={'conectado': False, 'erro': str(e)[:200]}), 503
    info['conectado'] = True
    ok = info['esquema_ok']
    return jsonify(status='ok' if ok else 'esquema_pendente', db=info), 200 if ok else 503


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
@perfis('admin', 'professor')
def criar_tag():
    d = request.get_json(silent=True) or {}
    try:
        tag, rot = _svc().criar_tag(d.get('nome') or d.get('tag'), d.get('descricao', ''))
    except ErroValidacao as e:
        return jsonify(erro=str(e)), 400
    except Conflito as e:
        return jsonify(erro=str(e)), 409
    _repo().registrar_log(_quem(), f"criar tag '{tag['display_name']}'", f'ok ({len(rot)} rotação(ões))')
    return jsonify(tag=tag, rotacoes=rot), 201


@bp.patch('/tags/<path:nome>')
@perfis('admin')
def editar_tag(nome):
    d=request.get_json(silent=True) or {}; novo=str(d.get('nome',nome)).strip(); desc=str(d.get('descricao','')).strip()[:200]
    try: resultado=_svc().editar_tag(nome,novo,desc)
    except ErroValidacao as e:return jsonify(erro=str(e)),400
    except Conflito as e:return jsonify(erro=str(e)),409
    if not resultado:return jsonify(erro='Tag não encontrada.'),404
    tag,rot=resultado
    _repo().registrar_log(_quem(),f"editar tag '{nome}' para '{novo}'",f'ok ({len(rot)} rotação(ões))')
    return jsonify(tag=tag,rotacoes=rot)

@bp.delete('/tags/<path:nome>')
@perfis('admin')
def remover_tag(nome):
    tag=_svc().buscar_tag(nome)
    if tag and tag['usage_count'] > 0:
        return jsonify(erro='Esta tag já está sendo utilizada e não pode ser removida.'), 409
    if not _svc().remover_tag(nome):
        return jsonify(erro='Tag não encontrada.'), 404
    _repo().registrar_log(_quem(), f"remover tag '{nome}'", 'ok')
    return jsonify(ok=True)


# ---------------------------------------------------------------- curtidas
def _curtidas(tipo, ids):
    """Total de curtidas e se o usuário logado curtiu, para uma lista de tópicos ou respostas."""
    out = {i: {'curtidas': 0, 'curtiu': False} for i in ids}
    if ids:
        sql = ('SELECT alvo_id, COUNT(*) AS n, SUM(CASE WHEN usuario_id=? THEN 1 ELSE 0 END) AS eu FROM curtidas '
               f"WHERE alvo_tipo=? AND alvo_id IN ({','.join('?' * len(ids))}) GROUP BY alvo_id")
        for r in _repo().db.execute(sql, (g.usuario['id'], tipo, *ids)).rows:
            out[r['alvo_id']] = {'curtidas': r['n'], 'curtiu': bool(r['eu'])}
    return out


def _alternar_curtida(tipo, alvo_id):
    db, uid = _repo().db, g.usuario['id']
    if db.execute('SELECT 1 FROM curtidas WHERE usuario_id=? AND alvo_tipo=? AND alvo_id=?', (uid, tipo, alvo_id)).rows:
        db.execute('DELETE FROM curtidas WHERE usuario_id=? AND alvo_tipo=? AND alvo_id=?', (uid, tipo, alvo_id))
    else:
        db.execute('INSERT OR IGNORE INTO curtidas(usuario_id,alvo_tipo,alvo_id,criado_em) VALUES(?,?,?,?)',
                   (uid, tipo, alvo_id, __import__('forum.repo', fromlist=['agora']).agora()))
    return jsonify(_curtidas(tipo, [alvo_id])[alvo_id])


def _com_foto(uids):
    uids = sorted({u for u in uids if u})
    if not uids:
        return set()
    sql = f"SELECT id FROM usuarios WHERE foto IS NOT NULL AND foto<>'' AND id IN ({','.join('?' * len(uids))})"
    return {r['id'] for r in _repo().db.execute(sql, tuple(uids)).rows}


def _reposts(ids):
    out = {i: {'reposts': 0, 'repostou': False} for i in ids}
    if ids:
        sql = ('SELECT topico_id, COUNT(*) AS n, SUM(CASE WHEN usuario_id=? THEN 1 ELSE 0 END) AS eu FROM reposts '
               f"WHERE topico_id IN ({','.join('?' * len(ids))}) GROUP BY topico_id")
        for r in _repo().db.execute(sql, (g.usuario['id'], *ids)).rows:
            out[r['topico_id']] = {'reposts': r['n'], 'repostou': bool(r['eu'])}
    return out


@bp.post('/topicos/<int:tid>/repostar')
def repostar_topico(tid):
    db, uid = _repo().db, g.usuario['id']
    if not db.execute("SELECT id FROM topicos WHERE id=? AND oculto=0 AND status_moderacao='aprovado'", (tid,)).rows:
        return jsonify(erro='Tópico não encontrado.'), 404
    if db.execute('SELECT 1 FROM reposts WHERE usuario_id=? AND topico_id=?', (uid, tid)).rows:
        db.execute('DELETE FROM reposts WHERE usuario_id=? AND topico_id=?', (uid, tid))
    else:
        db.execute('INSERT OR IGNORE INTO reposts(usuario_id,topico_id,criado_em) VALUES(?,?,?)',
                   (uid, tid, __import__('forum.repo', fromlist=['agora']).agora()))
    return jsonify(_reposts([tid])[tid])


@bp.post('/topicos/<int:tid>/curtir')
def curtir_topico(tid):
    if not _repo().db.execute("SELECT id FROM topicos WHERE id=? AND oculto=0 AND status_moderacao='aprovado'", (tid,)).rows:
        return jsonify(erro='Tópico não encontrado.'), 404
    return _alternar_curtida('topico', tid)


@bp.post('/respostas/<int:rid>/curtir')
def curtir_resposta(rid):
    if not _repo().db.execute("SELECT id FROM respostas WHERE id=? AND status='publicada'", (rid,)).rows:
        return jsonify(erro='Resposta não encontrada.'), 404
    return _alternar_curtida('resposta', rid)


# ---------------------------------------------------------------- tópicos
@bp.get('/topicos')
def listar_topicos():
    lista = _repo().listar_topicos()
    ids = [t['id'] for t in lista]
    c, rp = _curtidas('topico', ids), _reposts(ids)
    com_foto = _com_foto([t.get('autor_id') for t in lista])
    return jsonify([{**t, **c[t['id']], **rp[t['id']], 'autor_foto': t.get('autor_id') in com_foto} for t in lista])


@bp.post('/topicos')
def criar_topico():
    chave = f"u{g.usuario['id']}"
    if _repo().limite_atingido('post', chave, 60, 20):
        return jsonify(erro='Muitas dúvidas em pouco tempo. Aguarde um minuto.'), 429
    _repo().registrar_limite('post', chave)
    d = request.get_json(silent=True) or {}
    try:
        # o autor vem SEMPRE da sessão (o campo "autor" enviado pelo cliente é ignorado)
        t = _svc().criar_topico(d.get('titulo'), d.get('descricao'), g.usuario['nome'], d.get('tags'))
    except ErroValidacao as e:
        return jsonify(erro=str(e)), 400
    _repo().db.execute('UPDATE topicos SET autor_id=? WHERE id=?',(g.usuario['id'],t['id']))
    palavras=_repo().detectar_palavras(t['titulo']+' '+t['descricao'])
    if palavras:
        _repo().db.batch([("UPDATE topicos SET status_moderacao='pendente',oculto=1 WHERE id=?",(t['id'],)),
                          ("INSERT INTO moderacao(tipo,item_id,motivo,criado_em) VALUES('topico',?,?,?)",(t['id'],'Palavras restritas: '+', '.join(palavras),__import__('forum.repo',fromlist=['agora']).agora()))])
        t['oculto']=1; t['status_moderacao']='pendente'
    _repo().registrar_log(_quem(), f"nova dúvida '{t['titulo']}'", 'encaminhada à moderação' if palavras else f"ok ({len(t['tags'])} tag(s))")
    return jsonify(t), 201


# ---------------------------------------------------------------- membros
@bp.get('/membros')
def listar_membros():
    return jsonify(_repo().listar_membros())


# ---------------------------------------------------------------- administração
@bp.get('/avl')
@perfis('admin', 'professor')
def avl():
    return jsonify(_svc().snapshot())


@bp.get('/avl/rotacoes')
@perfis('admin', 'professor')
def rotacoes():
    return jsonify(_repo().resumo_rotacoes())


@bp.post('/avl/teste')
@perfis('admin', 'professor')
def teste():
    r = _svc().teste_carga('aula', 20)
    _repo().registrar_log(_quem(), 'teste de carga aula1→aula20',
                          f"ok ({r['resumo']['rotacoes']} rotações, altura {r['resumo']['altura']})")
    return jsonify(r)


@bp.get('/logs')
@perfis('admin')
def logs():
    return jsonify(_repo().listar_logs())


@bp.get('/dashboard')
@perfis('admin')
def dashboard():
    return jsonify(_svc().dashboard())


# Respostas: criação por usuário autenticado e consulta pública apenas do conteúdo aprovado.
@bp.get('/topicos/<int:tid>/respostas')
def listar_respostas(tid):
    rs = _repo().db.execute("SELECT r.id,r.topico_id,r.autor,r.conteudo,r.criado_em,r.autor_id,r.parent_id,u.perfil AS autor_perfil,COALESCE(u.verificado,0) AS autor_verificado FROM respostas r LEFT JOIN usuarios u ON u.id=r.autor_id WHERE r.topico_id=? AND r.status='publicada' ORDER BY r.id",(tid,)).rows
    c = _curtidas('resposta', [r['id'] for r in rs])
    com_foto = _com_foto([r['autor_id'] for r in rs])
    return jsonify([{**r,**c[r['id']],'autor_foto':r['autor_id'] in com_foto,'autor_verificado':bool(r['autor_verificado'] and r['autor_perfil']=='professor')} for r in rs])

@bp.post('/topicos/<int:tid>/respostas')
def criar_resposta(tid):
    if not _repo().db.execute('SELECT id FROM topicos WHERE id=? AND oculto=0 AND status_moderacao=\'aprovado\'',(tid,)).rows:
        return jsonify(erro='Tópico não encontrado.'),404
    d=request.get_json(silent=True) or {}; conteudo=str(d.get('conteudo','')).strip()
    if not conteudo or len(conteudo)>5000:return jsonify(erro='A resposta deve ter entre 1 e 5000 caracteres.'),400
    pai=d.get('pai_id')
    if pai is not None and (not isinstance(pai,int) or isinstance(pai,bool) or not _repo().db.execute("SELECT id FROM respostas WHERE id=? AND topico_id=? AND status='publicada'",(pai,tid)).rows):
        return jsonify(erro='Resposta original não encontrada.'),404
    r=_repo().db.execute('INSERT INTO respostas(topico_id,autor,conteudo,criado_em,autor_id,parent_id) VALUES(?,?,?,?,?,?)',(tid,g.usuario['nome'],conteudo,__import__('forum.repo',fromlist=['agora']).agora(),g.usuario['id'],pai))
    palavras=_repo().detectar_palavras(conteudo)
    if palavras:
        _repo().db.batch([("UPDATE respostas SET status='pendente' WHERE id=?",(r.last_id,)),("INSERT INTO moderacao(tipo,item_id,motivo,criado_em) VALUES('resposta',?,?,?)",(r.last_id,'Palavras restritas: '+', '.join(palavras),__import__('forum.repo',fromlist=['agora']).agora()))])
    if not palavras:
        _repo().db.execute('UPDATE topicos SET respostas=respostas+1 WHERE id=?',(tid,))
        _repo().notificar_resposta(r.last_id)
    return jsonify(id=r.last_id,topico_id=tid,status='pendente' if palavras else 'publicada'),201

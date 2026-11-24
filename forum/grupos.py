"""Grupos de estudo. Ver: todos os logados. Criar: admin e professor verificado. Editar/excluir/remover
participantes: admin (qualquer grupo) ou o professor responsável. Entrar/sair: alunos."""
from flask import Blueprint, current_app, g, jsonify, request

from forum.db import DbIntegrityError
from forum.repo import agora

bp = Blueprint('grupos', __name__, url_prefix='/api/grupos')
LISTA = ("SELECT gr.id, gr.nome, gr.descricao, gr.criado_em, gr.responsavel_id, r.nome AS responsavel_nome, "
         "r.foto AS responsavel_foto, r.perfil AS responsavel_perfil, COALESCE(r.verificado,0) AS responsavel_verificado, "
         "(SELECT COUNT(*) FROM grupo_membros gm WHERE gm.grupo_id=gr.id) AS participantes, "
         "EXISTS(SELECT 1 FROM grupo_membros gm WHERE gm.grupo_id=gr.id AND gm.usuario_id=?) AS participando "
         "FROM grupos gr LEFT JOIN usuarios r ON r.id=gr.responsavel_id")


def _db():
    return current_app.extensions['repo'].db


def _log(acao):
    current_app.extensions['repo'].registrar_log(g.usuario['email'], acao, 'ok')


def _fmt(x):
    x['participando'] = bool(x['participando'])
    x['responsavel_verificado'] = bool(x['responsavel_verificado'] and x['responsavel_perfil'] == 'professor')
    x['pode_gerenciar'] = _gerencia(x)
    return x


def _gerencia(gr):
    u = g.usuario
    return u['perfil'] == 'admin' or (u['perfil'] == 'professor' and bool(u['verificado'])
                                      and gr['responsavel_id'] == u['id'])


def _grupo(gid):
    r = _db().execute(LISTA + ' WHERE gr.id=?', (g.usuario['id'], gid)).rows
    return _fmt(r[0]) if r else None


def _dados(parcial=False):
    d = request.get_json(silent=True) or {}
    c = {}
    if 'nome' in d or not parcial:
        c['nome'] = ' '.join(str(d.get('nome') or '').split())
        if not 3 <= len(c['nome']) <= 80:
            return None, 'O nome deve ter entre 3 e 80 caracteres.'
    if 'descricao' in d or not parcial:
        c['descricao'] = str(d.get('descricao') or '').strip()[:1000]
    return c, None if c else 'Nenhuma alteração informada.'


@bp.get('')
def listar():
    return jsonify([_fmt(x) for x in _db().execute(LISTA + ' ORDER BY gr.nome COLLATE NOCASE', (g.usuario['id'],)).rows])


@bp.get('/<int:gid>')
def detalhe(gid):
    gr = _grupo(gid)
    if not gr:
        return jsonify(erro='Grupo não encontrado.'), 404
    gr['membros'] = _db().execute(
        'SELECT u.id, u.nome, u.foto, u.perfil FROM grupo_membros gm JOIN usuarios u ON u.id=gm.usuario_id '
        'WHERE gm.grupo_id=? ORDER BY u.nome COLLATE NOCASE', (gid,)).rows
    if gr['responsavel_verificado']:
        gr['responsavel'] = _db().execute('SELECT id, nome, foto, formacao, especialidade FROM usuarios WHERE id=?',
                                          (gr['responsavel_id'],)).rows[0]
    return jsonify(gr)


@bp.post('')
def criar():
    u = g.usuario
    if not (u['perfil'] == 'admin' or (u['perfil'] == 'professor' and u['verificado'])):
        return jsonify(erro='Somente professores verificados e administradores criam grupos.'), 403
    c, erro = _dados()
    if erro:
        return jsonify(erro=erro), 400
    try:
        r = _db().execute('INSERT INTO grupos(nome,descricao,criado_em,criado_por,responsavel_id) VALUES(?,?,?,?,?)',
                          (c['nome'], c['descricao'], agora(), u['email'], u['id']))
    except DbIntegrityError:
        return jsonify(erro='Já existe um grupo com esse nome.'), 409
    _log(f'criar grupo #{r.last_id}')
    return jsonify(_grupo(r.last_id)), 201


def _exige_gestao(gid):
    gr = _grupo(gid)
    if not gr:
        return None, (jsonify(erro='Grupo não encontrado.'), 404)
    if not gr['pode_gerenciar']:
        return None, (jsonify(erro='Você não pode gerenciar este grupo.'), 403)
    return gr, None


@bp.patch('/<int:gid>')
def editar(gid):
    gr, err = _exige_gestao(gid)
    if err:
        return err
    c, erro = _dados(parcial=True)
    if erro:
        return jsonify(erro=erro), 400
    try:
        _db().execute('UPDATE grupos SET ' + ','.join(k + '=?' for k in c) + ' WHERE id=?', (*c.values(), gid))
    except DbIntegrityError:
        return jsonify(erro='Já existe um grupo com esse nome.'), 409
    _log(f'editar grupo #{gid}')
    return jsonify(_grupo(gid))


@bp.delete('/<int:gid>')
def excluir(gid):
    gr, err = _exige_gestao(gid)
    if err:
        return err
    _db().batch([('DELETE FROM grupo_membros WHERE grupo_id=?', (gid,)), ('DELETE FROM grupos WHERE id=?', (gid,))])
    _log(f'excluir grupo #{gid}')
    return jsonify(ok=True)


@bp.delete('/<int:gid>/membros/<int:uid>')
def remover(gid, uid):
    gr, err = _exige_gestao(gid)
    if err:
        return err
    _db().execute('DELETE FROM grupo_membros WHERE grupo_id=? AND usuario_id=?', (gid, uid))
    _log(f'remover usuário #{uid} do grupo #{gid}')
    return jsonify(_grupo(gid))


@bp.post('/<int:gid>/entrar')
def entrar(gid):
    if g.usuario['perfil'] != 'aluno':
        return jsonify(erro='Somente alunos entram em grupos.'), 403
    if not _grupo(gid):
        return jsonify(erro='Grupo não encontrado.'), 404
    r = _db().execute('INSERT OR IGNORE INTO grupo_membros(grupo_id,usuario_id) VALUES(?,?)', (gid, g.usuario['id']))
    if not r.rowcount:
        return jsonify(erro='Você já participa deste grupo.'), 409
    return jsonify(_grupo(gid)), 201


@bp.post('/<int:gid>/sair')
def sair(gid):
    if g.usuario['perfil'] != 'aluno':
        return jsonify(erro='Somente alunos entram em grupos.'), 403
    if not _grupo(gid):
        return jsonify(erro='Grupo não encontrado.'), 404
    r = _db().execute('DELETE FROM grupo_membros WHERE grupo_id=? AND usuario_id=?', (gid, g.usuario['id']))
    if not r.rowcount:
        return jsonify(erro='Você não participa deste grupo.'), 409
    return jsonify(_grupo(gid))

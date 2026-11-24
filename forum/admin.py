"""Rotas administrativas incrementais. Todas protegidas no servidor por perfil admin."""
from flask import Blueprint, current_app, g, jsonify, request
from forum.auth import perfis
from forum.repo import agora

bp = Blueprint('admin', __name__, url_prefix='/api/admin')
def R(): return current_app.extensions['repo']
def D(): return R().db
def who(): return g.usuario['email']
def log(action, result='ok'): R().registrar_log(who(), action, result)
def body(): return request.get_json(silent=True) or {}

@bp.get('/professores')
@perfis('admin')
def professores():
    return jsonify(D().execute("SELECT id,nome,email,formacao,especialidade,descricao_profissional,verificado,status FROM usuarios WHERE perfil='professor' ORDER BY nome COLLATE NOCASE").rows)

@bp.patch('/professores/<int:uid>')
@perfis('admin')
def editar_professor(uid):
    d=body(); campos={k:str(d[k] or '').strip()[:lim] for k,lim in [('formacao',180),('especialidade',180),('descricao_profissional',2000)] if k in d}
    if not campos: return jsonify(erro='Informe ao menos um campo.'),400
    sets=', '.join(k+'=?' for k in campos)
    r=D().execute(f"UPDATE usuarios SET {sets} WHERE id=? AND perfil='professor'", (*campos.values(),uid))
    if not r.rowcount: return jsonify(erro='Professor não encontrado.'),404
    log(f'editar dados profissionais do professor #{uid}')
    return jsonify(ok=True)

@bp.get('/topicos')
@perfis('admin')
def topicos_admin(): return jsonify(R().listar_topicos(incluir_ocultos=True))

@bp.patch('/topicos/<int:tid>')
@perfis('admin')
def editar_topico(tid):
    d=body(); campos={k:str(d[k]).strip() for k in ('titulo','descricao') if k in d}
    if 'titulo' in campos and not 3 <= len(campos['titulo']) <= 150: return jsonify(erro='Título inválido.'),400
    if not campos: return jsonify(erro='Nenhum campo informado.'),400
    r=D().execute('UPDATE topicos SET '+', '.join(k+'=?' for k in campos)+' WHERE id=?',(*campos.values(),tid))
    if not r.rowcount:return jsonify(erro='Tópico não encontrado.'),404
    log(f'editar tópico #{tid}'); return jsonify(ok=True)

@bp.post('/topicos/<int:tid>/ocultar')
@perfis('admin')
def ocultar_topico(tid):
    r=D().execute('UPDATE topicos SET oculto=1 WHERE id=?',(tid,))
    if not r.rowcount:return jsonify(erro='Tópico não encontrado.'),404
    log(f'ocultar tópico #{tid}');return jsonify(ok=True)

@bp.post('/topicos/<int:tid>/mostrar')
@perfis('admin')
def mostrar_topico(tid):
    r=D().execute("UPDATE topicos SET oculto=0,status_moderacao='aprovado' WHERE id=?",(tid,))
    if not r.rowcount:return jsonify(erro='Tópico não encontrado.'),404
    log(f'reexibir tópico #{tid}');return jsonify(ok=True)

@bp.delete('/topicos/<int:tid>')
@perfis('admin')
def excluir_topico(tid):
    D().batch([('DELETE FROM respostas WHERE topico_id=?',(tid,)),('DELETE FROM moderacao WHERE tipo=? AND item_id=?',('topico',tid)),('DELETE FROM topicos WHERE id=?',(tid,))])
    log(f'excluir tópico #{tid}');return jsonify(ok=True)

@bp.get('/respostas')
@perfis('admin')
def respostas(): return jsonify(D().execute('SELECT * FROM respostas ORDER BY id DESC').rows)

@bp.delete('/respostas/<int:rid>')
@perfis('admin')
def excluir_resposta(rid):
    alvo=D().execute('SELECT topico_id,status FROM respostas WHERE id=?',(rid,)).rows
    if not alvo:return jsonify(erro='Resposta não encontrada.'),404
    D().batch([('DELETE FROM respostas WHERE id=?',(rid,)),('UPDATE topicos SET respostas=CASE WHEN respostas>0 AND ?=\'publicada\' THEN respostas-1 ELSE respostas END WHERE id=?',(alvo[0]['status'],alvo[0]['topico_id']))])
    log(f'excluir resposta #{rid}');return jsonify(ok=True)

@bp.get('/moderacao')
@perfis('admin')
def fila_moderacao(): return jsonify(D().execute("SELECT m.*,CASE m.tipo WHEN 'resposta' THEN (SELECT substr(conteudo,1,300) FROM respostas WHERE id=m.item_id) ELSE (SELECT titulo FROM topicos WHERE id=m.item_id) END AS conteudo FROM moderacao m ORDER BY m.id DESC").rows)

@bp.post('/moderacao/<int:mid>/aprovar')
@perfis('admin')
def aprovar(mid):
    row=D().execute('SELECT * FROM moderacao WHERE id=?',(mid,)).rows
    if not row:return jsonify(erro='Sinalização não encontrada.'),404
    m=row[0]
    if m['status']!='pendente':return jsonify(erro='Sinalização já revisada.'),409
    if m['tipo']=='topico': D().execute("UPDATE topicos SET status_moderacao='aprovado',oculto=0 WHERE id=?",(m['item_id'],))
    elif m['tipo']=='resposta':
        if D().execute("UPDATE respostas SET status='publicada' WHERE id=? AND status='pendente'",(m['item_id'],)).rowcount:
            D().execute('UPDATE topicos SET respostas=respostas+1 WHERE id=(SELECT topico_id FROM respostas WHERE id=?)',(m['item_id'],))
            R().notificar_resposta(m['item_id'])
    D().execute("UPDATE moderacao SET status='aprovado',revisado_em=?,revisado_por=? WHERE id=?",(agora(),who(),mid))
    log(f'aprovar sinalização #{mid}');return jsonify(ok=True)

@bp.post('/moderacao/<int:mid>/excluir')
@perfis('admin')
def excluir_sinalizado(mid):
    rows=D().execute('SELECT * FROM moderacao WHERE id=?',(mid,)).rows
    if not rows:return jsonify(erro='Sinalização não encontrada.'),404
    m=rows[0]
    if m['status']!='pendente':return jsonify(erro='Sinalização já revisada.'),409
    if m['tipo']=='topico': D().batch([('DELETE FROM respostas WHERE topico_id=?',(m['item_id'],)),('DELETE FROM topicos WHERE id=?',(m['item_id'],))])
    elif m['tipo']=='resposta':   # rejeita sem apagar: o texto fica no histórico, fora da publicação
        alvo=D().execute('SELECT topico_id,status FROM respostas WHERE id=?',(m['item_id'],)).rows
        if alvo:D().batch([("UPDATE respostas SET status='rejeitada' WHERE id=?",(m['item_id'],)),('UPDATE topicos SET respostas=CASE WHEN respostas>0 AND ?=\'publicada\' THEN respostas-1 ELSE respostas END WHERE id=?',(alvo[0]['status'],alvo[0]['topico_id']))])
    D().execute("UPDATE moderacao SET status='excluido',revisado_em=?,revisado_por=? WHERE id=?",(agora(),who(),mid))
    log(f'excluir conteúdo sinalizado #{mid}');return jsonify(ok=True)

@bp.get('/palavras-restritas')
@perfis('admin')
def palavras(): return jsonify(R().palavras())

@bp.post('/palavras-restritas')
@perfis('admin')
def criar_palavra():
    palavra=' '.join(str(body().get('palavra','')).split())[:80]
    if not palavra:return jsonify(erro='Informe a palavra.'),400
    try:D().execute('INSERT INTO palavras_restritas(palavra,criado_em) VALUES(?,?)',(palavra,agora()))
    except Exception:return jsonify(erro='Palavra já cadastrada.'),409
    log(f'adicionar palavra restrita: {palavra}');return jsonify(ok=True),201

@bp.patch('/palavras-restritas/<int:pid>')
@perfis('admin')
def editar_palavra(pid):
    d=body(); sets=[]; vals=[]
    if 'palavra' in d: sets.append('palavra=?');vals.append(' '.join(str(d['palavra']).split())[:80])
    if 'ativo' in d: sets.append('ativo=?');vals.append(1 if d['ativo'] else 0)
    if not sets:return jsonify(erro='Nenhum campo informado.'),400
    vals.append(pid)
    try:r=D().execute('UPDATE palavras_restritas SET '+','.join(sets)+' WHERE id=?',vals)
    except Exception:return jsonify(erro='Palavra já cadastrada.'),409
    if not r.rowcount:return jsonify(erro='Palavra não encontrada.'),404
    log(f'editar palavra restrita #{pid}');return jsonify(ok=True)

@bp.delete('/palavras-restritas/<int:pid>')
@perfis('admin')
def excluir_palavra(pid):
    r=D().execute('DELETE FROM palavras_restritas WHERE id=?',(pid,))
    if not r.rowcount:return jsonify(erro='Palavra não encontrada.'),404
    log(f'remover palavra restrita #{pid}');return jsonify(ok=True)

@bp.get('/grupos')
@perfis('admin')
def grupos(): return jsonify(D().execute('SELECT g.*,COUNT(gm.usuario_id) membros FROM grupos g LEFT JOIN grupo_membros gm ON gm.grupo_id=g.id GROUP BY g.id ORDER BY g.nome').rows)

@bp.post('/grupos')
@perfis('admin')
def criar_grupo():
    d=body(); nome=' '.join(str(d.get('nome','')).split())
    if not nome:return jsonify(erro='Informe o nome do grupo.'),400
    try:r=D().execute('INSERT INTO grupos(nome,descricao,criado_em,criado_por,responsavel_id) VALUES(?,?,?,?,?)',(nome,str(d.get('descricao',''))[:1000],agora(),who(),g.usuario['id']))
    except Exception:return jsonify(erro='Grupo já existente.'),409
    log(f'criar grupo #{r.last_id}');return jsonify(id=r.last_id),201

@bp.patch('/grupos/<int:gid>')
@perfis('admin')
def editar_grupo(gid):
    d=body(); fields={k:str(d[k]).strip() for k in ('nome','descricao') if k in d}
    if not fields:return jsonify(erro='Nenhum campo informado.'),400
    try:r=D().execute('UPDATE grupos SET '+','.join(k+'=?' for k in fields)+' WHERE id=?',(*fields.values(),gid))
    except Exception:return jsonify(erro='Já existe grupo com esse nome.'),409
    if not r.rowcount:return jsonify(erro='Grupo não encontrado.'),404
    log(f'editar grupo #{gid}');return jsonify(ok=True)

@bp.delete('/grupos/<int:gid>')
@perfis('admin')
def excluir_grupo(gid):
    D().batch([('DELETE FROM grupo_membros WHERE grupo_id=?',(gid,)),('DELETE FROM grupos WHERE id=?',(gid,))]);log(f'excluir grupo #{gid}');return jsonify(ok=True)

@bp.get('/grupos/<int:gid>/membros')
@perfis('admin')
def listar_membros_grupo(gid):
    if not D().execute('SELECT id FROM grupos WHERE id=?',(gid,)).rows:return jsonify(erro='Grupo não encontrado.'),404
    return jsonify(D().execute('SELECT u.id,u.nome,u.email,u.perfil FROM grupo_membros gm JOIN usuarios u ON u.id=gm.usuario_id WHERE gm.grupo_id=? ORDER BY u.nome',(gid,)).rows)

@bp.delete('/grupos/<int:gid>/membros/<int:uid>')
@perfis('admin')
def remover_membro_grupo(gid,uid):
    D().execute('DELETE FROM grupo_membros WHERE grupo_id=? AND usuario_id=?',(gid,uid));log(f'remover usuário #{uid} do grupo #{gid}');return jsonify(ok=True)

@bp.post('/grupos/<int:gid>/membros')
@perfis('admin')
def adicionar_membro_grupo(gid):
    uid=body().get('usuario_id')
    if not D().execute('SELECT id FROM grupos WHERE id=?',(gid,)).rows:return jsonify(erro='Grupo não encontrado.'),404
    if not D().execute('SELECT id FROM usuarios WHERE id=?',(uid,)).rows:return jsonify(erro='Usuário não encontrado.'),404
    if not isinstance(uid,int):return jsonify(erro='Usuário inválido.'),400
    D().execute('INSERT OR IGNORE INTO grupo_membros(grupo_id,usuario_id) VALUES(?,?)',(gid,uid));log(f'adicionar usuário #{uid} ao grupo #{gid}');return jsonify(ok=True)

@bp.get('/configuracoes')
@perfis('admin')
def configuracoes():
    try:
        info=R().saude(); info.update(R().dashboard_completo());return jsonify(sistema={'app':'Fórum AVL','modo':current_app.config.get('ENV','production')},banco=info)
    except Exception as e:return jsonify(sistema={'app':'Fórum AVL'},banco={'conectado':False,'erro':str(e)[:200]}),503

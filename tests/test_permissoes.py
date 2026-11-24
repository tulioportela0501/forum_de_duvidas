"""Matriz de permissões: TODO endpoint /api × TODOS os perfis (anônimo, aluno, professor, admin).

Para cada combinação confere que o backend responde 401 (sem sessão), 403 (perfil errado) ou deixa passar
(qualquer outro status: 200/400/404… — o importante é que o porteiro não barrou). Usa ids inexistentes nas
rotas destrutivas, então nada é de fato apagado. Também garante que NENHUM endpoint novo escape da matriz."""
import pytest

from forum.auth import PUBLICAS

ADM, PROF, TODOS = {'admin'}, {'admin', 'professor'}, {'admin', 'professor', 'aluno'}
X = 99999

# (endpoint, método, url, perfis permitidos)
MATRIZ = [
    ('api.listar_tags', 'GET', '/api/tags', TODOS),
    ('api.autocompletar', 'GET', '/api/tags/autocomplete?q=ab', TODOS),
    ('api.criar_tag', 'POST', '/api/tags', PROF),
    ('api.remover_tag', 'DELETE', '/api/tags/inexistente', ADM),
    ('api.editar_tag', 'PATCH', '/api/tags/inexistente', ADM),
    ('api.listar_topicos', 'GET', '/api/topicos', TODOS),
    ('api.criar_topico', 'POST', '/api/topicos', TODOS),
    ('api.listar_respostas', 'GET', f'/api/topicos/{X}/respostas', TODOS),
    ('api.criar_resposta', 'POST', f'/api/topicos/{X}/respostas', TODOS),
    ('api.curtir_topico', 'POST', f'/api/topicos/{X}/curtir', TODOS),
    ('api.curtir_resposta', 'POST', f'/api/respostas/{X}/curtir', TODOS),
    ('perfis.meu_perfil', 'GET', '/api/perfil', TODOS),
    ('perfis.preview', 'GET', f'/api/perfis/{X}', TODOS),
    ('perfis.foto_usuario', 'GET', f'/api/perfis/{X}/foto', TODOS),
    ('api.repostar_topico', 'POST', f'/api/topicos/{X}/repostar', TODOS),
    ('perfis.editar_perfil', 'PATCH', '/api/perfil', TODOS),
    ('perfis.diretorio', 'GET', '/api/professores', TODOS),
    ('perfis.professor', 'GET', f'/api/professores/{X}', TODOS),
    ('perfis.notificacoes', 'GET', '/api/notificacoes', {'aluno', 'professor'}),
    ('perfis.contagem_notificacoes', 'GET', '/api/notificacoes/contagem', {'aluno', 'professor'}),
    ('perfis.marcar_todas', 'POST', '/api/notificacoes/lidas', {'aluno', 'professor'}),
    ('perfis.marcar_uma', 'POST', f'/api/notificacoes/{X}/lida', {'aluno', 'professor'}),
    ('api.listar_membros', 'GET', '/api/membros', TODOS),
    ('api.avl', 'GET', '/api/avl', PROF),
    ('api.rotacoes', 'GET', '/api/avl/rotacoes', PROF),
    ('api.teste', 'POST', '/api/avl/teste', PROF),
    ('api.dashboard', 'GET', '/api/dashboard', ADM),
    ('api.logs', 'GET', '/api/logs', ADM),
    ('auth.eu', 'GET', '/api/auth/eu', TODOS),
    ('usuarios.listar', 'GET', '/api/usuarios', ADM),
    ('usuarios.criar', 'POST', '/api/usuarios', ADM),
    ('usuarios.obter', 'GET', f'/api/usuarios/{X}', ADM),
    ('usuarios.editar', 'PATCH', f'/api/usuarios/{X}', ADM),
    ('usuarios.excluir', 'DELETE', f'/api/usuarios/{X}', ADM),
    ('usuarios.bloquear', 'POST', f'/api/usuarios/{X}/bloquear', ADM),
    ('usuarios.desbloquear', 'POST', f'/api/usuarios/{X}/desbloquear', ADM),
    ('usuarios.verificar', 'POST', f'/api/usuarios/{X}/verificar', ADM),
    ('usuarios.revogar_verificacao', 'POST', f'/api/usuarios/{X}/revogar-verificacao', ADM),
    ('admin.professores', 'GET', '/api/admin/professores', ADM),
    ('admin.editar_professor', 'PATCH', f'/api/admin/professores/{X}', ADM),
    ('admin.topicos_admin', 'GET', '/api/admin/topicos', ADM),
    ('admin.editar_topico', 'PATCH', f'/api/admin/topicos/{X}', ADM),
    ('admin.ocultar_topico', 'POST', f'/api/admin/topicos/{X}/ocultar', ADM),
    ('admin.mostrar_topico', 'POST', f'/api/admin/topicos/{X}/mostrar', ADM),
    ('admin.excluir_topico', 'DELETE', f'/api/admin/topicos/{X}', ADM),
    ('admin.respostas', 'GET', '/api/admin/respostas', ADM),
    ('admin.excluir_resposta', 'DELETE', f'/api/admin/respostas/{X}', ADM),
    ('admin.fila_moderacao', 'GET', '/api/admin/moderacao', ADM),
    ('admin.aprovar', 'POST', f'/api/admin/moderacao/{X}/aprovar', ADM),
    ('admin.excluir_sinalizado', 'POST', f'/api/admin/moderacao/{X}/excluir', ADM),
    ('admin.palavras', 'GET', '/api/admin/palavras-restritas', ADM),
    ('admin.criar_palavra', 'POST', '/api/admin/palavras-restritas', ADM),
    ('admin.editar_palavra', 'PATCH', f'/api/admin/palavras-restritas/{X}', ADM),
    ('admin.excluir_palavra', 'DELETE', f'/api/admin/palavras-restritas/{X}', ADM),
    ('admin.grupos', 'GET', '/api/admin/grupos', ADM),
    ('admin.criar_grupo', 'POST', '/api/admin/grupos', ADM),
    ('admin.editar_grupo', 'PATCH', f'/api/admin/grupos/{X}', ADM),
    ('admin.excluir_grupo', 'DELETE', f'/api/admin/grupos/{X}', ADM),
    ('admin.listar_membros_grupo', 'GET', f'/api/admin/grupos/{X}/membros', ADM),
    ('admin.remover_membro_grupo', 'DELETE', f'/api/admin/grupos/{X}/membros/{X}', ADM),
    ('admin.adicionar_membro_grupo', 'POST', f'/api/admin/grupos/{X}/membros', ADM),
    ('admin.configuracoes', 'GET', '/api/admin/configuracoes', ADM),
]
# exigem sessão (qualquer perfil), mas destroem a própria sessão/senha: testadas em test_auth.py
SO_LOGADO = {'auth.logout', 'auth.trocar_senha', 'grupos.listar', 'grupos.detalhe', 'grupos.criar', 'grupos.editar', 'grupos.excluir',
              'grupos.remover', 'grupos.entrar', 'grupos.sair'}  # regras por papel/dono dentro da própria função
PUBLICAS_URLS = [('GET', '/api/health'), ('GET', '/api/auth/estado'),
                 ('POST', '/api/auth/login'), ('POST', '/api/auth/setup')]


def test_matriz_cobre_todos_os_endpoints_e_bate_com_os_decoradores(app):
    """Se alguém criar uma rota nova sem decidir quem pode usá-la, este teste falha."""
    na_matriz = {e: perfis for e, _, _, perfis in MATRIZ}
    for rule in app.url_map.iter_rules():
        ep = rule.endpoint
        if ep in ('static', 'index') or not rule.rule.startswith('/api/'):
            continue
        assert ep in na_matriz or ep in PUBLICAS or ep in SO_LOGADO, f'endpoint sem regra de permissão: {ep}'
        if ep in na_matriz:
            declarado = getattr(app.view_functions[ep], 'perfis_permitidos', None) or TODOS
            assert set(declarado) == na_matriz[ep], f'{ep}: decorador {set(declarado)} != matriz {na_matriz[ep]}'
    assert PUBLICAS == {'api.health', 'auth.estado', 'auth.setup', 'auth.login'}


@pytest.mark.parametrize('endpoint,metodo,url,permitidos', MATRIZ, ids=[m[0] for m in MATRIZ])
def test_matriz(endpoint, metodo, url, permitidos, anon, admin, prof, aluno):
    # sem sessão: sempre 401
    assert anon.req(metodo, url, json={} if metodo != 'GET' else None).status_code == 401
    for perfil, cli in (('aluno', aluno), ('professor', prof), ('admin', admin)):
        r = cli.req(metodo, url, json={} if metodo != 'GET' else None)
        if perfil in permitidos:
            assert r.status_code not in (401, 403), f'{perfil} deveria passar em {endpoint}: {r.status_code}'
        else:
            assert r.status_code == 403, f'{perfil} deveria ser barrado em {endpoint}: {r.status_code}'


def test_rotas_publicas_respondem_sem_sessao(anon):
    assert anon.get('/api/health').status_code == 200
    assert anon.get('/api/auth/estado').get_json() == {'configurado': False}
    # login e setup chegam ao handler (validação própria), não ao porteiro de sessão
    r = anon.post('/api/auth/login', {})
    assert r.status_code == 401 and r.get_json()['erro'] == 'E-mail ou senha incorretos.'
    assert anon.post('/api/auth/setup', {}).status_code == 400


def test_perfil_barrado_nao_causa_efeito_colateral(admin, aluno, prof):
    """Um 403 tem que acontecer ANTES da ação: nada é criado/removido/alterado."""
    assert aluno.post('/api/usuarios', {'nome': 'Hacker', 'email': 'h@x.com', 'senha': 'senhaforte123',
                                        'perfil': 'admin'}).status_code == 403
    assert prof.post('/api/usuarios', {'nome': 'Hacker', 'email': 'h@x.com', 'senha': 'senhaforte123',
                                       'perfil': 'admin'}).status_code == 403
    assert 'h@x.com' not in [u['email'] for u in admin.get('/api/usuarios').get_json()]
    admin.post('/api/tags', {'nome': 'Persiste'})
    assert aluno.delete('/api/tags/persiste').status_code == 403
    assert prof.delete('/api/tags/persiste').status_code == 403
    assert [t['key'] for t in admin.get('/api/tags').get_json()] == ['persiste']
    assert aluno.delete(f'/api/usuarios/{prof.id}').status_code == 403
    assert admin.get(f'/api/usuarios/{prof.id}').status_code == 200


def test_aluno_nao_se_promove(admin, aluno):
    assert aluno.patch(f'/api/usuarios/{aluno.id}', {'perfil': 'admin'}).status_code == 403
    assert aluno.post('/api/auth/setup', {'nome': 'X', 'email': 'x@x.com', 'senha': 'senhaforte123'}).status_code == 409
    assert admin.get(f'/api/usuarios/{aluno.id}').get_json()['perfil'] == 'aluno'
    assert aluno.get('/api/auth/eu').get_json()['usuario']['perfil'] == 'aluno'


def test_fluxo_antigo_removido(app, admin, anon):
    assert 'CODIGO_ADMIN' not in app.config
    for metodo, url in [('POST', '/api/admin/registro'), ('POST', '/api/admin/login')]:
        for cli in (anon, admin):
            assert cli.req(metodo, url, json={'codigo': 'x', 'email': 'a@b.com', 'senha': 'senhaforte123'}
                           ).status_code in (404, 405), url
    assert anon.get('/admin-cadastro.html').status_code == 404
    # o cabeçalho Bearer do fluxo antigo não autentica ninguém
    assert anon.get('/api/avl', headers={'Authorization': 'Bearer qualquer'}).status_code == 401

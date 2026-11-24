from forum import create_app


def test_frontend_e_health(anon):
    j = anon.get('/api/health').get_json()
    assert j['status'] == 'ok' and j['db']['conectado'] and j['db']['esquema_ok']
    assert anon.get('/').status_code == 200
    assert anon.get('/js/app.js').status_code == 200
    assert anon.get('/login.html').status_code == 200


def test_topico_cria_tags_na_avl_e_incrementa_uso(aluno):
    r = aluno.post('/api/topicos', {'titulo': 'Como funciona a AVL?', 'descricao': 'dúvida',
                                    'autor': 'Fulano Falso', 'tags': ['AVL', 'Árvores', 'avl']})
    assert r.status_code == 201 and r.get_json()['tags'] == ['AVL', 'Árvores']
    assert r.get_json()['autor'] == 'Aluno'          # vem da sessão; o "autor" enviado pelo cliente é ignorado
    aluno.post('/api/topicos', {'titulo': 'Outra dúvida', 'tags': ['avl']})
    tags = {t['key']: t for t in aluno.get('/api/tags').get_json()}
    assert tags['avl']['usage_count'] == 2 and tags['arvores']['usage_count'] == 1
    assert len(aluno.get('/api/topicos').get_json()) == 2


def test_validacoes_de_topico(aluno):
    assert aluno.post('/api/topicos', {'titulo': 'ab', 'tags': ['x']}).status_code == 400
    assert aluno.post('/api/topicos', {'titulo': 'Título ok', 'tags': []}).status_code == 400
    assert aluno.post('/api/topicos', {'titulo': 'Título ok', 'tags': ['<script>']}).status_code == 400


def test_limite_de_duvidas_por_usuario(aluno, prof):
    for i in range(20):
        assert aluno.post('/api/topicos', {'titulo': f'Dúvida {i}', 'tags': ['x']}).status_code == 201
    assert aluno.post('/api/topicos', {'titulo': 'Dúvida 21', 'tags': ['x']}).status_code == 429
    assert prof.post('/api/topicos', {'titulo': 'Outro usuário', 'tags': ['x']}).status_code == 201


def test_autocomplete(aluno):
    aluno.post('/api/topicos', {'titulo': 'Teste', 'tags': ['python', 'pytest', 'java']})
    r = aluno.get('/api/tags/autocomplete?q=py').get_json()
    assert [t['display_name'] for t in r] == ['pytest', 'python']
    assert aluno.get('/api/tags/autocomplete?q=').get_json() == []


def test_professor_cria_tag_mas_so_admin_remove(admin, prof):
    assert prof.post('/api/tags', {'nome': 'Grafos', 'descricao': 'BFS/DFS'}).status_code == 201
    assert admin.post('/api/tags', {'nome': 'grafos'}).status_code == 409
    assert prof.delete('/api/tags/grafos').status_code == 403
    assert admin.delete('/api/tags/grafos').status_code == 200
    assert admin.delete('/api/tags/grafos').status_code == 404
    assert admin.get('/api/tags').get_json() == []


def test_avl_dashboard_logs_e_rotacoes(admin, aluno):
    aluno.post('/api/topicos', {'titulo': 'Rotações', 'tags': ['a', 'b', 'c']})
    snap = admin.get('/api/avl').get_json()
    assert snap['root']['key'] == 'b' and snap['stats']['balanced'] is True
    assert admin.get('/api/avl/rotacoes').get_json()['por_tipo']['RR'] == 1
    dash = admin.get('/api/dashboard').get_json()
    assert dash['tags'] == 3 and dash['topicos'] == 1 and dash['membros'] == 4
    assert admin.get('/api/logs').get_json()


def test_teste_carga_nao_altera_dados_reais(admin):
    r = admin.post('/api/avl/teste').get_json()
    assert len(r['passos']) == 20 and r['resumo']['balanceada'] is True
    assert admin.get('/api/tags').get_json() == []


def test_serverless_sem_estado_nova_instancia_ve_os_mesmos_dados(cfg):
    """Cada create_app() simula uma instância fria: AVL e sessões vêm do banco, não da memória."""
    from tests.conftest import Cli
    a1 = create_app(cfg)
    c1 = Cli(a1)
    c1.csrf = c1.post('/api/auth/setup', {'nome': 'Admin', 'email': 'a@b.com', 'senha': 'senhaforte123'}
                      ).get_json()['csrf']
    c1.post('/api/topicos', {'titulo': 'Persistir', 'tags': ['sqlite', 'avl']})
    c2 = Cli(create_app({**cfg, 'AUTO_INIT_DB': False}))
    c2.c.set_cookie('forum_sid', c1.cookie(), path='/api')      # mesma sessão, outra instância
    c2.csrf = c1.csrf
    assert [t['key'] for t in c2.get('/api/tags').get_json()] == ['avl', 'sqlite']
    c2.post('/api/topicos', {'titulo': 'Outra', 'tags': ['avl']})
    assert {t['key']: t['usage_count'] for t in c1.get('/api/tags').get_json()}['avl'] == 2


def test_erro_json_em_rota_inexistente(admin):
    r = admin.get('/api/naoexiste')
    assert r.status_code == 404 and 'erro' in r.get_json()

import pytest

from app import create_app

CODIGO = 'CODIGO-TESTE-123'


@pytest.fixture()
def client(tmp_path):
    app = create_app({'DATA_DIR': str(tmp_path), 'SECRET_KEY': 'teste', 'CODIGO_ADMIN': CODIGO})
    app.config['TESTING'] = True
    return app.test_client()


@pytest.fixture()
def auth(client):
    r = client.post('/api/admin/registro', json={'nome': 'Admin', 'email': 'a@b.com',
                                                 'senha': 'senhaforte123', 'codigo': CODIGO})
    assert r.status_code == 200
    return {'Authorization': 'Bearer ' + r.get_json()['token']}


def test_frontend_e_health(client):
    assert client.get('/api/health').get_json() == {'status': 'ok'}
    assert client.get('/').status_code == 200
    assert client.get('/js/app.js').status_code == 200


def test_rotas_admin_exigem_token(client):
    for m, url in [('get', '/api/avl'), ('get', '/api/logs'), ('get', '/api/dashboard'),
                   ('get', '/api/avl/rotacoes'), ('post', '/api/avl/teste'), ('post', '/api/tags')]:
        assert getattr(client, m)(url).status_code == 401, url


def test_registro_codigo_errado_e_senha_curta(client):
    base = {'nome': 'X', 'email': 'x@y.com', 'senha': 'senhaforte123', 'codigo': 'errado'}
    assert client.post('/api/admin/registro', json=base).status_code == 403
    assert client.post('/api/admin/registro', json={**base, 'codigo': CODIGO, 'senha': 'curta'}).status_code == 400


def test_login_e_email_duplicado(client, auth):
    r = client.post('/api/admin/registro', json={'nome': 'A', 'email': 'a@b.com',
                                                 'senha': 'senhaforte123', 'codigo': CODIGO})
    assert r.status_code == 409
    assert client.post('/api/admin/login', json={'email': 'a@b.com', 'senha': 'senhaforte123'}).status_code == 200
    assert client.post('/api/admin/login', json={'email': 'a@b.com', 'senha': 'errada'}).status_code == 401


def test_topico_cria_tags_na_avl_e_incrementa_uso(client, auth):
    r = client.post('/api/topicos', json={'titulo': 'Como funciona a AVL?', 'descricao': 'dúvida',
                                          'autor': 'Marco', 'tags': ['AVL', 'Árvores', 'avl']})
    assert r.status_code == 201 and r.get_json()['tags'] == ['AVL', 'Árvores']
    client.post('/api/topicos', json={'titulo': 'Outra dúvida', 'tags': ['avl']})
    tags = {t['key']: t for t in client.get('/api/tags').get_json()}
    assert tags['avl']['usage_count'] == 2 and tags['arvores']['usage_count'] == 1
    assert len(client.get('/api/topicos').get_json()) == 2


def test_validacoes_de_topico(client):
    assert client.post('/api/topicos', json={'titulo': 'ab', 'tags': ['x']}).status_code == 400
    assert client.post('/api/topicos', json={'titulo': 'Título ok', 'tags': []}).status_code == 400
    assert client.post('/api/topicos', json={'titulo': 'Título ok', 'tags': ['<script>']}).status_code == 400


def test_autocomplete(client, auth):
    client.post('/api/topicos', json={'titulo': 'Teste', 'tags': ['python', 'pytest', 'java']})
    r = client.get('/api/tags/autocomplete?q=py').get_json()
    assert [t['display_name'] for t in r] == ['pytest', 'python']
    assert client.get('/api/tags/autocomplete?q=').get_json() == []


def test_admin_cria_e_remove_tag(client, auth):
    r = client.post('/api/tags', json={'nome': 'Grafos', 'descricao': 'BFS/DFS'}, headers=auth)
    assert r.status_code == 201
    assert client.post('/api/tags', json={'nome': 'grafos'}, headers=auth).status_code == 409
    assert client.delete('/api/tags/grafos', headers=auth).status_code == 200
    assert client.delete('/api/tags/grafos', headers=auth).status_code == 404
    assert client.get('/api/tags').get_json() == []


def test_avl_dashboard_logs_e_rotacoes(client, auth):
    client.post('/api/topicos', json={'titulo': 'Rotações', 'tags': ['a', 'b', 'c']})
    snap = client.get('/api/avl', headers=auth).get_json()
    assert snap['root']['key'] == 'b' and snap['stats']['balanced'] is True
    assert client.get('/api/avl/rotacoes', headers=auth).get_json()['por_tipo']['RR'] == 1
    dash = client.get('/api/dashboard', headers=auth).get_json()
    assert dash['tags'] == 3 and dash['topicos'] == 1 and dash['membros'] == 4
    assert client.get('/api/logs', headers=auth).get_json()


def test_teste_carga_nao_altera_dados_reais(client, auth):
    r = client.post('/api/avl/teste', headers=auth).get_json()
    assert len(r['passos']) == 20 and r['resumo']['balanceada'] is True
    assert client.get('/api/tags').get_json() == []


def test_persistencia_reconstroi_avl(tmp_path):
    cfg = {'DATA_DIR': str(tmp_path), 'SECRET_KEY': 'k', 'CODIGO_ADMIN': CODIGO}
    c1 = create_app(cfg).test_client()
    c1.post('/api/topicos', json={'titulo': 'Persistir', 'tags': ['sqlite', 'avl']})
    c2 = create_app(cfg).test_client()
    assert [t['key'] for t in c2.get('/api/tags').get_json()] == ['avl', 'sqlite']


def test_erro_json_em_rota_inexistente(client):
    r = client.get('/api/naoexiste')
    assert r.status_code == 404 and 'erro' in r.get_json()

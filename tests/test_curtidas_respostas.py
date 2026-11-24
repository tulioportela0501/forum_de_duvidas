"""Curtidas (alternar) e respostas a respostas (pai_id), em qualquer perfil."""


def _duvida(aluno):
    r = aluno.post('/api/topicos', json={'titulo': 'duvida 1', 'descricao': 'uma duvida', 'tags': ['duvida']})
    assert r.status_code == 201, r.get_json()
    return r.get_json()['id']


def test_professor_responde_a_resposta_do_aluno(aluno, prof):
    tid = _duvida(aluno)
    r1 = aluno.post(f'/api/topicos/{tid}/respostas', json={'conteudo': 'sigo com duvida'}).get_json()['id']
    r2 = prof.post(f'/api/topicos/{tid}/respostas', json={'conteudo': 'veja isto', 'pai_id': r1})
    assert r2.status_code == 201
    lista = aluno.get(f'/api/topicos/{tid}/respostas').get_json()
    assert [x['parent_id'] for x in lista] == [None, r1]


def test_pai_invalido_ou_de_outro_topico(aluno, prof):
    t1, t2 = _duvida(aluno), _duvida(aluno)
    r1 = aluno.post(f'/api/topicos/{t1}/respostas', json={'conteudo': 'a'}).get_json()['id']
    assert prof.post(f'/api/topicos/{t2}/respostas', json={'conteudo': 'b', 'pai_id': r1}).status_code == 404
    assert prof.post(f'/api/topicos/{t1}/respostas', json={'conteudo': 'b', 'pai_id': 'x'}).status_code == 404


def test_curtir_alterna_e_conta(aluno, prof):
    tid = _duvida(aluno)
    rid = aluno.post(f'/api/topicos/{tid}/respostas', json={'conteudo': 'a'}).get_json()['id']
    assert prof.post(f'/api/topicos/{tid}/curtir').get_json() == {'curtidas': 1, 'curtiu': True}
    assert aluno.post(f'/api/topicos/{tid}/curtir').get_json()['curtidas'] == 2
    assert prof.post(f'/api/topicos/{tid}/curtir').get_json() == {'curtidas': 1, 'curtiu': False}
    assert prof.post(f'/api/respostas/{rid}/curtir').get_json()['curtiu'] is True
    topico = next(t for t in aluno.get('/api/topicos').get_json() if t['id'] == tid)
    assert (topico['curtidas'], topico['curtiu']) == (1, True)
    resp = aluno.get(f'/api/topicos/{tid}/respostas').get_json()[0]
    assert (resp['curtidas'], resp['curtiu']) == (1, False)
    assert prof.post('/api/respostas/9999/curtir').status_code == 404


PNG = ('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')


def test_repostar_alterna(aluno, prof):
    tid = _duvida(aluno)
    assert prof.post(f'/api/topicos/{tid}/repostar').get_json() == {'reposts': 1, 'repostou': True}
    t = next(x for x in prof.get('/api/topicos').get_json() if x['id'] == tid)
    assert (t['reposts'], t['repostou']) == (1, True)
    assert prof.post(f'/api/topicos/{tid}/repostar').get_json() == {'reposts': 0, 'repostou': False}
    assert prof.post('/api/topicos/9999/repostar').status_code == 404


def test_foto_servida_como_imagem_e_preview(aluno, prof):
    uid = aluno.get('/api/perfil').get_json()['id']
    assert prof.get(f'/api/perfis/{uid}/foto').status_code == 404
    assert aluno.patch('/api/perfil', json={'foto': PNG, 'biografia': 'oi'}).status_code == 200
    r = prof.get(f'/api/perfis/{uid}/foto')
    assert r.status_code == 200 and r.mimetype == 'image/png' and r.data[:4] == b'\x89PNG'
    assert prof.get(f'/api/perfis/{uid}/foto', headers={'If-None-Match': r.headers['ETag']}).status_code == 304
    p = prof.get(f'/api/perfis/{uid}').get_json()
    assert p['tem_foto'] is True and p['biografia'] == 'oi' and 'email' not in p
    tid = _duvida(aluno)
    t = next(x for x in prof.get('/api/topicos').get_json() if x['id'] == tid)
    assert t['autor_id'] == uid and t['autor_foto'] is True
    assert aluno.get('/api/auth/eu').get_json()['usuario']['tem_foto'] is True

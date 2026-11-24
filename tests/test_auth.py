"""Primeiro acesso, login, sessões, CSRF, senhas e limitação de tentativas."""
import time

import pytest

from forum.db import DbIntegrityError
from tests.conftest import SENHA, Cli

SETUP = {'nome': 'Dona do Sistema', 'email': 'Dona@Escola.com', 'senha': SENHA}


# ------------------------------------------------------------ primeiro acesso
def test_primeiro_acesso_cria_principal_e_fecha(app, anon):
    assert anon.get('/api/auth/estado').get_json() == {'configurado': False}
    r = anon.post('/api/auth/setup', SETUP)
    assert r.status_code == 201
    u = r.get_json()['usuario']
    assert u['perfil'] == 'admin' and u['principal'] is True and u['email'] == 'dona@escola.com'
    assert anon.cookie()                                        # já entra logado
    assert anon.get('/api/auth/estado').get_json() == {'configurado': True}
    # depois do primeiro acesso a rota fecha para sempre
    outro = Cli(app, ip='10.0.0.50')
    r2 = outro.post('/api/auth/setup', {**SETUP, 'email': 'outro@x.com'})
    assert r2.status_code == 409 and not outro.cookie()


@pytest.mark.parametrize('corpo,trecho', [
    ({'nome': '', 'email': 'a@b.com', 'senha': SENHA}, 'Nome'),
    ({'nome': 'Ok', 'email': 'sem-arroba', 'senha': SENHA}, 'E-mail'),
    ({'nome': 'Ok', 'email': 'a@b.com', 'senha': 'curta1'}, 'mínimo 10'),
    ({'nome': 'Ok', 'email': 'a@b.com', 'senha': 'somenteletras'}, 'letras e números'),
    ({'nome': 'Ok', 'email': 'a@b.com', 'senha': '1234567890123'}, 'letras e números'),
    ({'nome': 'Ok', 'email': 'a@b.com', 'senha': 'a1' * 70}, 'máximo 128'),
    ({'nome': 'Ok', 'email': 'a@b.com', 'senha': ['lista']}, 'mínimo 10'),
])
def test_setup_valida_dados(anon, corpo, trecho):
    r = anon.post('/api/auth/setup', corpo)
    assert r.status_code == 400 and trecho in r.get_json()['erro']
    assert anon.get('/api/auth/estado').get_json() == {'configurado': False}      # nada foi criado


def test_setup_ignora_campos_extras(anon):
    anon.post('/api/auth/setup', {**SETUP, 'perfil': 'aluno', 'principal': 0, 'status': 'bloqueado'})
    u = anon.get('/api/auth/eu').get_json()['usuario']
    assert u['perfil'] == 'admin' and u['principal'] and u['status'] == 'ativo'


def test_apenas_um_principal_mesmo_com_corrida(app, anon):
    """O INSERT é condicional e o banco tem índice único: duas criações 'simultâneas' geram um só principal."""
    repo = app.extensions['repo']
    assert repo.criar_principal('A', 'a@x.com', 'h') is not None
    assert repo.criar_principal('B', 'b@x.com', 'h') is None
    with pytest.raises(DbIntegrityError):       # e mesmo forçando SQL direto o índice parcial impede o segundo
        repo.db.execute("INSERT INTO usuarios(nome,email,senha,perfil,principal) VALUES('C','c@x.com','h','admin',1)")
    assert repo.contar_usuarios() == 1


# ------------------------------------------------------------ login
def test_login_ok_e_dados_devolvidos(app, admin):
    c = Cli(app, ip='10.0.0.60')
    r = c.entrar('ADMIN@escola.com')                       # e-mail é case-insensitive
    assert r.status_code == 200
    j = r.get_json()
    assert j['usuario']['email'] == 'admin@escola.com' and j['csrf']
    assert 'senha' not in j['usuario'] and 'scrypt' not in r.get_data(as_text=True)
    assert c.get('/api/auth/eu').get_json()['usuario']['perfil'] == 'admin'


def test_login_falha_nao_revela_se_o_email_existe(admin, anon):
    a = anon.post('/api/auth/login', {'email': 'admin@escola.com', 'senha': 'errada12345'})
    b = anon.post('/api/auth/login', {'email': 'ninguem@escola.com', 'senha': 'errada12345'})
    assert a.status_code == b.status_code == 401
    assert a.get_json() == b.get_json() == {'erro': 'E-mail ou senha incorretos.'}
    assert not anon.cookie()


@pytest.mark.parametrize('corpo', [{}, {'email': None, 'senha': None}, {'email': ['x'], 'senha': {'a': 1}},
                                   {'email': 'admin@escola.com'}, {'email': 'admin@escola.com', 'senha': 12345}])
def test_login_entradas_estranhas_nao_quebram(admin, anon, corpo):
    assert anon.post('/api/auth/login', corpo).status_code == 401


def test_senha_guardada_com_hash_scrypt_e_nunca_exposta(app, admin, criar):
    criar('aluno', 'xa@escola.com')
    rows = app.extensions['repo'].db.execute('SELECT senha FROM usuarios').rows
    assert rows and all(r['senha'].startswith('scrypt:') and SENHA not in r['senha'] for r in rows)
    for url in ('/api/usuarios', '/api/auth/eu', '/api/logs'):
        txt = admin.get(url).get_data(as_text=True)
        assert 'scrypt' not in txt and SENHA not in txt


def test_bloqueio_por_tentativas_ip(admin, anon):
    for _ in range(8):
        assert anon.post('/api/auth/login', {'email': 'x@y.com', 'senha': 'zzzzzzzzzz1'}).status_code == 401
    # a 9ª é barrada ate com a senha CERTA
    assert anon.post('/api/auth/login', {'email': 'admin@escola.com', 'senha': SENHA}).status_code == 429
    assert Cli(anon.app, ip='10.9.9.9').post('/api/auth/login', {'email': 'admin@escola.com', 'senha': SENHA}
                                             ).status_code == 200      # outro IP não é afetado


def test_bloqueio_por_tentativas_no_mesmo_email_mesmo_trocando_de_ip(admin, app):
    for n in range(20):                      # 20 falhas vindas de 3 IPs diferentes (cada um abaixo do limite)
        c = Cli(app, ip=f'10.1.0.{n % 3}')
        assert c.post('/api/auth/login', {'email': 'admin@escola.com', 'senha': 'errada12345'}).status_code == 401
    assert Cli(app, ip='10.1.0.77').post('/api/auth/login', {'email': 'admin@escola.com', 'senha': SENHA}
                                         ).status_code == 429


# ------------------------------------------------------------ cookie e sessão
def test_cookie_de_sessao_seguro(admin):
    r = admin.post('/api/auth/login', {'email': 'admin@escola.com', 'senha': SENHA},
                   headers={'X-Forwarded-Proto': 'https'})
    sc = r.headers['Set-Cookie']
    assert sc.startswith('forum_sid=') and 'HttpOnly' in sc and 'SameSite=Strict' in sc and 'Path=/api' in sc
    assert 'Secure' in sc
    assert 'token' not in r.get_data(as_text=True).lower()          # o identificador NÃO vai no corpo/JS


def test_cookie_sem_secure_em_http_local(admin):
    sc = admin.post('/api/auth/login', {'email': 'admin@escola.com', 'senha': SENHA}).headers['Set-Cookie']
    assert 'HttpOnly' in sc and 'Secure' not in sc


def test_banco_guarda_so_o_hmac_da_sessao(app, admin):
    token = admin.cookie()
    ids = [r['id'] for r in app.extensions['repo'].db.execute('SELECT id FROM sessoes').rows]
    assert ids and token not in ids and all(len(i) == 64 for i in ids)


def test_cookie_forjado_ou_adulterado_e_recusado(app, admin):
    for valor in ('', 'abc', admin.cookie() + 'x', admin.cookie()[:-2], 'A' * 43):
        c = Cli(app)
        c.c.set_cookie('forum_sid', valor, path='/api')
        assert c.get('/api/auth/eu').status_code == 401, valor


def test_logout_invalida_a_sessao_no_servidor(app, admin):
    roubado = admin.cookie()
    assert admin.post('/api/auth/logout').status_code == 200
    assert admin.get('/api/auth/eu').status_code == 401
    copia = Cli(app)                                    # quem copiou o cookie antes do logout também perde acesso
    copia.c.set_cookie('forum_sid', roubado, path='/api')
    assert copia.get('/api/auth/eu').status_code == 401


def test_cada_login_gera_nova_sessao_independente(app, admin):
    outro = Cli(app, ip='10.0.0.61')
    outro.entrar('admin@escola.com')
    assert outro.cookie() != admin.cookie()
    outro.post('/api/auth/logout')
    assert admin.get('/api/auth/eu').status_code == 200          # sair num aparelho não derruba o outro


def test_sessao_expira_por_tempo_absoluto(app, admin):
    app.extensions['repo'].db.execute('UPDATE sessoes SET expira_em=?', (time.time() - 1,))
    r = admin.get('/api/auth/eu')
    assert r.status_code == 401 and 'forum_sid=;' in r.headers['Set-Cookie']
    assert app.extensions['repo'].db.execute('SELECT COUNT(*) AS n FROM sessoes').rows[0]['n'] == 0


def test_sessao_expira_por_inatividade(app, admin):
    app.extensions['repo'].db.execute('UPDATE sessoes SET ultimo_uso=?', (time.time() - app.config['SESSION_IDLE'] - 5,))
    assert admin.get('/api/auth/eu').status_code == 401


def test_uso_renova_o_ultimo_acesso(app, admin):
    db = app.extensions['repo'].db
    antigo = time.time() - 1000
    db.execute('UPDATE sessoes SET ultimo_uso=?', (antigo,))
    assert admin.get('/api/auth/eu').status_code == 200
    assert db.execute('SELECT ultimo_uso FROM sessoes').rows[0]['ultimo_uso'] > antigo + 900


# ------------------------------------------------------------ CSRF / origem
def test_csrf_obrigatorio_em_acoes_que_alteram_dados(admin):
    corpo = {'nome': 'Grafos'}
    assert admin.post('/api/tags', corpo, csrf=False).status_code == 403
    assert admin.post('/api/tags', corpo, headers={'X-CSRF-Token': 'errado'}).status_code == 403
    assert admin.delete('/api/tags/grafos', csrf=False).status_code == 403
    assert admin.post('/api/usuarios', {}, csrf=False).status_code == 403
    assert admin.get('/api/tags').get_json() == []                     # nada foi criado
    assert admin.post('/api/tags', corpo).status_code == 201           # com o token certo funciona
    assert admin.get('/api/tags', csrf=False).status_code == 200       # leitura não exige


def test_csrf_de_uma_sessao_nao_vale_em_outra(app, admin):
    outro = Cli(app, ip='10.0.0.62')
    outro.entrar('admin@escola.com')
    assert admin.post('/api/tags', {'nome': 'X'}, headers={'X-CSRF-Token': outro.csrf}).status_code == 403


def test_origem_de_outro_site_e_barrada(admin):
    assert admin.post('/api/tags', {'nome': 'A'}, headers={'Origin': 'https://site-malicioso.com'}).status_code == 403
    assert admin.post('/api/tags', {'nome': 'A'}, headers={'Origin': 'null'}).status_code == 403
    assert admin.post('/api/tags', {'nome': 'A'}, headers={'Origin': 'http://localhost'}).status_code == 201  # mesma origem
    assert admin.post('/api/tags', {'nome': 'B'}, headers={'Origin': 'http://localhost:5500'}).status_code == 201  # dev


def test_origem_externa_so_com_cors_configurado(cfg):
    from forum import create_app
    app = create_app({**cfg, 'CORS_ORIGINS': 'https://front.exemplo.com', 'IS_VERCEL': True})
    c = Cli(app)
    assert c.post('/api/auth/setup', SETUP, headers={'Origin': 'https://front.exemplo.com'}).status_code == 201
    assert c.post('/api/tags', {'nome': 'A'}, headers={'Origin': 'http://localhost:5500'}).status_code == 403
    r = c.get('/api/tags', headers={'Origin': 'https://front.exemplo.com'})
    assert r.headers['Access-Control-Allow-Origin'] == 'https://front.exemplo.com'
    assert r.headers['Access-Control-Allow-Credentials'] == 'true'
    assert 'Access-Control-Allow-Origin' not in c.get('/api/tags', headers={'Origin': 'https://evil.com'}).headers


def test_cabecalhos_de_seguranca(admin):
    r = admin.get('/api/tags')
    assert r.headers['Cache-Control'] == 'no-store' and r.headers['X-Frame-Options'] == 'DENY'
    assert r.headers['X-Content-Type-Options'] == 'nosniff'


# ------------------------------------------------------------ troca da própria senha
def test_trocar_senha(app, admin):
    outro = Cli(app, ip='10.0.0.63')
    outro.entrar('admin@escola.com')                    # segundo dispositivo
    assert admin.post('/api/auth/senha', {'senha_atual': 'errada12345', 'nova_senha': 'NovaSenha2024x'}
                      ).status_code == 403
    assert admin.post('/api/auth/senha', {'senha_atual': SENHA, 'nova_senha': 'curta'}).status_code == 400
    assert admin.post('/api/auth/senha', {'senha_atual': SENHA, 'nova_senha': 'NovaSenha2024x'}).status_code == 200
    assert admin.get('/api/auth/eu').status_code == 200            # este continua logado
    assert outro.get('/api/auth/eu').status_code == 401            # o outro dispositivo foi derrubado
    fresco = Cli(app, ip='10.0.0.64')
    assert fresco.entrar('admin@escola.com', SENHA).status_code == 401
    assert fresco.entrar('admin@escola.com', 'NovaSenha2024x').status_code == 200


def test_logs_registram_eventos_de_acesso(admin, anon):
    anon.post('/api/auth/login', {'email': 'admin@escola.com', 'senha': 'errada12345'})
    anon.post('/api/auth/login', {'email': 'admin@escola.com', 'senha': SENHA})
    logs = admin.get('/api/logs').get_json()
    acoes = {(l['usuario'], l['acao'], l['resultado']) for l in logs}
    assert ('admin@escola.com', 'login', 'falhou') in acoes and ('admin@escola.com', 'login', 'ok') in acoes
    assert ('admin@escola.com', 'setup', 'administrador principal criado') in acoes
    assert SENHA not in str(logs)

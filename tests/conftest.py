import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from forum import create_app  # noqa: E402
from tests.mock_turso import TOKEN, MockTurso  # noqa: E402

SENHA = 'senhaforte123'


@pytest.fixture(autouse=True)
def hash_rapido(monkeypatch):
    """scrypt com custo mínimo só nos testes (o formato do hash é o mesmo; produção usa o padrão do Werkzeug)."""
    from werkzeug.security import generate_password_hash
    monkeypatch.setattr('forum.auth.generate_password_hash', lambda s: generate_password_hash(s, method='scrypt:1024:8:1'))


@pytest.fixture()
def mock_turso(tmp_path):
    m = MockTurso(str(tmp_path / 'turso_mock.db'))
    yield m
    m.close()


def _cfg(tmp_path, driver, mock):
    cfg = {'DATA_DIR': str(tmp_path), 'SECRET_KEY': 'teste',
           'LOCAL_DB_PATH': str(tmp_path / 'forum.db'), 'TURSO_DATABASE_URL': '', 'TURSO_AUTH_TOKEN': ''}
    if driver == 'turso':
        cfg.update(TURSO_DATABASE_URL=mock.base_http, TURSO_AUTH_TOKEN=TOKEN, AUTO_INIT_DB=True)
    return cfg


@pytest.fixture(params=['sqlite', 'turso'])
def cfg(request, tmp_path, mock_turso):
    """Roda cada teste de API nos dois drivers (SQLite local e Turso simulado via HTTP)."""
    return _cfg(tmp_path, request.param, mock_turso)


class Cli:
    """Navegador de mentira: guarda o cookie de sessão (via test_client) e manda o token CSRF como o front faz."""

    def __init__(self, app, ip='10.0.0.1'):
        self.app, self.c, self.ip = app, app.test_client(), ip
        self.csrf = None
        self.usuario = None

    def req(self, metodo, url, json=None, csrf=True, headers=None, **kw):
        h = dict(headers or {})
        if csrf and self.csrf and 'X-CSRF-Token' not in h:
            h['X-CSRF-Token'] = self.csrf
        return self.c.open(url, method=metodo, json=json, headers=h,
                           environ_overrides={'REMOTE_ADDR': self.ip}, **kw)

    def get(self, url, **kw):
        return self.req('GET', url, **kw)

    def post(self, url, json=None, **kw):
        return self.req('POST', url, json=json if json is not None else {}, **kw)

    def patch(self, url, json=None, **kw):
        return self.req('PATCH', url, json=json if json is not None else {}, **kw)

    def delete(self, url, **kw):
        return self.req('DELETE', url, **kw)

    def entrar(self, email, senha=SENHA):
        r = self.post('/api/auth/login', {'email': email, 'senha': senha})
        if r.status_code == 200:
            self.csrf, self.usuario = r.get_json()['csrf'], r.get_json()['usuario']
        return r

    def cookie(self):
        c = self.c.get_cookie('forum_sid', path='/api')
        return c.value if c else None


@pytest.fixture()
def app(cfg):
    a = create_app(cfg)
    a.config['TESTING'] = True
    return a


@pytest.fixture()
def anon(app):
    return Cli(app, ip='10.0.0.99')


@pytest.fixture()
def admin(app):
    """Administrador PRINCIPAL, criado pelo fluxo de primeiro acesso."""
    c = Cli(app, ip='10.0.0.2')
    r = c.post('/api/auth/setup', {'nome': 'Admin Principal', 'email': 'admin@escola.com', 'senha': SENHA})
    assert r.status_code == 201, r.get_json()
    c.csrf, c.usuario = r.get_json()['csrf'], r.get_json()['usuario']
    return c


@pytest.fixture()
def criar(app, admin):
    """criar(perfil, email, verificar=True) -> Cli já autenticado, usuário criado pelo administrador."""
    def _criar(perfil, email, nome=None, verificar=True, entrar=True):
        r = admin.post('/api/usuarios', {'nome': nome or email.split('@')[0].title(), 'email': email,
                                         'senha': SENHA, 'perfil': perfil})
        assert r.status_code == 201, r.get_json()
        uid = r.get_json()['id']
        if perfil == 'professor' and verificar:
            assert admin.post(f'/api/usuarios/{uid}/verificar').status_code == 200
        c = Cli(app, ip='10.0.0.%d' % (10 + uid))
        c.id = uid
        if entrar:
            assert c.entrar(email).status_code == 200
        return c
    return _criar


@pytest.fixture()
def admin2(criar):
    return criar('admin', 'admin2@escola.com')


@pytest.fixture()
def prof(criar):
    return criar('professor', 'prof@escola.com')


@pytest.fixture()
def aluno(criar):
    return criar('aluno', 'aluno@escola.com')

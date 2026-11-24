import pytest

from forum.db import DbError, DbIntegrityError, SqliteDb, TursoDb
from forum.repo import SCHEMA, Repositorio
from tests.mock_turso import TOKEN


@pytest.fixture(params=['sqlite', 'turso'])
def db(request, tmp_path, mock_turso):
    if request.param == 'sqlite':
        return SqliteDb(str(tmp_path / 'x.db'))
    return TursoDb(mock_turso.url.replace('libsql://', 'http://'), TOKEN)


def test_execute_tipos_e_last_id(db):
    db.execute('CREATE TABLE t(id INTEGER PRIMARY KEY AUTOINCREMENT, s TEXT, n INTEGER, f REAL)')
    r = db.execute('INSERT INTO t(s, n, f) VALUES(?,?,?)', ('olá ã', 7, 1.5))
    assert r.last_id == 1
    db.execute('INSERT INTO t(s, n, f) VALUES(?,?,?)', (None, True, 2.0))
    rows = db.execute('SELECT * FROM t ORDER BY id').rows
    assert rows[0] == {'id': 1, 's': 'olá ã', 'n': 7, 'f': 1.5}
    assert rows[1]['s'] is None and rows[1]['n'] == 1


def test_batch_confirma_tudo(db):
    db.execute('CREATE TABLE t(k TEXT PRIMARY KEY)')
    res = db.batch([('INSERT INTO t VALUES(?)', ('a',)), ('INSERT INTO t VALUES(?)', ('b',)),
                    ('SELECT COUNT(*) AS n FROM t', ())])
    assert res[2].rows[0]['n'] == 2


def test_batch_atomico_rollback_e_erro_de_integridade(db):
    db.execute('CREATE TABLE t(k TEXT PRIMARY KEY)')
    with pytest.raises(DbIntegrityError):
        db.batch([('INSERT INTO t VALUES(?)', ('a',)), ('INSERT INTO t VALUES(?)', ('a',))])
    assert db.execute('SELECT COUNT(*) AS n FROM t').rows[0]['n'] == 0     # nada foi gravado
    with pytest.raises(DbError):
        db.execute('SELECT * FROM tabela_inexistente')


def test_batch_vazio(db):
    assert db.batch([]) == []


def test_schema_idempotente_e_seed(db):
    repo = Repositorio(db)
    repo.inicializar()
    repo.inicializar()
    assert repo.contar('membros') == 4
    assert repo.saude()['esquema_ok']


def test_turso_token_invalido_e_url_invalida(mock_turso):
    with pytest.raises(DbError, match='401'):
        TursoDb(mock_turso.url.replace('libsql://', 'http://'), 'errado').ping()
    with pytest.raises(DbError):
        TursoDb('nao-e-url', 'x')
    with pytest.raises(DbError, match='Falha ao contatar'):
        TursoDb('http://127.0.0.1:9', TOKEN, timeout=1).ping()      # porta fechada


def test_turso_converte_libsql_para_https():
    assert TursoDb('libsql://meu-db-org.turso.io', 't').base == 'https://meu-db-org.turso.io'


def test_health_sem_esquema_retorna_503(tmp_path):
    from forum import create_app
    app = create_app({'DATA_DIR': str(tmp_path), 'SECRET_KEY': 'k', 'CODIGO_ADMIN': 'c',
                      'LOCAL_DB_PATH': str(tmp_path / 'v.db'), 'TURSO_DATABASE_URL': '', 'AUTO_INIT_DB': False})
    r = app.test_client().get('/api/health')
    assert r.status_code == 503 and r.get_json()['status'] == 'esquema_pendente'


def test_health_turso_inacessivel_retorna_503(tmp_path):
    from forum import create_app
    app = create_app({'DATA_DIR': str(tmp_path), 'SECRET_KEY': 'k', 'CODIGO_ADMIN': 'c',
                      'TURSO_DATABASE_URL': 'http://127.0.0.1:9', 'TURSO_AUTH_TOKEN': 'x', 'AUTO_INIT_DB': False})
    r = app.test_client().get('/api/health')
    assert r.status_code == 503 and r.get_json()['db']['conectado'] is False
    c = app.test_client()
    c.set_cookie('forum_sid', 'qualquer', path='/api')               # a checagem da sessão já precisa do banco
    r2 = c.get('/api/tags')
    assert r2.status_code == 503 and 'erro' in r2.get_json()        # DbError -> 503 JSON, não 500
    assert app.test_client().post('/api/auth/login', json={'email': 'a@b.com', 'senha': 'x'}).status_code == 503


def test_migracao_dos_admins_do_fluxo_antigo(tmp_path):
    """Bancos já em produção têm a tabela `admins`: as contas viram administradores (o mais antigo é o principal),
    a senha continua valendo e a tabela antiga some."""
    from werkzeug.security import generate_password_hash
    from forum import create_app
    from tests.conftest import Cli
    cfg = {'DATA_DIR': str(tmp_path), 'SECRET_KEY': 'k', 'LOCAL_DB_PATH': str(tmp_path / 'velho.db'),
           'TURSO_DATABASE_URL': '', 'AUTO_INIT_DB': False}
    db = SqliteDb(cfg['LOCAL_DB_PATH'])
    db.execute('CREATE TABLE admins(id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL, nome TEXT, senha TEXT NOT NULL)')
    db.execute('INSERT INTO admins(email, nome, senha) VALUES(?,?,?)',
               ('Antigo@Escola.com', 'Admin Antigo', generate_password_hash('senhaantiga123', method='pbkdf2:sha256')))
    db.execute('INSERT INTO admins(email, nome, senha) VALUES(?,?,?)',
               ('segundo@escola.com', None, generate_password_hash('outrasenha123')))
    repo = Repositorio(db)
    repo.inicializar()
    repo.inicializar()                                           # idempotente
    assert 'admins' not in repo.tabelas_existentes() and repo.saude()['esquema_ok']
    us = repo.listar_usuarios()
    assert [(u['email'], u['perfil'], bool(u['principal'])) for u in us] == [
        ('antigo@escola.com', 'admin', True), ('segundo@escola.com', 'admin', False)]
    assert us[1]['nome'] == 'segundo@escola.com'
    app = create_app({**cfg, 'AUTO_INIT_DB': True})
    c = Cli(app)
    assert c.entrar('antigo@escola.com', 'senhaantiga123').status_code == 200
    assert c.get('/api/auth/estado').get_json() == {'configurado': True}      # não oferece novo primeiro acesso
    assert Cli(app).post('/api/auth/setup', {'nome': 'X', 'email': 'x@x.com', 'senha': 'senhaforte123'}).status_code == 409


def test_banco_novo_nao_cria_tabela_admins(db):
    repo = Repositorio(db)
    repo.inicializar()
    assert 'admins' not in repo.tabelas_existentes()
    assert {'usuarios', 'sessoes'} <= set(repo.tabelas_existentes())

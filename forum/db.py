"""Drivers de banco com a MESMA interface:

    db.execute(sql, params) -> Resultado
    db.batch([(sql, params), ...]) -> [Resultado, ...]   # transação atômica (tudo ou nada)
    db.ping() -> dict

* SqliteDb: arquivo local (desenvolvimento/testes). Biblioteca padrão.
* TursoDb : Turso (libSQL) pela API HTTP oficial (/v2/pipeline, protocolo Hrana). Só biblioteca padrão,
            sem dependência nativa — roda bem em função serverless da Vercel.
Sem conexão persistente: cada chamada é independente (modelo serverless).
"""
import base64
import json
import sqlite3
import urllib.error
import urllib.request
from pathlib import Path


class DbError(Exception):
    pass


class DbIntegrityError(DbError):
    """Violação de UNIQUE/constraint."""


class Resultado:
    __slots__ = ('rows', 'last_id', 'rowcount')

    def __init__(self, rows=None, last_id=None, rowcount=0):
        self.rows = rows or []
        self.last_id = last_id
        self.rowcount = rowcount


def _classificar(msg):
    m = str(msg).lower()
    return DbIntegrityError(msg) if ('unique' in m or 'constraint' in m) else DbError(msg)


# ============================================================ SQLite local
class SqliteDb:
    modo = 'sqlite'

    def __init__(self, caminho):
        self.caminho = str(caminho)
        if self.caminho != ':memory:':
            Path(self.caminho).parent.mkdir(parents=True, exist_ok=True)

    def _conectar(self):
        c = sqlite3.connect(self.caminho, timeout=10)
        c.row_factory = sqlite3.Row
        return c

    @staticmethod
    def _rodar(c, sql, params):
        cur = c.execute(sql, tuple(params))
        rows = [dict(r) for r in cur.fetchall()] if cur.description else []
        return Resultado(rows, cur.lastrowid, cur.rowcount)

    def execute(self, sql, params=()):
        return self.batch([(sql, params)])[0]

    def batch(self, stmts):
        if not stmts:
            return []
        c = self._conectar()
        try:
            out = [self._rodar(c, s, p) for s, p in stmts]
            c.commit()
            return out
        except sqlite3.IntegrityError as e:
            c.rollback()
            raise DbIntegrityError(str(e)) from e
        except sqlite3.Error as e:
            c.rollback()
            raise DbError(str(e)) from e
        finally:
            c.close()

    def ping(self):
        r = self.execute('SELECT sqlite_version() AS v').rows[0]
        return {'modo': self.modo, 'versao': r['v']}


# ============================================================ Turso (HTTP)
def _arg(v):
    if v is None:
        return {'type': 'null'}
    if isinstance(v, bool):
        return {'type': 'integer', 'value': str(int(v))}
    if isinstance(v, int):
        return {'type': 'integer', 'value': str(v)}
    if isinstance(v, float):
        return {'type': 'float', 'value': v}
    if isinstance(v, (bytes, bytearray)):
        return {'type': 'blob', 'base64': base64.b64encode(bytes(v)).decode()}
    return {'type': 'text', 'value': str(v)}


def _valor(c):
    t = c.get('type')
    if t == 'null':
        return None
    if t == 'integer':
        return int(c['value'])
    if t == 'float':
        return float(c['value'])
    if t == 'blob':
        return base64.b64decode(c.get('base64', ''))
    return c.get('value')


def _stmt(sql, params):
    return {'sql': sql, 'args': [_arg(p) for p in params]}


def _resultado(r):
    cols = [c.get('name') for c in r.get('cols', [])]
    rows = [dict(zip(cols, (_valor(c) for c in linha))) for linha in r.get('rows', [])]
    last = r.get('last_insert_rowid')
    return Resultado(rows, int(last) if last not in (None, '') else None, r.get('affected_row_count') or 0)


class TursoDb:
    modo = 'turso'

    def __init__(self, url, token, timeout=10):
        url = (url or '').strip().rstrip('/')
        for pref in ('libsql://', 'wss://', 'ws://'):
            if url.startswith(pref):
                url = 'https://' + url[len(pref):]
        if not url.startswith(('https://', 'http://')):
            raise DbError('TURSO_DATABASE_URL inválida (esperado libsql://nome-org.turso.io).')
        self.base = url
        self.token = (token or '').strip()
        self.timeout = timeout

    def _pipeline(self, requests):
        corpo = json.dumps({'requests': requests + [{'type': 'close'}]}).encode()
        req = urllib.request.Request(self.base + '/v2/pipeline', data=corpo, method='POST', headers={
            'Content-Type': 'application/json',
            **({'Authorization': 'Bearer ' + self.token} if self.token else {})})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read().decode())['results']
        except urllib.error.HTTPError as e:
            detalhe = e.read().decode(errors='replace')[:200]
            raise DbError(f'Turso respondeu HTTP {e.code}: {detalhe}') from e
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError) as e:
            raise DbError(f'Falha ao contatar o Turso: {e}') from e

    def execute(self, sql, params=()):
        res = self._pipeline([{'type': 'execute', 'stmt': _stmt(sql, params)}])[0]
        if res.get('type') == 'error':
            raise _classificar(res['error'].get('message', 'erro'))
        return _resultado(res['response']['result'])

    def batch(self, stmts):
        """BEGIN + comandos encadeados por condição + COMMIT; ROLLBACK se algum falhar."""
        if not stmts:
            return []
        n = len(stmts)
        passos = [{'stmt': {'sql': 'BEGIN'}}]
        for i, (sql, params) in enumerate(stmts, start=1):
            passos.append({'stmt': _stmt(sql, params), 'condition': {'type': 'ok', 'step': i - 1}})
        passos.append({'stmt': {'sql': 'COMMIT'}, 'condition': {'type': 'ok', 'step': n}})
        passos.append({'stmt': {'sql': 'ROLLBACK'},
                       'condition': {'type': 'not', 'cond': {'type': 'ok', 'step': n + 1}}})
        res = self._pipeline([{'type': 'batch', 'batch': {'steps': passos}}])[0]
        if res.get('type') == 'error':
            raise _classificar(res['error'].get('message', 'erro'))
        r = res['response']['result']
        erros = r.get('step_errors') or []
        for e in erros[:n + 2]:
            if e:
                raise _classificar(e.get('message', 'erro'))
        return [_resultado(x) for x in (r.get('step_results') or [])[1:n + 1]]

    def ping(self):
        r = self.execute('SELECT sqlite_version() AS v').rows[0]
        return {'modo': self.modo, 'versao': r['v'], 'host': self.base.split('://', 1)[1]}


def criar_db(cfg):
    if cfg.get('TURSO_DATABASE_URL'):
        return TursoDb(cfg['TURSO_DATABASE_URL'], cfg.get('TURSO_AUTH_TOKEN'))
    return SqliteDb(cfg['LOCAL_DB_PATH'])

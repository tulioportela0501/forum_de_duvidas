"""Servidor HTTP que imita o endpoint /v2/pipeline do Turso (protocolo Hrana) sobre um SQLite local.
Serve para testar o driver TursoDb (codificação, batch transacional com condições, erros, auth) sem rede."""
import json
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

TOKEN = 'token-de-teste'


def _enc(v):
    if v is None:
        return {'type': 'null'}
    if isinstance(v, int):
        return {'type': 'integer', 'value': str(v)}
    if isinstance(v, float):
        return {'type': 'float', 'value': v}
    return {'type': 'text', 'value': str(v)}


def _dec(a):
    t = a['type']
    if t == 'null':
        return None
    if t == 'integer':
        return int(a['value'])
    if t == 'float':
        return float(a['value'])
    return a['value']


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _responder(self, codigo, corpo):
        dados = json.dumps(corpo).encode()
        self.send_response(codigo)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def _stmt(self, st):
        cur = self.server.conn.execute(st['sql'], [_dec(a) for a in st.get('args', [])])
        cols = [{'name': d[0]} for d in cur.description] if cur.description else []
        rows = [[_enc(v) for v in r] for r in cur.fetchall()] if cur.description else []
        return {'cols': cols, 'rows': rows, 'affected_row_count': max(cur.rowcount, 0),
                'last_insert_rowid': str(cur.lastrowid) if cur.lastrowid else None}

    def _cond(self, c, res, errs):
        if c is None:
            return True
        t = c['type']
        if t == 'ok':
            return res[c['step']] is not None and errs[c['step']] is None
        if t == 'error':
            return errs[c['step']] is not None
        if t == 'not':
            return not self._cond(c['cond'], res, errs)
        raise AssertionError('condição não suportada: ' + t)

    def do_POST(self):
        self.server.requisicoes += 1
        if self.path != '/v2/pipeline':
            return self._responder(404, {'error': 'not found'})
        if self.headers.get('Authorization') != 'Bearer ' + TOKEN:
            return self._responder(401, {'error': 'Unauthorized'})
        corpo = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        saida = []
        for rq in corpo['requests']:
            if rq['type'] == 'close':
                saida.append({'type': 'ok', 'response': {'type': 'close'}})
            elif rq['type'] == 'execute':
                try:
                    saida.append({'type': 'ok', 'response': {'type': 'execute', 'result': self._stmt(rq['stmt'])}})
                except sqlite3.Error as e:
                    saida.append({'type': 'error', 'error': {'message': str(e)}})
            elif rq['type'] == 'batch':
                steps = rq['batch']['steps']
                res, errs = [None] * len(steps), [None] * len(steps)
                for i, s in enumerate(steps):
                    if not self._cond(s.get('condition'), res, errs):
                        continue
                    try:
                        res[i] = self._stmt(s['stmt'])
                    except sqlite3.Error as e:
                        errs[i] = {'message': str(e)}
                saida.append({'type': 'ok', 'response': {'type': 'batch',
                              'result': {'step_results': res, 'step_errors': errs}}})
        self._responder(200, {'baton': None, 'base_url': None, 'results': saida})


class MockTurso:
    def __init__(self, caminho):
        self.srv = HTTPServer(('127.0.0.1', 0), _Handler)
        self.srv.conn = sqlite3.connect(caminho, check_same_thread=False, isolation_level=None)
        self.srv.requisicoes = 0
        self.thread = threading.Thread(target=self.srv.serve_forever, daemon=True)
        self.thread.start()
        self.url = 'libsql://127.0.0.1:%d' % self.srv.server_port   # TursoDb troca libsql:// por https://

    @property
    def base_http(self):
        return 'http://127.0.0.1:%d' % self.srv.server_port

    def close(self):
        self.srv.shutdown()
        self.srv.conn.close()

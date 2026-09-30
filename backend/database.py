"""Camada de persistência (SQLite). A AVL fica em memória e é reconstruída a partir daqui.

Para migrar para PostgreSQL/MySQL basta reescrever esta classe mantendo os mesmos métodos.
"""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

MEMBROS_INICIAIS = [
    'Hugo Leonardo Ribeiro Salomão',
    'Isaque Martins Costa',
    'Marco Túlio Chaves Portela',
    'Wanderson Henrique Reis Luz',
]


def agora():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


class Repositorio:
    def __init__(self, caminho):
        self.caminho = caminho
        self._criar_tabelas()

    @contextmanager
    def conexao(self):
        c = sqlite3.connect(self.caminho, timeout=10)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise
        finally:
            c.close()

    def _criar_tabelas(self):
        with self.conexao() as c:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS tags(
                    key TEXT PRIMARY KEY, display_name TEXT NOT NULL,
                    description TEXT DEFAULT '', usage_count INTEGER DEFAULT 0, criado_em TEXT);
                CREATE TABLE IF NOT EXISTS topicos(
                    id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT NOT NULL, descricao TEXT DEFAULT '',
                    autor TEXT DEFAULT '', tags TEXT DEFAULT '[]', criado_em TEXT,
                    respostas INTEGER DEFAULT 0, visualizacoes INTEGER DEFAULT 0);
                CREATE TABLE IF NOT EXISTS membros(
                    id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE NOT NULL, funcao TEXT DEFAULT 'Integrante');
                CREATE TABLE IF NOT EXISTS logs(
                    id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, usuario TEXT, acao TEXT, resultado TEXT);
                CREATE TABLE IF NOT EXISTS rotacoes(
                    id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, tipo TEXT, no TEXT);
                CREATE TABLE IF NOT EXISTS admins(
                    id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL, nome TEXT, senha TEXT NOT NULL);
            """)
            if c.execute('SELECT COUNT(*) FROM membros').fetchone()[0] == 0:
                c.executemany('INSERT INTO membros(nome) VALUES(?)', [(n,) for n in MEMBROS_INICIAIS])

    # ---- tags
    def listar_tags(self):
        with self.conexao() as c:
            return [dict(r) for r in c.execute('SELECT * FROM tags ORDER BY criado_em, rowid')]

    def salvar_tag(self, chave, nome, descricao, uso):
        with self.conexao() as c:
            c.execute("""INSERT INTO tags(key, display_name, description, usage_count, criado_em)
                         VALUES(?,?,?,?,?)
                         ON CONFLICT(key) DO UPDATE SET usage_count=excluded.usage_count,
                         description=excluded.description""", (chave, nome, descricao, uso, agora()))

    def remover_tag(self, chave):
        with self.conexao() as c:
            c.execute('DELETE FROM tags WHERE key=?', (chave,))

    # ---- tópicos
    @staticmethod
    def _topico(r):
        d = dict(r)
        d['tags'] = json.loads(d['tags'] or '[]')
        return d

    def criar_topico(self, titulo, descricao, autor, tags):
        with self.conexao() as c:
            cur = c.execute('INSERT INTO topicos(titulo, descricao, autor, tags, criado_em) VALUES(?,?,?,?,?)',
                            (titulo, descricao, autor, json.dumps(tags, ensure_ascii=False), agora()))
            return self._topico(c.execute('SELECT * FROM topicos WHERE id=?', (cur.lastrowid,)).fetchone())

    def listar_topicos(self):
        with self.conexao() as c:
            return [self._topico(r) for r in c.execute('SELECT * FROM topicos ORDER BY id DESC')]

    # ---- membros
    def listar_membros(self):
        with self.conexao() as c:
            membros = [dict(r) for r in c.execute('SELECT * FROM membros ORDER BY nome')]
            autores = [r['autor'] for r in c.execute('SELECT autor FROM topicos')]
        for m in membros:
            alvo = m['nome'].casefold()
            m['n_duvidas'] = sum(1 for a in autores if (a or '').casefold() == alvo)
        return membros

    # ---- logs e rotações
    def registrar_log(self, usuario, acao, resultado):
        with self.conexao() as c:
            c.execute('INSERT INTO logs(data, usuario, acao, resultado) VALUES(?,?,?,?)',
                      (agora(), usuario or 'anônimo', acao, resultado))

    def listar_logs(self, limite=200):
        with self.conexao() as c:
            return [dict(r) for r in c.execute('SELECT * FROM logs ORDER BY id DESC LIMIT ?', (limite,))]

    def registrar_rotacoes(self, eventos):
        with self.conexao() as c:
            c.executemany('INSERT INTO rotacoes(data, tipo, no) VALUES(?,?,?)',
                          [(agora(), e['tipo'], e['no']) for e in eventos])

    def resumo_rotacoes(self):
        por_tipo = {'LL': 0, 'RR': 0, 'LR': 0, 'RL': 0}
        with self.conexao() as c:
            for r in c.execute('SELECT tipo, COUNT(*) n FROM rotacoes GROUP BY tipo'):
                por_tipo[r['tipo']] = r['n']
        return {'total': sum(por_tipo.values()), 'por_tipo': por_tipo}

    # ---- administradores
    def criar_admin(self, email, nome, senha_hash):
        try:
            with self.conexao() as c:
                cur = c.execute('INSERT INTO admins(email, nome, senha) VALUES(?,?,?)', (email, nome, senha_hash))
                return cur.lastrowid
        except sqlite3.IntegrityError:
            return None

    def obter_admin(self, email):
        with self.conexao() as c:
            r = c.execute('SELECT * FROM admins WHERE email=?', (email,)).fetchone()
            return dict(r) if r else None

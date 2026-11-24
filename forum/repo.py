"""Repositório: SQL puro sobre o driver (SQLite local ou Turso). Sem estado em memória.

A AVL NÃO é persistida como árvore: o banco guarda as tags (fonte da verdade) e a árvore é reconstruída
a partir delas a cada requisição (ver service.py)."""
import json
import time
from datetime import datetime, timezone

MEMBROS_INICIAIS = [
    'Hugo Leonardo Ribeiro Salomão',
    'Isaque Martins Costa',
    'Marco Túlio Chaves Portela',
    'Wanderson Henrique Reis Luz',
]

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS tags(
        key TEXT PRIMARY KEY, display_name TEXT NOT NULL,
        description TEXT DEFAULT '', usage_count INTEGER DEFAULT 0, criado_em TEXT)""",
    """CREATE TABLE IF NOT EXISTS topicos(
        id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT NOT NULL, descricao TEXT DEFAULT '',
        autor TEXT DEFAULT '', tags TEXT DEFAULT '[]', criado_em TEXT,
        respostas INTEGER DEFAULT 0, visualizacoes INTEGER DEFAULT 0)""",
    """CREATE TABLE IF NOT EXISTS membros(
        id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE NOT NULL, funcao TEXT DEFAULT 'Integrante')""",
    """CREATE TABLE IF NOT EXISTS logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, usuario TEXT, acao TEXT, resultado TEXT)""",
    """CREATE TABLE IF NOT EXISTS rotacoes(
        id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, tipo TEXT, no TEXT)""",
    """CREATE TABLE IF NOT EXISTS usuarios(
        id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
        senha TEXT NOT NULL,
        perfil TEXT NOT NULL CHECK(perfil IN ('admin','professor','aluno')),
        status TEXT NOT NULL DEFAULT 'ativo' CHECK(status IN ('ativo','bloqueado')),
        verificado INTEGER NOT NULL DEFAULT 0, principal INTEGER NOT NULL DEFAULT 0,
        criado_em TEXT, criado_por INTEGER, verificado_em TEXT, verificado_por INTEGER, ultimo_login TEXT)""",
    # no máximo UM administrador principal (garantido pelo próprio banco, mesmo com cadastros simultâneos)
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_principal ON usuarios(principal) WHERE principal = 1",
    # sessões no servidor: guardamos só o HMAC do identificador (o cookie traz o valor original)
    """CREATE TABLE IF NOT EXISTS sessoes(
        id TEXT PRIMARY KEY, usuario_id INTEGER NOT NULL, csrf TEXT NOT NULL,
        criado_em REAL NOT NULL, ultimo_uso REAL NOT NULL, expira_em REAL NOT NULL, ip TEXT, agente TEXT)""",
    "CREATE INDEX IF NOT EXISTS idx_sessoes_usuario ON sessoes(usuario_id)",
    # limitador de requisições compartilhado entre instâncias serverless
    """CREATE TABLE IF NOT EXISTS limites(chave TEXT NOT NULL, ts REAL NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS idx_limites ON limites(chave, ts)",
    "CREATE TABLE IF NOT EXISTS respostas(id INTEGER PRIMARY KEY AUTOINCREMENT, topico_id INTEGER NOT NULL, autor TEXT NOT NULL, conteudo TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'publicada', criado_em TEXT)",
    "CREATE INDEX IF NOT EXISTS idx_respostas_topico ON respostas(topico_id, id)",
    "CREATE TABLE IF NOT EXISTS palavras_restritas(id INTEGER PRIMARY KEY AUTOINCREMENT, palavra TEXT UNIQUE NOT NULL, ativo INTEGER NOT NULL DEFAULT 1, criado_em TEXT)",
    "CREATE TABLE IF NOT EXISTS moderacao(id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT NOT NULL, item_id INTEGER NOT NULL, motivo TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pendente', criado_em TEXT, revisado_em TEXT, revisado_por TEXT)",
    "CREATE TABLE IF NOT EXISTS notificacoes(id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER NOT NULL, resposta_id INTEGER NOT NULL, topico_id INTEGER NOT NULL, autor_nome TEXT NOT NULL, lida INTEGER NOT NULL DEFAULT 0, criado_em TEXT)",
    "CREATE INDEX IF NOT EXISTS idx_notif_usuario ON notificacoes(usuario_id, lida, id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_notif_resposta ON notificacoes(resposta_id)",
    "CREATE TABLE IF NOT EXISTS grupos(id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL UNIQUE, descricao TEXT DEFAULT '', criado_em TEXT, criado_por TEXT)",
    "CREATE TABLE IF NOT EXISTS grupo_membros(grupo_id INTEGER NOT NULL, usuario_id INTEGER NOT NULL, PRIMARY KEY(grupo_id, usuario_id))",
    "CREATE TABLE IF NOT EXISTS curtidas(usuario_id INTEGER NOT NULL, alvo_tipo TEXT NOT NULL, alvo_id INTEGER NOT NULL, criado_em TEXT, PRIMARY KEY(usuario_id, alvo_tipo, alvo_id))",
    "CREATE INDEX IF NOT EXISTS idx_curtidas_alvo ON curtidas(alvo_tipo, alvo_id)",
    "CREATE TABLE IF NOT EXISTS reposts(usuario_id INTEGER NOT NULL, topico_id INTEGER NOT NULL, criado_em TEXT, PRIMARY KEY(usuario_id, topico_id))",
    "CREATE INDEX IF NOT EXISTS idx_reposts_topico ON reposts(topico_id)",
]
TABELAS = ['tags', 'topicos', 'membros', 'logs', 'rotacoes', 'usuarios', 'sessoes', 'limites', 'respostas', 'palavras_restritas', 'moderacao', 'grupos', 'grupo_membros', 'notificacoes']


def agora():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


class Repositorio:
    def __init__(self, db):
        self.db = db

    # ---- esquema / saúde
    def inicializar(self):
        self.db.batch([(s, ()) for s in SCHEMA])
        # Migrações aditivas: preservam os dados e não recriam tabelas existentes.
        cols = {r['name'] for r in self.db.execute('PRAGMA table_info(usuarios)').rows}
        for nome, tipo in [('formacao', "TEXT DEFAULT ''"), ('especialidade', "TEXT DEFAULT ''"), ('descricao_profissional', "TEXT DEFAULT ''"),
                           ('foto', "TEXT DEFAULT ''"), ('biografia', "TEXT DEFAULT ''"), ('informacoes', "TEXT DEFAULT ''")]:
            if nome not in cols:
                self.db.execute(f'ALTER TABLE usuarios ADD COLUMN {nome} {tipo}')
        if 'autor_id' not in {r['name'] for r in self.db.execute('PRAGMA table_info(respostas)').rows}:
            self.db.execute('ALTER TABLE respostas ADD COLUMN autor_id INTEGER')
        if 'parent_id' not in {r['name'] for r in self.db.execute('PRAGMA table_info(respostas)').rows}:
            self.db.execute('ALTER TABLE respostas ADD COLUMN parent_id INTEGER')   # resposta a outra resposta
        if 'responsavel_id' not in {r['name'] for r in self.db.execute('PRAGMA table_info(grupos)').rows}:
            self.db.execute('ALTER TABLE grupos ADD COLUMN responsavel_id INTEGER')
            self.db.execute('UPDATE grupos SET responsavel_id=(SELECT id FROM usuarios WHERE email=grupos.criado_por)')
        self.db.execute('DELETE FROM grupo_membros WHERE usuario_id NOT IN (SELECT id FROM usuarios) '
                        'OR grupo_id NOT IN (SELECT id FROM grupos)')
        top_cols = {r['name'] for r in self.db.execute('PRAGMA table_info(topicos)').rows}
        if 'autor_id' not in top_cols:
            self.db.execute('ALTER TABLE topicos ADD COLUMN autor_id INTEGER')
            self.db.execute('UPDATE topicos SET autor_id=(SELECT id FROM usuarios WHERE nome=topicos.autor) WHERE '
                            '(SELECT COUNT(*) FROM usuarios WHERE nome=topicos.autor)=1')
        for nome, tipo in [('oculto', 'INTEGER NOT NULL DEFAULT 0'), ('status_moderacao', "TEXT NOT NULL DEFAULT 'aprovado'")]:
            if nome not in top_cols:
                self.db.execute(f'ALTER TABLE topicos ADD COLUMN {nome} {tipo}')
        self._migrar_admins_antigos()
        if self.db.execute('SELECT COUNT(*) AS n FROM membros').rows[0]['n'] == 0:
            self.db.batch([('INSERT INTO membros(nome) VALUES(?)', (n,)) for n in MEMBROS_INICIAIS])

    def _migrar_admins_antigos(self):
        """Fluxo antigo removido: contas da tabela `admins` viram administradores em `usuarios`
        (o hash da senha é o mesmo; o mais antigo vira o principal) e a tabela é descartada."""
        if 'admins' not in self.tabelas_existentes():
            return
        stmts = []
        if self.contar_usuarios() == 0:
            stmts += [("""INSERT INTO usuarios(nome, email, senha, perfil, status, criado_em)
                          SELECT COALESCE(NULLIF(nome, ''), email), lower(email), senha, 'admin', 'ativo', ?
                          FROM admins ORDER BY id""", (agora(),)),
                      ('UPDATE usuarios SET principal = 1 WHERE id = (SELECT MIN(id) FROM usuarios)', ())]
        self.db.batch(stmts + [('DROP TABLE admins', ())])

    def tabelas_existentes(self):
        rows = self.db.execute("SELECT name FROM sqlite_master WHERE type='table'").rows
        return sorted(r['name'] for r in rows)

    def saude(self):
        info = self.db.ping()
        faltando = [t for t in TABELAS if t not in self.tabelas_existentes()]
        info['esquema_ok'] = not faltando
        if faltando:
            info['tabelas_faltando'] = faltando
        return info

    # ---- tags
    def listar_tags(self):
        """Ordem de inserção (rowid): é a ordem usada para reconstruir a AVL."""
        return self.db.execute('SELECT key, display_name, description, usage_count FROM tags ORDER BY rowid').rows

    def contar(self, tabela):
        assert tabela in TABELAS
        return self.db.execute(f'SELECT COUNT(*) AS n FROM {tabela}').rows[0]['n']

    @staticmethod
    def _sql_rotacoes(eventos):
        return [('INSERT INTO rotacoes(data, tipo, no) VALUES(?,?,?)', (agora(), e['tipo'], e['no']))
                for e in eventos]

    def criar_tag(self, chave, nome, descricao, rotacoes):
        """Lança DbIntegrityError se a chave já existir."""
        self.db.batch([('INSERT INTO tags(key, display_name, description, usage_count, criado_em) VALUES(?,?,?,0,?)',
                        (chave, nome, descricao, agora()))] + self._sql_rotacoes(rotacoes))

    def remover_tag(self, chave, rotacoes):
        self.db.batch([('DELETE FROM tags WHERE key=?', (chave,))] + self._sql_rotacoes(rotacoes))

    def editar_tag(self, chave_antiga, chave_nova, nome_antigo, nome, descricao, uso, rotacoes):
        rows=self.db.execute('SELECT id,tags FROM topicos').rows
        stmts=[('UPDATE tags SET key=?,display_name=?,description=? WHERE key=?',(chave_nova,nome,descricao,chave_antiga))]
        for row in rows:
            tags=json.loads(row['tags'] or '[]')
            atualizadas=[nome if str(t).casefold()==nome_antigo.casefold() else t for t in tags]
            if atualizadas!=tags: stmts.append(('UPDATE topicos SET tags=? WHERE id=?',(json.dumps(atualizadas,ensure_ascii=False),row['id'])))
        stmts += self._sql_rotacoes(rotacoes)
        self.db.batch(stmts)

    def criar_topico(self, titulo, descricao, autor, tags, rotacoes):
        """Em UMA transação: incrementa/cria as tags, grava o tópico e as rotações.
        `tags` = [(chave, nome, descricao)]. O incremento é feito no SQL (seguro entre instâncias)."""
        t = agora()
        stmts = [("""INSERT INTO tags(key, display_name, description, usage_count, criado_em) VALUES(?,?,?,1,?)
                     ON CONFLICT(key) DO UPDATE SET usage_count = usage_count + 1""",
                  (ch, nome, desc, t)) for ch, nome, desc in tags]
        stmts.append(('INSERT INTO topicos(titulo, descricao, autor, tags, criado_em) VALUES(?,?,?,?,?)',
                      (titulo, descricao, autor, json.dumps([n for _, n, _ in tags], ensure_ascii=False), t)))
        res = self.db.batch(stmts + self._sql_rotacoes(rotacoes))
        novo_id = res[len(tags)].last_id
        return self._topico(self.db.execute('SELECT * FROM topicos WHERE id=?', (novo_id,)).rows[0])

    # ---- tópicos
    @staticmethod
    def _topico(r):
        d = dict(r)
        d['tags'] = json.loads(d['tags'] or '[]')
        return d

    def listar_topicos(self, incluir_ocultos=False):
        sql = 'SELECT * FROM topicos' + ('' if incluir_ocultos else ' WHERE oculto=0 AND status_moderacao=\'aprovado\'') + ' ORDER BY id DESC'
        return [self._topico(r) for r in self.db.execute(sql).rows]

    # ---- consultas administrativas complementares
    def atividades_recentes(self, limite=12):
        return self.db.execute('SELECT data, usuario, acao, resultado FROM logs ORDER BY id DESC LIMIT ?', (limite,)).rows

    def dashboard_completo(self):
        return {'usuarios': self.contar('usuarios'), 'professores': self.db.execute("SELECT COUNT(*) n FROM usuarios WHERE perfil='professor'").rows[0]['n'],
                'respostas': self.contar('respostas'), 'grupos': self.contar('grupos'),
                'pendentes': self.db.execute("SELECT COUNT(*) n FROM moderacao WHERE status='pendente'").rows[0]['n'],
                'topicos_ocultos': self.db.execute('SELECT COUNT(*) n FROM topicos WHERE oculto=1').rows[0]['n'],
                'atividades': self.atividades_recentes()}

    def registrar_atividade(self, usuario, acao, resultado='ok'):
        self.registrar_log(usuario, acao, resultado)

    def palavras(self):
        return self.db.execute('SELECT * FROM palavras_restritas ORDER BY palavra COLLATE NOCASE').rows

    def detectar_palavras(self, texto):
        achadas=[]
        for r in self.palavras():
            if r['ativo'] and r['palavra'].casefold() in str(texto or '').casefold(): achadas.append(r['palavra'])
        return achadas

    # ---- membros
    def listar_membros(self):
        membros = self.db.execute('SELECT * FROM membros ORDER BY nome').rows
        autores = [r['autor'] for r in self.db.execute('SELECT autor FROM topicos').rows]
        for m in membros:
            alvo = m['nome'].casefold()
            m['n_duvidas'] = sum(1 for a in autores if (a or '').casefold() == alvo)
        return membros

    # ---- logs e rotações
    def registrar_log(self, usuario, acao, resultado):
        self.db.execute('INSERT INTO logs(data, usuario, acao, resultado) VALUES(?,?,?,?)',
                        (agora(), usuario or 'anônimo', acao, resultado))

    def listar_logs(self, limite=200):
        return self.db.execute('SELECT * FROM logs ORDER BY id DESC LIMIT ?', (limite,)).rows

    def resumo_rotacoes(self):
        por_tipo = {'LL': 0, 'RR': 0, 'LR': 0, 'RL': 0}
        for r in self.db.execute('SELECT tipo, COUNT(*) AS n FROM rotacoes GROUP BY tipo').rows:
            por_tipo[r['tipo']] = r['n']
        return {'total': sum(por_tipo.values()), 'por_tipo': por_tipo}

    # ---- usuários
    _COLS_USUARIO = ('u.id, u.nome, u.email, u.perfil, u.status, u.verificado, u.principal, u.criado_em, '
                     'u.ultimo_login, u.verificado_em, v.nome AS verificado_por_nome')
    _JOIN_USUARIO = 'FROM usuarios u LEFT JOIN usuarios v ON v.id = u.verificado_por'

    def contar_usuarios(self):
        return self.db.execute('SELECT COUNT(*) AS n FROM usuarios').rows[0]['n']

    def criar_principal(self, nome, email, senha_hash):
        """Cria o administrador principal SOMENTE se não existir nenhum usuário (uma única instrução atômica:
        dois cadastros simultâneos não geram dois principais). Devolve o id ou None."""
        r = self.db.execute("""INSERT INTO usuarios(nome, email, senha, perfil, status, verificado, principal, criado_em)
                               SELECT ?, ?, ?, 'admin', 'ativo', 0, 1, ?
                               WHERE NOT EXISTS (SELECT 1 FROM usuarios)""",
                            (nome, email, senha_hash, agora()))
        return r.last_id if r.rowcount else None

    def criar_usuario(self, nome, email, senha_hash, perfil, criado_por):
        """Devolve o id, ou None se o e-mail já existir."""
        from forum.db import DbIntegrityError
        try:
            return self.db.execute(
                'INSERT INTO usuarios(nome, email, senha, perfil, criado_em, criado_por) VALUES(?,?,?,?,?,?)',
                (nome, email, senha_hash, perfil, agora(), criado_por)).last_id
        except DbIntegrityError:
            return None

    def obter_usuario_por_email(self, email):
        """Linha completa (com hash da senha) — uso interno do login."""
        rows = self.db.execute('SELECT * FROM usuarios WHERE email=?', (email,)).rows
        return rows[0] if rows else None

    def obter_usuario(self, uid):
        rows = self.db.execute(f'SELECT {self._COLS_USUARIO} {self._JOIN_USUARIO} WHERE u.id=?', (uid,)).rows
        return rows[0] if rows else None

    _COLS_PERFIL = 'id, nome, foto, biografia, formacao, especialidade, descricao_profissional, verificado'

    def perfil_proprio(self, uid):
        rows = self.db.execute('SELECT id, nome, email, perfil, verificado, foto, biografia, informacoes, formacao, '
                               'especialidade, descricao_profissional FROM usuarios WHERE id=?', (uid,)).rows
        return rows[0] if rows else None

    def notificar_resposta(self, resposta_id):
        """Avisa o autor da dúvida (aluno/professor) quando um professor verificado tem uma resposta publicada."""
        rows = self.db.execute(
            "SELECT r.id, r.topico_id, r.autor, r.autor_id, t.autor_id AS dono, d.perfil AS perfil_dono, "
            "a.perfil AS perfil_autor, a.verificado AS verif_autor FROM respostas r "
            "JOIN topicos t ON t.id=r.topico_id JOIN usuarios d ON d.id=t.autor_id JOIN usuarios a ON a.id=r.autor_id "
            "WHERE r.id=? AND r.status='publicada'", (resposta_id,)).rows
        if not rows:
            return
        r = rows[0]
        if r['perfil_autor'] == 'professor' and r['verif_autor'] and r['dono'] != r['autor_id'] \
                and r['perfil_dono'] in ('aluno', 'professor'):
            self.db.execute('INSERT OR IGNORE INTO notificacoes(usuario_id,resposta_id,topico_id,autor_nome,criado_em) '
                            'VALUES(?,?,?,?,?)', (r['dono'], r['id'], r['topico_id'], r['autor'], agora()))

    def listar_professores(self):
        return self.db.execute(f"SELECT {self._COLS_PERFIL} FROM usuarios WHERE perfil='professor' AND verificado=1 "
                               "AND status='ativo' ORDER BY nome COLLATE NOCASE").rows

    def obter_professor(self, uid):
        rows = self.db.execute(f"SELECT {self._COLS_PERFIL} FROM usuarios WHERE id=? AND perfil='professor' "
                               "AND verificado=1 AND status='ativo'", (uid,)).rows
        return rows[0] if rows else None

    def listar_usuarios(self, limite=500):
        return self.db.execute(f'SELECT {self._COLS_USUARIO} {self._JOIN_USUARIO} ORDER BY u.principal DESC, u.nome '
                               'COLLATE NOCASE LIMIT ?', (limite,)).rows

    def atualizar_usuario(self, uid, campos, revogar_sessoes=False):
        """`campos`: dict coluna->valor (colunas controladas pelo código, nunca vindas do cliente).
        Devolve False se o e-mail novo já existir."""
        from forum.db import DbIntegrityError
        colunas = {'nome', 'email', 'senha', 'perfil', 'status', 'verificado', 'verificado_em', 'verificado_por',
                   'ultimo_login', 'foto', 'biografia', 'informacoes', 'formacao', 'especialidade',
                   'descricao_profissional'}
        assert campos and set(campos) <= colunas
        stmts = [(f"UPDATE usuarios SET {', '.join(c + '=?' for c in campos)} WHERE id=?", (*campos.values(), uid))]
        if revogar_sessoes:
            stmts.append(('DELETE FROM sessoes WHERE usuario_id=?', (uid,)))
        try:
            self.db.batch(stmts)
            return True
        except DbIntegrityError:
            return False

    def excluir_usuario(self, uid):
        self.db.batch([('DELETE FROM sessoes WHERE usuario_id=?', (uid,)),
                       ('DELETE FROM grupo_membros WHERE usuario_id=?', (uid,)),
                       ('DELETE FROM notificacoes WHERE usuario_id=?', (uid,)),
                       ('UPDATE grupos SET responsavel_id=NULL WHERE responsavel_id=?', (uid,)),
                       ('DELETE FROM usuarios WHERE id=? AND principal=0', (uid,))])

    # ---- sessões
    def criar_sessao(self, sid, uid, csrf, expira_em, ip, agente):
        t = time.time()
        self.db.batch([('DELETE FROM sessoes WHERE expira_em < ?', (t,)),      # limpeza oportunista
                       ('INSERT INTO sessoes(id, usuario_id, csrf, criado_em, ultimo_uso, expira_em, ip, agente) '
                        'VALUES(?,?,?,?,?,?,?,?)', (sid, uid, csrf, t, t, expira_em, ip, (agente or '')[:200]))])

    def obter_sessao(self, sid):
        """Sessão + dados ATUAIS do usuário (perfil/status/verificação vêm sempre do banco)."""
        rows = self.db.execute(
            """SELECT s.id AS sid, s.csrf, s.criado_em AS s_criado, s.ultimo_uso, s.expira_em,
                      u.id, u.nome, u.email, u.perfil, u.status, u.verificado, u.principal
               FROM sessoes s JOIN usuarios u ON u.id = s.usuario_id WHERE s.id=?""", (sid,)).rows
        return rows[0] if rows else None

    def tocar_sessao(self, sid):
        self.db.execute('UPDATE sessoes SET ultimo_uso=? WHERE id=?', (time.time(), sid))

    def encerrar_sessao(self, sid):
        self.db.execute('DELETE FROM sessoes WHERE id=?', (sid,))

    def encerrar_sessoes_do_usuario(self, uid, exceto=None):
        if exceto:
            self.db.execute('DELETE FROM sessoes WHERE usuario_id=? AND id<>?', (uid, exceto))
        else:
            self.db.execute('DELETE FROM sessoes WHERE usuario_id=?', (uid,))

    # ---- limitador de requisições (compartilhado entre instâncias)
    def limite_atingido(self, escopo, ip, janela, maximo):
        r = self.db.execute('SELECT COUNT(*) AS n FROM limites WHERE chave=? AND ts>?',
                            (f'{escopo}:{ip}', time.time() - janela))
        return r.rows[0]['n'] >= maximo

    def registrar_limite(self, escopo, ip):
        agora_ts = time.time()
        self.db.batch([('DELETE FROM limites WHERE ts<?', (agora_ts - 3600,)),
                       ('INSERT INTO limites(chave, ts) VALUES(?,?)', (f'{escopo}:{ip}', agora_ts))])

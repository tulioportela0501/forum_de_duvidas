"""Testa a conexão com o banco e faz um ciclo escrita/leitura/limpeza.

  python scripts/check_connection.py --local     # SQLite local (arquivo temporário, não toca nos seus dados)
  python scripts/check_connection.py --remote    # Turso: exige TURSO_DATABASE_URL e TURSO_AUTH_TOKEN
"""
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from forum.config import carregar_config  # noqa: E402
from forum.db import DbError, SqliteDb, TursoDb  # noqa: E402
from forum.repo import Repositorio  # noqa: E402

modo = sys.argv[1] if len(sys.argv) > 1 else '--local'
cfg = carregar_config()

if modo == '--remote':
    if not cfg['TURSO_DATABASE_URL'] or not cfg['TURSO_AUTH_TOKEN']:
        print('Defina TURSO_DATABASE_URL e TURSO_AUTH_TOKEN (.env ou ambiente).')
        sys.exit(2)
    db = TursoDb(cfg['TURSO_DATABASE_URL'], cfg['TURSO_AUTH_TOKEN'])
elif modo == '--local':
    db = SqliteDb(os.path.join(tempfile.mkdtemp(), 'check.db'))
else:
    print(__doc__)
    sys.exit(2)

repo = Repositorio(db)
try:
    t0 = time.time()
    print('Conexão     :', db.ping(), f'({(time.time() - t0) * 1000:.0f} ms)')
    if modo == '--local':
        repo.inicializar()
    info = repo.saude()
    print('Esquema     :', 'OK' if info['esquema_ok'] else f"FALTANDO {info.get('tabelas_faltando')} -> rode scripts/init_db.py")
    if info['esquema_ok']:
        chave = f'__check__{int(time.time())}'
        repo.registrar_limite('check', chave)
        n = db.execute('SELECT COUNT(*) AS n FROM limites WHERE chave=?', (f'check:{chave}',)).rows[0]['n']
        db.execute('DELETE FROM limites WHERE chave=?', (f'check:{chave}',))
        print('Escrita/leitura:', 'OK' if n == 1 else f'FALHOU (n={n})')
        sys.exit(0 if n == 1 else 1)
    sys.exit(1)
except DbError as e:
    print('ERRO:', e)
    sys.exit(1)

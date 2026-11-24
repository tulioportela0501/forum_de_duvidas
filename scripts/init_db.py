"""Cria as tabelas (idempotente) no banco configurado: Turso se TURSO_DATABASE_URL existir, senão SQLite local.

Uso:  python scripts/init_db.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from forum.config import carregar_config  # noqa: E402
from forum.db import DbError, criar_db  # noqa: E402
from forum.repo import Repositorio  # noqa: E402

cfg = carregar_config()
db = criar_db(cfg)
repo = Repositorio(db)
try:
    repo.inicializar()
    print(f'OK  modo={db.modo}  tabelas={", ".join(repo.tabelas_existentes())}')
except DbError as e:
    print('ERRO:', e)
    sys.exit(1)

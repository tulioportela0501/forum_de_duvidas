"""Configuração do backend.

Ordem de prioridade: variáveis de ambiente > arquivo .env > valores gerados automaticamente.
SECRET_KEY e CODIGO_ADMIN, quando não definidos, são gerados na primeira execução e
guardados em backend/data/ (pasta ignorada pelo git) — nenhum segredo fica no código-fonte.
"""
import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent


def _carregar_env(caminho):
    if not caminho.is_file():
        return
    for linha in caminho.read_text(encoding='utf-8').splitlines():
        linha = linha.strip()
        if not linha or linha.startswith('#') or '=' not in linha:
            continue
        chave, _, valor = linha.partition('=')
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


def _segredo_persistido(pasta, nome, gerar):
    arq = pasta / nome
    if arq.is_file():
        valor = arq.read_text(encoding='utf-8').strip()
        if valor:
            return valor
    valor = gerar()
    arq.write_text(valor, encoding='utf-8')
    try:
        os.chmod(arq, 0o600)
    except OSError:
        pass
    return valor


def carregar_config(overrides=None):
    _carregar_env(ROOT_DIR / '.env')
    _carregar_env(BASE_DIR / '.env')
    overrides = overrides or {}

    data_dir = Path(overrides.get('DATA_DIR') or os.environ.get('DATA_DIR') or BASE_DIR / 'data')
    data_dir.mkdir(parents=True, exist_ok=True)

    cfg = {
        'DATA_DIR': str(data_dir),
        'DB_PATH': str(data_dir / 'forum.db'),
        'FRONTEND_DIR': str(ROOT_DIR / 'frontend'),
        'SECRET_KEY': os.environ.get('SECRET_KEY')
        or _segredo_persistido(data_dir, 'secret_key.txt', lambda: secrets.token_hex(32)),
        'CODIGO_ADMIN': os.environ.get('CODIGO_ADMIN')
        or _segredo_persistido(data_dir, 'codigo_admin.txt', lambda: secrets.token_urlsafe(9)),
        'CODIGO_ADMIN_ORIGEM': 'ambiente' if os.environ.get('CODIGO_ADMIN') else 'arquivo gerado',
        'TOKEN_MAX_AGE': int(os.environ.get('TOKEN_MAX_AGE', 8 * 3600)),
        'CORS_ORIGINS': [o.strip() for o in os.environ.get('CORS_ORIGINS', '').split(',') if o.strip()],
        'MAX_CONTENT_LENGTH': 64 * 1024,
    }
    if 'DATA_DIR' in overrides:
        cfg['DB_PATH'] = str(data_dir / 'forum.db')
    cfg.update({k: v for k, v in overrides.items() if k != 'DATA_DIR'})
    return cfg

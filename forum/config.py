"""Configuração do backend (local e Vercel).

Prioridade: overrides (testes) > variáveis de ambiente > .env/.env.local > valores gerados (SÓ em dev local).

Variáveis:
  TURSO_DATABASE_URL, TURSO_AUTH_TOKEN  -> usa Turso (libSQL) via HTTP. Se vazio, usa SQLite local.
  LOCAL_DB_PATH                           -> arquivo SQLite local (padrão: data/forum.db)
  SECRET_KEY                              -> OBRIGATÓRIA na Vercel (protege os identificadores de sessão no banco);
                                             em dev local é gerada em data/.
  AUTO_INIT_DB                            -> 1 cria tabelas ao iniciar (padrão: 1 no SQLite, 0 no Turso)
  SESSION_MAX_AGE, SESSION_IDLE, COOKIE_SECURE, CORS_ORIGINS, PORT
"""
import os
import secrets
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


class ConfigError(RuntimeError):
    pass


def _carregar_env(caminho):
    if not caminho.is_file():
        return
    for linha in caminho.read_text(encoding='utf-8').splitlines():
        linha = linha.strip()
        if not linha or linha.startswith('#') or '=' not in linha:
            continue
        chave, _, valor = linha.partition('=')
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


def _segredo_local(data_dir, nome, gerar):
    """Dev local: persiste o segredo gerado em data/ (pasta ignorada pelo git)."""
    data_dir.mkdir(parents=True, exist_ok=True)
    arq = data_dir / nome
    if arq.is_file() and arq.read_text(encoding='utf-8').strip():
        return arq.read_text(encoding='utf-8').strip()
    valor = gerar()
    arq.write_text(valor, encoding='utf-8')
    try:
        os.chmod(arq, 0o600)
    except OSError:
        pass
    return valor


def carregar_config(overrides=None):
    overrides = dict(overrides or {})
    _carregar_env(ROOT_DIR / '.env')
    _carregar_env(ROOT_DIR / '.env.local')      # gerado por `vercel env pull`
    env = os.environ.get
    pegar = lambda k, padrao='': overrides[k] if k in overrides else env(k, padrao)

    is_vercel = bool(env('VERCEL'))
    turso_url = str(pegar('TURSO_DATABASE_URL')).strip()
    data_dir = Path(pegar('DATA_DIR') or ROOT_DIR / 'data')

    def segredo(nome, gerar):
        valor = str(pegar(nome)).strip()
        if valor:
            return valor, ('override' if nome in overrides else 'ambiente')
        if is_vercel:
            raise ConfigError(f'Variável de ambiente obrigatória ausente: {nome} '
                              '(defina em Vercel > Settings > Environment Variables).')
        return _segredo_local(data_dir, nome.lower() + '.txt', gerar), 'arquivo gerado (dev local)'

    secret_key, _ = segredo('SECRET_KEY', lambda: secrets.token_hex(32))

    auto = str(pegar('AUTO_INIT_DB', '')).strip()
    cfg = {
        'IS_VERCEL': is_vercel,
        'PUBLIC_DIR': str(ROOT_DIR / 'public'),
        'TURSO_DATABASE_URL': turso_url,
        'TURSO_AUTH_TOKEN': str(pegar('TURSO_AUTH_TOKEN')).strip(),
        'LOCAL_DB_PATH': str(pegar('LOCAL_DB_PATH') or data_dir / 'forum.db'),
        'AUTO_INIT_DB': (auto == '1') if auto else (not turso_url),
        'SECRET_KEY': secret_key,
        'SESSION_MAX_AGE': int(pegar('SESSION_MAX_AGE', 8 * 3600)),     # duração máxima absoluta da sessão
        'SESSION_IDLE': int(pegar('SESSION_IDLE', 2 * 3600)),           # expira após esse tempo sem uso
        # None = automático (Secure quando a requisição chega por HTTPS); '1'/'0' força
        'COOKIE_SECURE': (str(pegar('COOKIE_SECURE')).strip() == '1') if str(pegar('COOKIE_SECURE')).strip() else None,
        'CORS_ORIGINS': [o.strip() for o in str(pegar('CORS_ORIGINS')).split(',') if o.strip()],
        'MAX_CONTENT_LENGTH': 64 * 1024,
    }
    cfg.update({k: v for k, v in overrides.items() if k in cfg})
    return cfg

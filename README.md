# Fórum de Dúvidas Acadêmicas — Dicionário de Tags com Árvore AVL

Disciplina **Algoritmos e Estrutura de Dados Avançado** (Anhanguera São Luís — MA, 2026).
Stack: **Python + Flask** (API), **HTML/CSS/JS puro** (front), **Turso (libSQL)** (persistência), **Vercel** (deploy serverless).

## Arquitetura
```
public/            frontend estático (index.html, login.html, css/, js/)   -> CDN da Vercel
api/index.py       função serverless: expõe o app Flask                              -> /api/*
forum/             avl.py (AVL manual, INALTERADA) · service.py · repo.py · db.py · config.py
                   auth.py (sessões, login, permissões) · usuarios.py (gestão de contas) · routes.py (fórum)
scripts/           init_db.py (cria tabelas) · check_connection.py (testa banco)
tests/             ~250 testes (AVL, API, autenticação, permissões e drivers; API roda em SQLite e em Turso simulado)
vercel.json        rewrite /api/* -> api/index ; cabeçalhos de segurança
```
**Serverless e a AVL:** funções da Vercel não guardam estado. O banco (tabela `tags`) é a fonte da verdade; a
cada requisição a árvore AVL manual é **reconstruída em memória** a partir das tags, a operação roda nela
(inserção, busca, remoção, rotações, prefixo) e o resultado é gravado em **uma transação** (tags + tópico + rotações).
O contador de uso é incrementado no SQL (`usage_count = usage_count + 1`), seguro entre instâncias concorrentes.
Limitador de tentativas e rotações também ficam no banco.

**Drivers** (`forum/db.py`, só biblioteca padrão): `SqliteDb` (local) e `TursoDb` (API HTTP `/v2/pipeline` do Turso,
sem dependência nativa). Se `TURSO_DATABASE_URL` estiver vazia, usa SQLite em `data/forum.db`.

## Rodar localmente (VS Code)
```bash
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python run_local.py                                       # http://127.0.0.1:5000
```
Windows/Linux: `run.bat` / `./run.sh` fazem o mesmo. Sem `.env`, usa SQLite local e gera
o `SECRET_KEY` em `data/`. No primeiro acesso, abra o endereço e crie o administrador principal. No VS Code: **Terminal > Run Task** (instalar, iniciar,
criar tabelas, testar conexão, testes) ou **F5** (`.vscode/launch.json`).

## Variáveis de ambiente (`.env.example`)
| Variável | Local | Vercel |
|---|---|---|
| `TURSO_DATABASE_URL` / `TURSO_AUTH_TOKEN` | opcional (vazio = SQLite) | **obrigatório** |
| `SECRET_KEY` | gerado em `data/` se vazio | **obrigatório** |
| `SESSION_MAX_AGE` / `SESSION_IDLE` | 8 h / 2 h | idem (opcional) |
| `AUTO_INIT_DB` | padrão 1 (SQLite) | padrão 0 → use `scripts/init_db.py` |

## Turso
```bash
turso db create forum-avl
turso db show forum-avl --url          # TURSO_DATABASE_URL  (libsql://...)
turso db tokens create forum-avl       # TURSO_AUTH_TOKEN
```
Coloque os dois no `.env`, depois:
```bash
python scripts/init_db.py                      # cria as tabelas no Turso (idempotente)
python scripts/check_connection.py --remote    # testa conexão + escrita/leitura
python scripts/check_connection.py --local     # idem, em SQLite temporário
```

## Deploy na Vercel
1. Suba o projeto ao GitHub e importe na Vercel (framework: *Other*; sem build command).
2. Em *Settings > Environment Variables* cadastre `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN`, `SECRET_KEY`
   (ex.: `python -c "import secrets;print(secrets.token_hex(32))"`).
3. Rode `python scripts/init_db.py` uma vez (local, apontando para o Turso).
4. Deploy. **Abra o site imediatamente e crie o administrador principal** (ver abaixo). Verifique `https://SEU-PROJETO.vercel.app/api/health` → `{"status":"ok", ...}`.
Teste local do ambiente Vercel: `vercel dev` (usa `.env.local` gerado por `vercel env pull`).

`/api/health` responde 503 com `esquema_pendente` (tabelas não criadas) ou `erro` (banco inacessível).

## Autenticação e permissões
**Primeiro acesso:** enquanto não existe nenhum usuário, `login.html` mostra a criação do **administrador principal**
(`POST /api/auth/setup`). Depois disso a rota responde 409 para sempre e **somente administradores cadastram contas**.
Quem abrir um deploy novo primeiro vira o principal — por isso crie-o logo após o deploy.

| Perfil | Pode |
|---|---|
| **Aluno** | ler tags, dúvidas e membros; publicar dúvidas (o autor é sempre o nome da sessão) |
| **Professor** (verificado) | tudo do aluno + criar tags, ver árvore AVL, rotações, painel e teste de carga |
| **Administrador** | tudo + remover tags, ver logs e gerenciar usuários |

* **Professor precisa de verificação administrativa:** nasce "aguardando verificação" e não consegue entrar até um
  administrador usar *Verificar professor*. A verificação cai se o e-mail mudar, se o perfil mudar ou se for
  revogada (a sessão aberta é derrubada na hora).
* **Administrador principal:** só ele mesmo o altera; ninguém (nem ele) o bloqueia, exclui ou rebaixa — o sistema nunca fica sem administrador.
  Ninguém bloqueia, exclui ou muda o próprio perfil; a própria senha só muda em *Minha conta* (exige a senha atual).
* **Sessões:** cookie `forum_sid` aleatório (256 bits), `HttpOnly`, `SameSite=Strict`, `Secure` em HTTPS; o banco guarda só o
  HMAC dele. Expira em 8 h (absoluto) ou 2 h sem uso, e é revogada ao bloquear, excluir, trocar perfil/senha ou revogar verificação.
  Perfil, status e verificação são relidos do banco **a cada requisição**.
* **Backend nega por padrão:** toda rota `/api/*` exige sessão, exceto `health`, `auth/estado`, `auth/setup` e `auth/login`;
  o perfil exigido é declarado com `@perfis(...)`. Ações que alteram dados exigem o cabeçalho `X-CSRF-Token` e origem do mesmo site.
* **Senhas:** scrypt com sal; mínimo 10 caracteres, letras e números; login com mesma mensagem para e-mail inexistente/senha errada;
  limite de 8 falhas/15 min por IP e 20 por e-mail.
* Contas do fluxo antigo (tabela `admins`) são migradas para administradores por `scripts/init_db.py` (ou ao iniciar, no SQLite local).
* Local com front em outra porta (ex.: Live Server): abra a página com o mesmo host do backend (`127.0.0.1` com `127.0.0.1`),
  senão o navegador não envia o cookie.

## API
| Método | Rota | Acesso |
|---|---|---|
| GET | `/api/health`, `/api/auth/estado` | público |
| POST | `/api/auth/setup` (só sem usuários), `/api/auth/login` | público (8 falhas/15 min por IP) |
| GET/POST | `/api/auth/eu`, `/api/auth/logout`, `/api/auth/senha` | logado |
| GET | `/api/tags`, `/api/tags/autocomplete?q=`, `/api/topicos`, `/api/membros` | logado |
| POST | `/api/topicos` `{titulo, descricao, tags[]}` | logado (20/min por usuário) |
| POST | `/api/tags` | professor, admin |
| GET | `/api/avl`, `/api/avl/rotacoes`, `/api/dashboard` · POST `/api/avl/teste` | professor, admin |
| DELETE | `/api/tags/<nome>` · GET `/api/logs` | admin |
| GET/POST | `/api/usuarios` (listar / cadastrar) | admin |
| GET/PATCH/DELETE | `/api/usuarios/<id>` | admin |
| POST | `/api/usuarios/<id>/bloquear`, `/desbloquear`, `/verificar`, `/revogar-verificacao` | admin |

## AVL (resumo)
`forum/avl.py` é a implementação manual original, **sem nenhuma alteração**: nós com ponteiros, altura,
FB = h(esq) − h(dir), rotações LL/RR/LR/RL, remoção com sucessor in-order, prefixo com poda. Busca, inserção e
remoção O(log n); autocomplete O(log n + k). Tags comparadas sem acento/caixa.

## Testes
```bash
python -m pytest -q      # ~250 testes (a suíte de API roda duas vezes: SQLite e Turso simulado)
```
`tests/mock_turso.py` simula o endpoint `/v2/pipeline` do Turso sobre SQLite, então o mesmo conjunto de testes de
API roda com o driver remoto sem rede.

## Limitações conhecidas (próximas etapas)
* Reconstrução da AVL a cada requisição: ideal para centenas/milhares de tags; a forma da árvore após remoções
  pode diferir da anterior (as chaves e contadores são idênticos).
* Sem recuperação de senha por e-mail (um administrador redefine a senha em *Usuários*).
* Sem paginação de tópicos; respostas/visualizações ainda não implementadas.
* O ranking do dashboard ainda usa `sorted()` (fora da AVL).

# Plataforma de Fórum de Dúvidas Acadêmicas — Dicionário de Tags com Árvore AVL

Projeto da disciplina **Algoritmos e Estrutura de Dados Avançado** (Faculdade Anhanguera de São Luís — MA, 2026).
Estudantes publicam dúvidas com tags; cada tag vive em uma **Árvore AVL implementada manualmente** em Python
(sem dict/set/sorted/bibliotecas como substituto), com contador de uso, busca, remoção, autocomplete e visualização.

## Como rodar

```bash
# Windows: dê dois cliques em run.bat      Linux/Mac: ./run.sh
# ou manualmente:
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Abra **http://127.0.0.1:5000**. O mesmo servidor entrega API e frontend (sem problemas de CORS).
Ao iniciar, o console mostra o **código de cadastro de administrador**.

## Rodando com o Go Live (Live Server) no VS Code
O Go Live só serve arquivos estáticos; a API precisa do Flask rodando ao mesmo tempo:
1. Terminal 1 (fica aberto): `cd backend` → `python -m pip install -r requirements.txt` (só na 1ª vez) → `python app.py`
   (ou `Terminal > Run Task > Backend: iniciar`).
2. Clique com o botão direito em `frontend/index.html` → **Open with Live Server** (ou botão *Go Live*).
3. O front descobre sozinho o backend em `http://127.0.0.1:5000`. Se o backend estiver desligado, a tela avisa e o
   botão *Tentar novamente* funciona assim que você iniciá-lo.

A pasta `.vscode/` já configura o Live Server para servir `/frontend` e **ignorar `backend/`** (senão cada gravação
no banco recarregaria a página e cortaria a animação da AVL).

## Área administrativa
1. Abra `Área administrativa` → *Entrar / cadastrar* → **Cadastrar (código de acesso)**.
2. Informe nome, e-mail, senha (mín. 10 caracteres) e o código exibido no console.
3. O código e a `SECRET_KEY` **não ficam no código-fonte**: vêm de `.env`/variáveis de ambiente
   (veja `.env.example`) ou são gerados na 1ª execução em `backend/data/` (ignorado pelo git).
   Defina `CODIGO_ADMIN` no `.env` para escolher o seu, e troque-o após a entrega.
4. Rotas protegidas por token (8 h): árvore AVL, rotações, logs, dashboard, teste de carga, criar/remover tags.
   Limite de 8 tentativas falhas / 15 min por IP.

## API
| Método | Rota | Acesso |
|---|---|---|
| GET | `/api/tags`, `/api/tags/autocomplete?q=`, `/api/topicos`, `/api/membros`, `/api/health` | público |
| POST | `/api/topicos` `{titulo, descricao, autor, tags[]}` | público (20/min por IP) |
| POST/DELETE | `/api/tags`, `/api/tags/<nome>` | admin |
| GET | `/api/avl`, `/api/avl/rotacoes`, `/api/logs`, `/api/dashboard` | admin |
| POST | `/api/avl/teste` (aula1→aula20 em árvore temporária) | admin |
| POST | `/api/admin/registro`, `/api/admin/login` | público |

## Estrutura
```
backend/  app.py (fábrica Flask) · avl.py (AVL manual) · service.py (regras) · database.py (SQLite)
          routes.py · admin_auth.py · config.py · tests/
frontend/ index.html · admin-cadastro.html · css/style.css · js/{api,arvore,app}.js
```
Dados persistem em SQLite (`backend/data/forum.db`); a AVL é reconstruída na inicialização.
Para PostgreSQL/MySQL, reescreva apenas `database.py`.

## Como a AVL funciona
Cada nó guarda tag, contador de uso e altura. **Fator de balanceamento (FB) = altura(esq) − altura(dir)**;
se |FB| > 1 após inserir/remover, rotaciona:

| Caso | Situação | Correção |
|---|---|---|
| **LL** | FB > 1 e filho esquerdo com FB ≥ 0 | rotação simples à direita |
| **RR** | FB < −1 e filho direito com FB ≤ 0 | rotação simples à esquerda |
| **LR** | FB > 1 e filho esquerdo com FB < 0 | esquerda no filho, depois direita no nó |
| **RL** | FB < −1 e filho direito com FB > 0 | direita no filho, depois esquerda no nó |

**Complexidade:** busca, inserção e remoção são **O(log n)** (altura ≤ ~1,44·log₂ n); o autocomplete por
prefixo poda a árvore e custa **O(log n + k)**; percurso em ordem é O(n). Tags são comparadas sem acento e sem
diferenciar maiúsculas (`Programação` = `programacao`); inserir uma tag existente apenas incrementa o uso.
Remoção trata folha, um filho e dois filhos (sucessor in-order).

## Testes
```bash
cd backend && python -m pytest -q     # 30 testes: AVL (LL/RR/LR/RL, remoções, 1500 operações aleatórias) e API
```

## Limitações conhecidas
* Use **um único processo** (a AVL fica em memória): `python app.py`, sem múltiplos workers do gunicorn.
* O servidor embutido do Flask é para desenvolvimento/demonstração.

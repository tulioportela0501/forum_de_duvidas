# Fórum Acadêmico — Dicionário de Tags com Árvore AVL

Projeto acadêmico de Estruturas de Dados. É um MVP de uma plataforma de fórum de dúvidas onde as tags dos tópicos ficam guardadas em uma **Árvore AVL implementada manualmente em Python**, sem usar `dict`, `set`, `sorted()` ou qualquer biblioteca de árvore pronta.

---

## 1. O problema

Em uma plataforma EAD, os estudantes criam tópicos categorizados por tags (`Cálculo1`, `EstruturaDeDados`, `Redes`). Conforme o usuário digita na barra de busca, o sistema precisa sugerir tags existentes em tempo real.

O problema não é a busca em si — é **a ordem em que as tags entram na estrutura**.

Estudantes tendem a copiar e colar sugestões anteriores, então as tags acabam sendo cadastradas em ordem alfabética. Se a estrutura for uma BST comum, inserir `aula1`, `aula10`, `aula11`, `aula12`... em ordem crescente produz isto:

```
aula1
   \
   aula10
      \
      aula11
         \
         aula12
            \
            ...
```

Cada nó novo vira o filho direito do anterior, porque nunca existe nada maior para forçar uma ramificação à esquerda. A árvore **degenera em uma lista encadeada**: altura `n` em vez de `log n`, e a busca cai de O(log n) para O(n). Com 20 tags, a altura é 20. Com 10.000 tags, é 10.000 — e em horário de pico, com milhares de requisições de autocompletação por segundo, isso trava.

## 2. Justificativa: por que AVL

A AVL é uma BST que se **auto-balanceia**. Ela garante, por construção, que a diferença de altura entre as subárvores esquerda e direita de qualquer nó nunca passa de 1.

Sempre que uma inserção ou remoção quebra essa propriedade, a árvore aplica **rotações** para se reorganizar. O resultado é que a altura fica presa em O(log n) **independentemente da ordem de entrada dos dados** — que é exatamente o cenário do nosso problema.

No cenário obrigatório do levantamento (`aula1`..`aula20` em ordem alfabética estrita), a BST teria altura 20. A nossa AVL termina com **altura 5**, usando 15 rotações. É um ganho de 4x já com 20 elementos, e a diferença cresce muito rápido.

## 3. Objetivo

Implementar o módulo de dicionário de tags baseado em AVL, com API REST em Flask e interface web, atendendo aos requisitos funcionais, não funcionais e regras de negócio do levantamento.

---

## 4. Como a AVL funciona neste projeto

### 4.1 Estrutura do nó

Cada nó (`backend/avl_tree.py`, classe `Node`) guarda:

| Campo | Para que serve |
|---|---|
| `key` | chave normalizada (minúscula) — usada em **toda** comparação |
| `display_name` | capitalização original do cadastro — usada só para exibir |
| `description` | descrição opcional da tag |
| `usage_count` | contador de uso (RF07) |
| `height` | altura do nó, base do cálculo do fator de balanceamento |
| `left` / `right` | ponteiros para os filhos |

A altura fica **armazenada** no nó em vez de ser recalculada. Se ela fosse recalculada recursivamente a cada consulta, cada verificação custaria O(n) e destruiria o ganho da AVL.

### 4.2 Fator de balanceamento (FB)

```
FB(nó) = altura(subárvore esquerda) − altura(subárvore direita)
```

Convenção usada: ponteiro nulo tem altura **0**, então uma folha tem altura **1**.

- `FB = +2` → o lado **esquerdo** pesou demais
- `FB = -2` → o lado **direito** pesou demais
- Após qualquer operação de escrita, todo nó deve ter `FB ∈ {-1, 0, 1}` (RNF05)

### 4.3 As quatro rotações

| Caso | Condição | Ação |
|---|---|---|
| **LL** | `FB(nó) = 2` e `FB(filho esq) ≥ 0` | rotação simples à **direita** |
| **RR** | `FB(nó) = -2` e `FB(filho dir) ≤ 0` | rotação simples à **esquerda** |
| **LR** | `FB(nó) = 2` e `FB(filho esq) < 0` | esquerda no filho, depois direita no nó |
| **RL** | `FB(nó) = -2` e `FB(filho dir) > 0` | direita no filho, depois esquerda no nó |

**Rotação simples à direita (caso LL):**

```
       y                 x
      / \               / \
     x   C    ==>      A   y
    / \                   / \
   A   B                 B   C
```

A subárvore `B` troca de pai: era filho direito de `x`, vira filho esquerdo de `y`. A ordem continua válida porque `A < x < B < y < C` antes e depois.

**Por que LR e RL precisam de duas rotações?** Porque nesses casos o desequilíbrio está no **neto**, não no filho. Uma rotação simples só empurraria o problema para o outro lado. A primeira rotação alinha o neto na mesma direção do desequilíbrio (transformando LR em LL), e aí a segunda rotação resolve.

No código, uma rotação dupla incrementa o contador de rotações em **2**, porque de fato são duas rotações simples encadeadas.

### 4.4 Onde o rebalanceamento acontece

`insert` e `delete` são recursivos. Na **volta** da recursão, cada nó ancestral no caminho chama `rebalance()`. Isso implementa a RN03 de forma natural: o balanceamento é avaliado do nó alterado até a raiz, aplicando no máximo uma rotação (simples ou dupla) por nível.

### 4.5 Busca por prefixo — o detalhe que importa

Este é o ponto onde é fácil "trapacear". A implementação ingênua seria listar todas as tags e filtrar — mas isso é O(n) e joga fora todo o benefício da árvore.

A implementação em `search_prefix()` usa a **ordenação da BST para podar subárvores**:

- **Poda à esquerda:** se `node.key < prefixo`, então tudo na subárvore esquerda também é menor que o prefixo. Como qualquer chave que começa com o prefixo é necessariamente `>= prefixo`, a subárvore esquerda inteira é descartada sem ser visitada.
- **Poda à direita:** se `node.key > prefixo` e `node.key` não começa com ele, então `node.key` é maior que **qualquer** string que comece com o prefixo — e tudo à direita é ainda maior. Descarta a subárvore direita inteira.

Na prática, a busca desce O(log n) até a faixa do prefixo e só então coleta os resultados em ordem.

---

## 5. Complexidade

| Operação | Pior caso | Observação |
|---|---|---|
| Busca exata | **O(log n)** | a altura é garantidamente logarítmica |
| Inserção | **O(log n)** | descida O(log n) + no máximo O(log n) rebalanceamentos |
| Remoção | **O(log n)** | idem, mais a busca do sucessor in-order |
| Listagem in-order | **O(n)** | precisa visitar todos os nós, por definição |
| Altura da árvore | **O(log n)** | limite teórico: `h ≤ 1.4405 · log₂(n+2)` |

### Busca por prefixo — atenção à complexidade

**Não é correto dizer O(log n).** A complexidade real é:

```
O(log n + k)
```

onde **k** é a quantidade de resultados retornados.

A razão: a parte O(log n) é a descida até a região do prefixo. Mas se o prefixo casa com `k` tags, a árvore precisa **visitar cada uma dessas k tags** para retorná-las — não existe atalho, já que cada resultado é um nó distinto. Se o usuário digitar `"a"` e existirem 5.000 tags começando com "a", a operação é O(log n + 5000).

Por isso o endpoint aceita um parâmetro `limit` (padrão 10): limitando a `k`, mantemos o tempo de resposta dentro do RNF03 (< 100 ms) mesmo em picos.

---

## 6. Instalação

Pré-requisito: **Python 3.10+**.

### Windows (PowerShell / terminal do VS Code)

```bash
python -m venv .venv
```

```bash
.venv\Scripts\activate
```

```bash
pip install -r requirements.txt
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> Se o PowerShell bloquear a ativação, rode uma vez:
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

## 7. Executar

Com o ambiente virtual ativado, na raiz do projeto:

```bash
python run.py
```

Depois abra no navegador: **http://127.0.0.1:5000**

## 8. Rodar os testes

```bash
python -m unittest discover -s tests -t . -v
```

Ou, se preferir pytest (`pip install pytest`):

```bash
pytest -v
```

São **37 testes**. O teste `test_relatorio_do_cenario` imprime o relatório completo do cenário obrigatório no terminal — é o que você mostra ao professor.

## 9. Git no terminal do VS Code

Abra a pasta do projeto no VS Code, abra o terminal integrado (`Ctrl + '`) e rode:

```bash
git init
git add .
git commit -m "feat: versão inicial do projeto"
```

Para conectar ao GitHub depois:

1. Crie um repositório **vazio** no GitHub (sem README, sem .gitignore — o projeto já tem os dois).
2. Copie a URL que o GitHub mostrar.
3. No terminal:

```bash
git branch -M main
git remote add origin <COLE_AQUI_A_URL_DO_SEU_REPOSITORIO>
git push -u origin main
```

O `.gitignore` já está configurado para não enviar `.venv/`, `__pycache__/`, `.env` nem arquivos de IDE.

---

## 10. Estrutura de arquivos

```text
forum-avl/
├── backend/
│   ├── __init__.py       # marca o pacote
│   ├── app.py            # fábrica Flask, serve a API e o frontend
│   ├── avl_tree.py       # ** A AVL — núcleo acadêmico do projeto **
│   ├── models.py         # normalização, validação (RN04) e serialização
│   ├── routes.py         # endpoints REST
│   └── services.py       # regras de negócio (RN01..RN04)
├── frontend/
│   ├── index.html        # interface
│   ├── css/style.css     # estilo
│   └── js/app.js         # fetch da API + debounce do autocomplete
├── tests/
│   ├── __init__.py
│   └── test_avl.py       # 37 testes unitários
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
└── run.py                # ponto de entrada: python run.py
```

### Por que essa separação em camadas

A AVL (`avl_tree.py`) **não sabe** que existe Flask, HTTP ou regra de negócio de fórum. Ela é uma estrutura de dados genérica e reutilizável.

A RN02 ("só remove com contador zero") mora em `services.py`, não na árvore. Se ela estivesse dentro de `delete()`, a AVL ficaria acoplada a uma regra específica deste projeto e não serviria para mais nada.

Isso atende ao RNF06 e é o que vai permitir plugar SQLite/MySQL/PostgreSQL depois sem tocar em uma linha de `avl_tree.py`.

---

## 11. API

Base: `http://127.0.0.1:5000/api`

| Método | Endpoint | Descrição | Requisito |
|---|---|---|---|
| `POST` | `/tags` | Cadastra tag ou incrementa uso se já existir. Body: `{"tag": "...", "description": "..."}`. Retorna **201** se criou, **200** se já existia | RF01, RF07, RF08 |
| `GET` | `/tags` | Lista todas as tags em ordem alfabética (in-order) | RF06 |
| `GET` | `/tags/search?q=&limit=` | Autocompletação por prefixo | RF05 |
| `GET` | `/tags/<tag>` | Busca exata (case-insensitive). **404** se não existir | RF04 |
| `POST` | `/tags/<tag>/use` | Incrementa o contador (tag associada a novo tópico) | RF07, UC01 |
| `POST` | `/tags/<tag>/unuse` | Decrementa o contador (tópico excluído) | UC03 |
| `DELETE` | `/tags/<tag>` | Remove a tag. **400** se o contador for maior que zero | RF03, RN02 |
| `GET` | `/avl` | Estrutura da árvore com altura e FB de cada nó (JSON + texto) | RF09, UC04 |
| `GET` | `/metrics` | Altura, nº de nós, nº de rotações, validação do FB | RF10 |
| `POST` | `/seed` | Carrega o cenário `aula1..aula20` (apoio à demonstração) | item 5.4 |
| `POST` | `/reset` | Limpa o dicionário (apoio à demonstração) | — |

`/seed` e `/reset` não são requisitos do levantamento — foram adicionados só para facilitar a demonstração ao vivo.

---

## 12. Mapa de requisitos

### Requisitos Funcionais

| Requisito | Implementação | Arquivo |
|---|---|---|
| RF01 | Inserção de tag mantendo ordem lexicográfica | `backend/avl_tree.py` → `insert()` / `_insert()` |
| RF02 | Balanceamento automático (LL, RR, LR, RL) | `backend/avl_tree.py` → `rebalance()`, `rotate_left()`, `rotate_right()` |
| RF03 | Remoção com rebalanceamento | `backend/avl_tree.py` → `delete()` / `_delete()` |
| RF04 | Busca exata O(log n) | `backend/avl_tree.py` → `search()` |
| RF05 | Busca por prefixo com poda de subárvores | `backend/avl_tree.py` → `search_prefix()` |
| RF06 | Percurso in-order | `backend/avl_tree.py` → `in_order()` |
| RF07 | Contador de uso | `Node.usage_count`; `services.py` → `increment_usage()` / `decrement_usage()` |
| RF08 | Prevenção de duplicidade (incrementa em vez de duplicar) | `backend/avl_tree.py` → `_insert()` (ramo `else`) |
| RF09 | Visualização da árvore com altura e FB | `backend/avl_tree.py` → `to_dict()` / `to_text()`; `GET /api/avl` |
| RF10 | Métricas (altura e rotações) | `backend/avl_tree.py` → `metrics()`, `rotation_count`; `GET /api/metrics` |

### Requisitos Não Funcionais

| Requisito | Como é atendido | Onde |
|---|---|---|
| RNF01 | Busca exata iterativa em árvore de altura logarítmica | `avl_tree.py` → `search()`; teste `test_altura_logaritmica` |
| RNF02 | Inserção/remoção com rebalanceamento O(log n) | `avl_tree.py` → `_insert()`, `_delete()`, `rebalance()` |
| RNF03 | Debounce de 250 ms no frontend + `limit` no backend | `frontend/js/app.js` → `debounce()`; `services.py` → `search_prefix()` |
| RNF04 | Altura O(log n) suporta dezenas de milhares de tags | validado em `test_altura_logaritmica` (1000 nós) |
| RNF05 | `FB ∈ {-1,0,1}` em 100% dos nós após escrita | `avl_tree.py` → `is_balanced()`; `TestBalanceamento` |
| RNF06 | AVL totalmente independente de banco e de Flask | `avl_tree.py` não importa nada externo |
| RNF07 | Cada rotação testada isoladamente | `tests/test_avl.py` → `TestRotacoes` |

### Regras de Negócio

| Regra | Implementação | Arquivo | Teste |
|---|---|---|---|
| RN01 | `casefold()` na chave + `display_name` com a capitalização original | `models.py` → `normalize()`; `Node` | `test_insercao_case_insensitive`, `test_busca_case_insensitive` |
| RN02 | Remoção bloqueada se `usage_count > 0` | `services.py` → `remove_tag()` | `test_rn02_bloqueia_remocao_com_contador_maior_que_zero` |
| RN03 | Rebalanceamento na volta da recursão, do nó até a raiz | `avl_tree.py` → `_insert()`, `_delete()`, `rebalance()` | `TestBalanceamento` |
| RN04 | Tags com menos de 2 caracteres rejeitadas | `models.py` → `validate_tag()` | `test_tag_curta_rejeitada` |

### Casos de Uso

| UC | Onde aparece |
|---|---|
| UC01 — Cadastrar tag em novo tópico | `POST /api/tags` + botão "Adicionar tag" |
| UC02 — Buscar tag por prefixo | `GET /api/tags/search` + barra de busca com autocomplete |
| UC03 — Remover tag órfã | `POST /tags/<tag>/unuse` até zerar, depois `DELETE /tags/<tag>` |
| UC04 — Auditar estrutura da árvore | `GET /api/avl` + `GET /api/metrics` + área de debug da interface |

---

## 13. Cenário de teste obrigatório (item 5.4 do levantamento)

Inserindo `aula1` até `aula20` em **ordem alfabética estrita** — justamente o padrão que destrói uma BST comum:

```
Altura da AVL ....... 5
Número de nós ....... 20
Rotações realizadas . 15
FB válido em todos .. True
Altura de uma BST comum nesse cenário: 20 (lista encadeada)
```

Estrutura resultante (saída real do `to_text()`):

```
[raiz] aula16 (h=5, FB=-1, uso=1)
    [E] aula12 (h=3, FB=0, uso=1)
        [E] aula10 (h=2, FB=0, uso=1)
            [E] aula1 (h=1, FB=0, uso=1)
            [D] aula11 (h=1, FB=0, uso=1)
        [D] aula14 (h=2, FB=0, uso=1)
            [E] aula13 (h=1, FB=0, uso=1)
            [D] aula15 (h=1, FB=0, uso=1)
    [D] aula5 (h=4, FB=0, uso=1)
        [E] aula2 (h=3, FB=0, uso=1)
            [E] aula18 (h=2, FB=0, uso=1)
                [E] aula17 (h=1, FB=0, uso=1)
                [D] aula19 (h=1, FB=0, uso=1)
            [D] aula3 (h=2, FB=0, uso=1)
                [E] aula20 (h=1, FB=0, uso=1)
                [D] aula4 (h=1, FB=0, uso=1)
        [D] aula7 (h=3, FB=-1, uso=1)
            [E] aula6 (h=1, FB=0, uso=1)
            [D] aula8 (h=2, FB=-1, uso=1)
                [D] aula9 (h=1, FB=0, uso=1)
```

**Leitura do resultado:** repare que `aula16` virou a raiz, mesmo tendo sido a 12ª tag inserida (na ordem alfabética, `aula16` vem depois de `aula15` e antes de `aula17`). Isso só aconteceu porque as rotações promoveram nós do meio para o topo conforme a árvore crescia para um lado só. Todos os FB estão em `{-1, 0, 1}`.

**Observação sobre a ordem:** `aula1..aula20` em ordem *alfabética* não é a ordem numérica — é `aula1, aula10, aula11, ..., aula19, aula2, aula20, aula3, ...`. O teste usa `sorted()` apenas para ordenar a **entrada** do experimento; a estrutura de dados do sistema continua sendo exclusivamente a AVL.

Para ver ao vivo: clique em **"Carregar cenário aula1..aula20"** na interface e olhe a área de debug.

Reproduzir no terminal:

```bash
python -m unittest tests.test_avl.TestCenarioObrigatorio -v
```

---

## 14. Limitações do MVP

Coisas que conscientemente **não** foram feitas nesta versão, por estarem fora do escopo combinado:

- **Dados em memória.** Reiniciar o servidor apaga tudo. A separação em camadas já deixa isso pronto para receber persistência.
- **Sem usuários, login ou autenticação.** Qualquer um que acessar pode cadastrar e remover tags.
- **Sem sistema de tópicos.** Os botões `+` e `−` *simulam* a associação/desassociação de tópicos; não existe entidade Tópico de verdade.
- **Instância única do serviço.** Se o Flask rodar com múltiplos workers, cada um teria sua própria árvore. Para desenvolvimento e apresentação, tudo bem.
- **Sem controle de concorrência.** A AVL não tem lock. Escritas simultâneas de threads diferentes poderiam corromper a estrutura.
- **Descrição só do primeiro cadastro.** Se a tag já existe, uma nova descrição só é gravada caso a anterior esteja vazia.

## 15. Melhorias futuras

- Persistência em SQLite, com reconstrução da AVL na inicialização
- Entidade Tópico real, com o contador de uso derivado das associações
- Comparar AVL vs BST comum lado a lado na interface, com gráfico de altura
- Animação das rotações no frontend (ótimo para a apresentação)
- Contadores separados de rotações por tipo (LL / RR / LR / RL)
- Cache das sugestões de autocompletação mais frequentes
- Lock de leitura/escrita para acesso concorrente
- Busca por similaridade (distância de Levenshtein) para erros de digitação

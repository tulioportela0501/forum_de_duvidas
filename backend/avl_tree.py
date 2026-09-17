# =============================================================================
# avl_tree.py
# -----------------------------------------------------------------------------
# Implementacao MANUAL de uma Arvore AVL usada como dicionario de tags.
#
# Este modulo e PURO: ele nao conhece Flask, nao conhece HTTP e nao conhece
# banco de dados. Isso atende ao RNF06 (portabilidade / independencia de banco):
# a estrutura pode ser mantida em memoria hoje e persistida depois sem que
# uma unica linha deste arquivo precise mudar.
#
# Nao e usado nenhum dict/set/list como estrutura principal, nem sorted(),
# nem biblioteca pronta de arvore. A ordenacao vem da propria propriedade
# de arvore binaria de busca + percurso in-order.
# =============================================================================


class Node:
    # Representa um unico no da AVL.
    # Conforme o item 5.1 do levantamento, o no precisa guardar no minimo:
    # chave, altura, contador de uso e os dois ponteiros de filho.
    def __init__(self, key, display_name=None, description=""):
        # 'key' e a chave NORMALIZADA (minuscula), usada para TODA comparacao.
        # E ela que garante o RN01: "Redes" e "redes" caem no mesmo no.
        self.key = key

        # 'display_name' guarda a capitalizacao ORIGINAL do cadastro.
        # Tambem exigido pelo RN01: comparamos sem case, mas exibimos com case.
        self.display_name = display_name if display_name is not None else key

        # Descricao opcional da tag (campo extra previsto na interface).
        self.description = description

        # Contador de uso (RF07). Comeca em 1 porque, quando uma tag e criada,
        # ela ja esta sendo associada ao topico que motivou a criacao.
        self.usage_count = 1

        # Altura do no. Um no folha tem altura 1.
        # Guardamos a altura em vez de recalcular recursivamente porque
        # recalcular custaria O(n) por consulta e destruiria o O(log n).
        self.height = 1

        # Ponteiros para os filhos (ponteiroEsquerda / ponteiroDireita).
        self.left = None
        self.right = None


class AVLTree:
    # Arvore AVL completa, com todas as operacoes exigidas no item 6 do prompt.

    def __init__(self):
        # Raiz da arvore. None significa arvore vazia.
        self.root = None

        # Quantidade de nos distintos (nao soma contadores de uso).
        self.size = 0

        # Metrica do RF10: total acumulado de rotacoes ja executadas.
        # Uma rotacao dupla (LR/RL) conta como 2, porque de fato sao
        # duas rotacoes simples encadeadas.
        self.rotation_count = 0

    # -------------------------------------------------------------------------
    # UTILITARIOS DE ALTURA E BALANCEAMENTO
    # -------------------------------------------------------------------------

    def get_height(self, node):
        # Retorna a altura de um no de forma segura.
        # Convencionamos altura 0 para o ponteiro nulo, de modo que uma folha
        # (que tem dois filhos nulos) fique com altura 1.
        if node is None:
            return 0
        return node.height

    def update_height(self, node):
        # Recalcula a altura do no a partir das alturas ja conhecidas dos filhos.
        # Deve ser chamada SEMPRE que a estrutura abaixo do no mudar
        # (apos insercao, remocao ou rotacao), senao o fator de balanceamento
        # passa a ser calculado com dados desatualizados.
        node.height = 1 + max(self.get_height(node.left), self.get_height(node.right))

    def get_balance(self, node):
        # Calcula o fator de balanceamento do no (item 5.2 do levantamento):
        #     FB(no) = altura(subarvore esquerda) - altura(subarvore direita)
        # Um FB de +2 indica que o lado esquerdo pesou demais;
        # um FB de -2 indica que o lado direito pesou demais.
        if node is None:
            return 0
        return self.get_height(node.left) - self.get_height(node.right)

    # -------------------------------------------------------------------------
    # ROTACOES (item 5.3 do levantamento)
    # -------------------------------------------------------------------------

    def rotate_right(self, node):
        # Realiza uma rotacao simples para a direita, usada quando a arvore
        # apresenta um desequilibrio do tipo LL (o peso esta na esquerda da
        # esquerda). O filho esquerdo sobe e vira a nova raiz da subarvore;
        # o no desbalanceado desce para a direita dele.
        #
        #        y                x
        #       / \              / \
        #      x   C    ==>     A   y
        #     / \                  / \
        #    A   B                B   C
        #
        # O subarvore B "troca de pai": era filho direito de x, vira filho
        # esquerdo de y. Isso preserva a ordem da BST porque A < x < B < y < C.
        y = node
        x = y.left
        B = x.right

        x.right = y
        y.left = B

        # A ordem importa: y ficou mais embaixo, entao a altura dele
        # precisa ser recalculada ANTES da altura de x.
        self.update_height(y)
        self.update_height(x)

        self.rotation_count += 1
        return x  # x e a nova raiz desta subarvore

    def rotate_left(self, node):
        # Realiza uma rotacao simples para a esquerda, usada no desequilibrio
        # do tipo RR (peso na direita da direita). E o espelho exato de
        # rotate_right: o filho direito sobe e o no desce para a esquerda.
        #
        #      x                    y
        #     / \                  / \
        #    A   y      ==>       x   C
        #       / \              / \
        #      B   C            A   B
        x = node
        y = x.right
        B = y.left

        y.left = x
        x.right = B

        self.update_height(x)
        self.update_height(y)

        self.rotation_count += 1
        return y  # y e a nova raiz desta subarvore

    def rebalance(self, node):
        # Verifica o fator de balanceamento do no e, se ele estourou (+-2),
        # aplica exatamente um dos quatro casos de rotacao.
        #
        # Esta funcao e chamada na volta da recursao de insert/remove, o que
        # implementa o RN03: o balanceamento e avaliado do no alterado ate a
        # raiz, aplicando no maximo uma rotacao (simples ou dupla) por nivel.
        self.update_height(node)
        balance = self.get_balance(node)

        # --- Caso LL: o no pesa para a esquerda e o filho esquerdo tambem
        # (ou esta neutro). Uma unica rotacao a direita resolve.
        if balance == 2 and self.get_balance(node.left) >= 0:
            return self.rotate_right(node)

        # --- Caso LR: o no pesa para a esquerda, mas o filho esquerdo pesa
        # para a DIREITA. Uma rotacao simples nao resolveria (o problema esta
        # no neto). Primeiro endireitamos o filho, depois giramos o no.
        if balance == 2 and self.get_balance(node.left) < 0:
            node.left = self.rotate_left(node.left)
            return self.rotate_right(node)

        # --- Caso RR: espelho do LL.
        if balance == -2 and self.get_balance(node.right) <= 0:
            return self.rotate_left(node)

        # --- Caso RL: espelho do LR.
        if balance == -2 and self.get_balance(node.right) > 0:
            node.right = self.rotate_right(node.right)
            return self.rotate_left(node)

        # No ja estava dentro de {-1, 0, 1}: nada a fazer.
        return node

    # -------------------------------------------------------------------------
    # RF01 / RF02 / RF08 — INSERCAO COM BALANCEAMENTO E ANTI-DUPLICIDADE
    # -------------------------------------------------------------------------

    def insert(self, key, display_name=None, description=""):
        # Insere uma tag mantendo a ordem lexicografica (RF01) e rebalanceando
        # automaticamente (RF02).
        #
        # Se a chave ja existir, NAO cria outro no: apenas incrementa o
        # contador de uso (RF08). Retorna True se um no novo foi criado e
        # False se a tag ja existia, para que a camada de servico saiba
        # diferenciar "criada" de "reutilizada".
        created = {"value": False}
        self.root = self._insert(self.root, key, display_name, description, created)
        if created["value"]:
            self.size += 1
        return created["value"]

    def _insert(self, node, key, display_name, description, created):
        # Descida recursiva padrao de BST: compara a chave e desce para o lado
        # correto ate encontrar um ponto nulo onde o no cabe.
        if node is None:
            created["value"] = True
            return Node(key, display_name, description)

        if key < node.key:
            node.left = self._insert(node.left, key, display_name, description, created)
        elif key > node.key:
            node.right = self._insert(node.right, key, display_name, description, created)
        else:
            # Chave igual => tag duplicada (RF08 + RN01).
            # Nao criamos no novo; so incrementamos o uso. A capitalizacao
            # original do PRIMEIRO cadastro e preservada de proposito.
            node.usage_count += 1
            if description and not node.description:
                node.description = description
            return node

        # Na volta da recursao, cada ancestral afetado se rebalanceia.
        return self.rebalance(node)

    # -------------------------------------------------------------------------
    # RF04 — BUSCA EXATA
    # -------------------------------------------------------------------------

    def search(self, key):
        # Busca exata em O(log n) (RF04 / RNF01). Escrita de forma iterativa
        # para evitar custo de pilha de recursao no caminho mais quente do
        # sistema. A cada comparacao descartamos metade da arvore.
        node = self.root
        while node is not None:
            if key < node.key:
                node = node.left
            elif key > node.key:
                node = node.right
            else:
                return node
        return None

    # -------------------------------------------------------------------------
    # SUPORTE A REMOCAO — MENOR NO DA SUBARVORE (SUCESSOR)
    # -------------------------------------------------------------------------

    def _min_value_node(self, node):
        # Retorna o no de menor chave de uma subarvore, ou seja, o filho mais
        # a esquerda. Usado para achar o SUCESSOR in-order na remocao de um
        # no com dois filhos: o sucessor e o menor elemento da subarvore
        # direita, e e o unico valor que pode ocupar o lugar do removido sem
        # quebrar a ordenacao.
        current = node
        while current.left is not None:
            current = current.left
        return current

    # -------------------------------------------------------------------------
    # RF03 — REMOCAO COM REBALANCEAMENTO
    # -------------------------------------------------------------------------

    def delete(self, key):
        # Remove fisicamente um no da arvore e rebalanceia o caminho ate a raiz.
        #
        # ATENCAO: esta funcao NAO conhece a RN02 (so remover com contador
        # zerado). Essa e uma regra de NEGOCIO e vive em services.py.
        # A estrutura de dados deve continuar generica e reutilizavel.
        removed = {"value": False}
        self.root = self._delete(self.root, key, removed)
        if removed["value"]:
            self.size -= 1
        return removed["value"]

    def _delete(self, node, key, removed):
        if node is None:
            return None  # chave inexistente: nada muda

        if key < node.key:
            node.left = self._delete(node.left, key, removed)
        elif key > node.key:
            node.right = self._delete(node.right, key, removed)
        else:
            # Achamos o no alvo. Ha tres situacoes classicas:
            removed["value"] = True

            # (1) e (2): no folha ou no com apenas um filho.
            # Basta promover o filho existente (ou None) para o lugar do no.
            if node.left is None:
                return node.right
            if node.right is None:
                return node.left

            # (3) no com DOIS filhos: nao podemos simplesmente apagar.
            # Copiamos os dados do sucessor in-order para este no e, em
            # seguida, removemos o sucessor da subarvore direita — que
            # cai obrigatoriamente no caso (1) ou (2), pois o menor no
            # nunca tem filho esquerdo.
            successor = self._min_value_node(node.right)
            node.key = successor.key
            node.display_name = successor.display_name
            node.description = successor.description
            node.usage_count = successor.usage_count
            node.right = self._delete(node.right, successor.key, {"value": False})

        # Rebalanceia na volta da recursao (RN03).
        return self.rebalance(node)

    # -------------------------------------------------------------------------
    # RF06 — PERCURSO IN-ORDER
    # -------------------------------------------------------------------------

    def in_order(self):
        # Percorre a arvore em ordem (esquerda -> raiz -> direita), o que
        # produz a listagem alfabetica completa sem precisar de sorted().
        # A ordenacao e consequencia direta da propriedade da BST.
        result = []
        self._in_order(self.root, result)
        return result

    def _in_order(self, node, result):
        if node is None:
            return
        self._in_order(node.left, result)
        result.append(node)
        self._in_order(node.right, result)

    # -------------------------------------------------------------------------
    # RF05 — BUSCA POR PREFIXO (AUTOCOMPLETACAO)
    # -------------------------------------------------------------------------

    def search_prefix(self, prefix, limit=None):
        # Retorna todas as tags que comecam com o prefixo, em ordem alfabetica.
        #
        # O ponto academico importante: NAO percorremos a arvore inteira.
        # Usamos a ordenacao da BST para PODAR subarvores:
        #
        #   - se a maior chave possivel da subarvore esquerda ainda for menor
        #     que o prefixo, a esquerda inteira e descartada;
        #   - se a chave do no ja e lexicograficamente maior que o prefixo
        #     "esgotado", a direita inteira e descartada.
        #
        # Na pratica isso significa descer O(log n) ate a regiao do prefixo e
        # so entao coletar os resultados em ordem.
        result = []
        self._search_prefix(self.root, prefix, result, limit)
        return result

    def _search_prefix(self, node, prefix, result, limit):
        if node is None:
            return
        if limit is not None and len(result) >= limit:
            return

        # PODA A ESQUERDA: so vale descer para a esquerda se ainda existir
        # chance de encontrar chaves >= prefixo la. Se a chave do no ja e
        # menor que o prefixo, tudo a esquerda dele tambem e, e nao interessa.
        if node.key >= prefix:
            self._search_prefix(node.left, prefix, result, limit)

        if limit is not None and len(result) >= limit:
            return

        # O proprio no entra no resultado se casar com o prefixo.
        if node.key.startswith(prefix):
            result.append(node)

        # PODA A DIREITA: se a chave do no ja ultrapassou lexicograficamente
        # a faixa do prefixo (e nao e do prefixo), nada a direita servira,
        # porque tudo la e ainda maior.
        if node.key < prefix or node.key.startswith(prefix):
            self._search_prefix(node.right, prefix, result, limit)

    # -------------------------------------------------------------------------
    # RF09 — VISUALIZACAO DA ARVORE (MODO DEBUG / ACADEMICO)
    # -------------------------------------------------------------------------

    def to_dict(self):
        # Serializa a arvore como dicionario aninhado, incluindo altura e
        # fator de balanceamento de cada no. E o que alimenta a area de
        # debug da interface e permite ao professor auditar a estrutura (UC04).
        return self._to_dict(self.root, 0)

    def _to_dict(self, node, level):
        if node is None:
            return None
        return {
            "tag": node.display_name,
            "key": node.key,
            "usage_count": node.usage_count,
            "height": node.height,
            "balance": self.get_balance(node),
            "level": level,
            "left": self._to_dict(node.left, level + 1),
            "right": self._to_dict(node.right, level + 1),
        }

    def to_text(self):
        # Versao textual indentada da arvore, util para imprimir no terminal
        # durante a apresentacao do trabalho.
        lines = []
        self._to_text(self.root, 0, "raiz", lines)
        return "\n".join(lines) if lines else "(arvore vazia)"

    def _to_text(self, node, level, side, lines):
        if node is None:
            return
        indent = "    " * level
        lines.append(
            f"{indent}[{side}] {node.display_name} "
            f"(h={node.height}, FB={self.get_balance(node)}, uso={node.usage_count})"
        )
        self._to_text(node.left, level + 1, "E", lines)
        self._to_text(node.right, level + 1, "D", lines)

    # -------------------------------------------------------------------------
    # RF10 / RNF05 — METRICAS E VALIDACAO ESTRUTURAL
    # -------------------------------------------------------------------------

    def metrics(self):
        # Reune as metricas exigidas pelo RF10: altura atual, numero de nos e
        # total de rotacoes. A altura e o dado que prova, na apresentacao, que
        # a arvore nao degenerou em lista encadeada.
        return {
            "height": self.get_height(self.root),
            "node_count": self.size,
            "rotations": self.rotation_count,
            "total_usage": sum(n.usage_count for n in self.in_order()),
        }

    def is_balanced(self):
        # Valida o RNF05: verifica se TODOS os nos respeitam FB ∈ {-1, 0, 1}.
        # Tambem confere se a altura armazenada em cada no bate com a altura
        # real — um erro classico e rebalancear certo mas esquecer de
        # atualizar a altura, e ai o FB passa a mentir.
        return self._is_balanced(self.root)

    def _is_balanced(self, node):
        if node is None:
            return True
        if abs(self.get_balance(node)) > 1:
            return False
        expected = 1 + max(self.get_height(node.left), self.get_height(node.right))
        if node.height != expected:
            return False
        return self._is_balanced(node.left) and self._is_balanced(node.right)

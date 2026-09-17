# =============================================================================
# services.py
# -----------------------------------------------------------------------------
# Camada de servico: e aqui que as REGRAS DE NEGOCIO (RN01..RN04) sao
# aplicadas em cima da estrutura de dados.
#
# Por que separar isso da AVL? Porque a AVL e uma estrutura generica e
# reutilizavel: ela nao deveria saber que "so se remove tag com contador
# zero". Se amanha o projeto usar a mesma AVL para outra coisa, as regras
# do forum nao vao junto.
# =============================================================================

from .avl_tree import AVLTree
from .models import TagValidationError, normalize, serialize_node, validate_tag


class TagService:
    # Fachada usada pelas rotas Flask. Guarda a AVL em memoria (suficiente
    # para o MVP, conforme item 13 do escopo) e expoe operacoes de negocio.

    def __init__(self):
        self.tree = AVLTree()

    # -------------------------------------------------------------------------
    # RF01 / RF07 / RF08 — CADASTRAR OU REUTILIZAR TAG
    # -------------------------------------------------------------------------

    def add_tag(self, raw_tag, description=""):
        # Cadastra uma tag nova OU incrementa o uso de uma tag existente.
        #
        # Fluxo de regras:
        #   1. valida tamanho minimo (RN04) via validate_tag;
        #   2. normaliza para comparacao case-insensitive (RN01);
        #   3. delega a insercao para a AVL, que ja trata duplicidade (RF08)
        #      incrementando o contador de uso (RF07) em vez de criar no novo.
        display = validate_tag(raw_tag)
        key = normalize(display)

        created = self.tree.insert(key, display, (description or "").strip())
        node = self.tree.search(key)

        return {
            "created": created,   # True = tag nova; False = ja existia
            "tag": serialize_node(node),
        }

    # -------------------------------------------------------------------------
    # RF04 — BUSCA EXATA
    # -------------------------------------------------------------------------

    def get_tag(self, raw_tag):
        # Busca exata. Normaliza antes de consultar para que "Redes" encontre
        # o no cadastrado como "redes" (RN01).
        node = self.tree.search(normalize(raw_tag or ""))
        return serialize_node(node) if node else None

    # -------------------------------------------------------------------------
    # RF05 — AUTOCOMPLETACAO POR PREFIXO
    # -------------------------------------------------------------------------

    def search_prefix(self, prefix, limit=10):
        # Retorna sugestoes para a barra de busca.
        #
        # Prefixo vazio devolve lista vazia de proposito: sem isso, cada vez
        # que o usuario apagasse o campo o backend devolveria o dicionario
        # inteiro, o que atrapalha o RNF03 (resposta < 100 ms).
        normalized = normalize(prefix or "")
        if not normalized:
            return []
        nodes = self.tree.search_prefix(normalized, limit=limit)
        return [serialize_node(n) for n in nodes]

    # -------------------------------------------------------------------------
    # RF06 — LISTAGEM ALFABETICA
    # -------------------------------------------------------------------------

    def list_tags(self):
        # Listagem completa em ordem alfabetica via percurso in-order.
        return [serialize_node(n) for n in self.tree.in_order()]

    # -------------------------------------------------------------------------
    # RF07 — INCREMENTO EXPLICITO DE USO
    # -------------------------------------------------------------------------

    def increment_usage(self, raw_tag):
        # Simula "a tag foi associada a mais um topico" (RF07 / UC01).
        node = self.tree.search(normalize(raw_tag or ""))
        if node is None:
            return None
        node.usage_count += 1
        return serialize_node(node)

    def decrement_usage(self, raw_tag):
        # Simula "um topico que usava a tag foi excluido" (UC03).
        # Nunca deixamos o contador ficar negativo.
        node = self.tree.search(normalize(raw_tag or ""))
        if node is None:
            return None
        if node.usage_count > 0:
            node.usage_count -= 1
        return serialize_node(node)

    # -------------------------------------------------------------------------
    # RF03 + RN02 — REMOCAO CONDICIONADA AO CONTADOR DE USO
    # -------------------------------------------------------------------------

    def remove_tag(self, raw_tag):
        # Remove a tag do dicionario, MAS apenas se o contador de uso estiver
        # zerado (RN02). Se algum topico ainda referencia a tag, a remocao e
        # bloqueada — apagar a tag nesse caso deixaria topicos orfaos.
        key = normalize(raw_tag or "")
        node = self.tree.search(key)

        if node is None:
            raise TagValidationError("Tag nao encontrada.")

        if node.usage_count > 0:
            raise TagValidationError(
                f"A tag '{node.display_name}' ainda e usada por "
                f"{node.usage_count} topico(s) e nao pode ser removida (RN02)."
            )

        # Contador zerado: agora sim a estrutura pode apagar o no e
        # se rebalancear (RF03 / RN03).
        self.tree.delete(key)
        return True

    # -------------------------------------------------------------------------
    # RF09 / RF10 — AUDITORIA E METRICAS
    # -------------------------------------------------------------------------

    def tree_view(self):
        # Estrutura da arvore com altura e FB de cada no (RF09 / UC04).
        return {
            "tree": self.tree.to_dict(),
            "text": self.tree.to_text(),
        }

    def metrics(self):
        # Metricas do RF10 + validacao do RNF05 num unico payload.
        data = self.tree.metrics()
        data["is_balanced"] = self.tree.is_balanced()
        return data

    def reset(self):
        # Zera o dicionario. Util durante a apresentacao, para demonstrar o
        # cenario obrigatorio (aula1..aula20) com metricas limpas.
        self.tree = AVLTree()

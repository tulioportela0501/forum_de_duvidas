# =============================================================================
# test_avl.py
# -----------------------------------------------------------------------------
# Testes unitarios do nucleo academico do projeto.
#
# Executar com:   python -m unittest discover -s tests -v
#            ou:  pytest -v
# =============================================================================

import unittest

from backend.avl_tree import AVLTree
from backend.models import TagValidationError
from backend.services import TagService


def keys(tree):
    # Helper: devolve a lista de chaves em ordem alfabetica (percurso in-order).
    return [n.key for n in tree.in_order()]


# =============================================================================
# INSERCAO (RF01, RF02, RF08, RN01, RN04)
# =============================================================================
class TestInsercao(unittest.TestCase):

    def setUp(self):
        self.service = TagService()

    def test_insercao_normal(self):
        # Insercao simples deve criar o no e manter a ordem lexicografica.
        self.service.add_tag("Redes")
        self.service.add_tag("Algoritmos")
        self.service.add_tag("Calculo1")
        self.assertEqual(keys(self.service.tree), ["algoritmos", "calculo1", "redes"])
        self.assertEqual(self.service.tree.size, 3)

    def test_insercao_duplicada_nao_cria_no(self):
        # RF08: tag repetida nao gera no novo, apenas incrementa o contador.
        self.service.add_tag("Redes")
        resultado = self.service.add_tag("Redes")
        self.assertFalse(resultado["created"])
        self.assertEqual(self.service.tree.size, 1)
        self.assertEqual(resultado["tag"]["usage_count"], 2)

    def test_insercao_case_insensitive(self):
        # RN01: "Redes" e "redes" sao a mesma tag, mas a capitalizacao
        # do primeiro cadastro e preservada para exibicao.
        self.service.add_tag("Redes")
        resultado = self.service.add_tag("redes")
        self.assertFalse(resultado["created"])
        self.assertEqual(self.service.tree.size, 1)
        self.assertEqual(resultado["tag"]["tag"], "Redes")
        self.assertEqual(resultado["tag"]["usage_count"], 2)

    def test_tag_curta_rejeitada(self):
        # RN04: tags com menos de 2 caracteres nao sao aceitas.
        with self.assertRaises(TagValidationError):
            self.service.add_tag("a")
        with self.assertRaises(TagValidationError):
            self.service.add_tag("   ")
        self.assertEqual(self.service.tree.size, 0)

    def test_tag_com_dois_caracteres_aceita(self):
        # Limite exato da RN04: 2 caracteres deve passar.
        self.service.add_tag("IA")
        self.assertEqual(self.service.tree.size, 1)


# =============================================================================
# BUSCA (RF04, RF05, RF06)
# =============================================================================
class TestBusca(unittest.TestCase):

    def setUp(self):
        self.service = TagService()
        for tag in ["Algoritmos", "Algebra", "AlgoritmoGenetico", "Redes", "Banco"]:
            self.service.add_tag(tag)

    def test_busca_tag_existente(self):
        self.assertIsNotNone(self.service.get_tag("Redes"))

    def test_busca_tag_inexistente(self):
        self.assertIsNone(self.service.get_tag("Compiladores"))

    def test_busca_case_insensitive(self):
        # RN01 aplicada tambem na leitura.
        self.assertIsNotNone(self.service.get_tag("REDES"))
        self.assertIsNotNone(self.service.get_tag("rEdEs"))

    def test_busca_por_prefixo_ordenada(self):
        # RF05: retorna todas as tags com o prefixo, em ordem alfabetica.
        sugestoes = [s["key"] for s in self.service.search_prefix("alg")]
        self.assertEqual(sugestoes, ["algebra", "algoritmogenetico", "algoritmos"])

    def test_busca_por_prefixo_sem_resultado(self):
        self.assertEqual(self.service.search_prefix("zzz"), [])

    def test_busca_por_prefixo_respeita_limite(self):
        self.assertEqual(len(self.service.search_prefix("alg", limit=2)), 2)

    def test_prefixo_vazio_nao_retorna_tudo(self):
        self.assertEqual(self.service.search_prefix(""), [])

    def test_listagem_em_ordem(self):
        # RF06: percurso in-order produz a ordem alfabetica.
        listagem = [t["key"] for t in self.service.list_tags()]
        self.assertEqual(listagem, sorted(listagem))


# =============================================================================
# REMOCAO (RF03, RN02, RN03)
# =============================================================================
class TestRemocao(unittest.TestCase):

    def setUp(self):
        self.tree = AVLTree()

    def test_remover_no_folha(self):
        for k in ["m", "c", "t"]:
            self.tree.insert(k)
        self.tree.delete("c")  # "c" e folha
        self.assertEqual(keys(self.tree), ["m", "t"])
        self.assertTrue(self.tree.is_balanced())

    def test_remover_no_com_um_filho(self):
        for k in ["m", "c", "t", "a"]:
            self.tree.insert(k)
        self.tree.delete("c")  # "c" tem apenas o filho "a"
        self.assertEqual(keys(self.tree), ["a", "m", "t"])
        self.assertTrue(self.tree.is_balanced())

    def test_remover_no_com_dois_filhos(self):
        for k in ["m", "c", "t", "a", "e", "p", "z"]:
            self.tree.insert(k)
        self.tree.delete("c")  # "c" tem filhos "a" e "e"
        self.assertEqual(keys(self.tree), ["a", "e", "m", "p", "t", "z"])
        self.assertTrue(self.tree.is_balanced())

    def test_remover_raiz_com_dois_filhos(self):
        for k in ["m", "c", "t"]:
            self.tree.insert(k)
        self.tree.delete("m")
        self.assertEqual(keys(self.tree), ["c", "t"])
        self.assertTrue(self.tree.is_balanced())

    def test_remover_inexistente(self):
        self.tree.insert("m")
        self.assertFalse(self.tree.delete("xyz"))
        self.assertEqual(self.tree.size, 1)

    def test_rn02_bloqueia_remocao_com_contador_maior_que_zero(self):
        # RN02: tag em uso nao pode ser removida.
        service = TagService()
        service.add_tag("Redes")  # contador = 1
        with self.assertRaises(TagValidationError):
            service.remove_tag("Redes")
        self.assertEqual(service.tree.size, 1)

    def test_rn02_permite_remocao_com_contador_zero(self):
        service = TagService()
        service.add_tag("Redes")       # contador = 1
        service.decrement_usage("Redes")  # contador = 0
        self.assertTrue(service.remove_tag("Redes"))
        self.assertEqual(service.tree.size, 0)

    def test_remocao_em_massa_mantem_balanceamento(self):
        # Remove metade dos nos e verifica o RNF05 a cada passo.
        for i in range(60):
            self.tree.insert(f"tag{i:03d}")
        for i in range(0, 60, 2):
            self.tree.delete(f"tag{i:03d}")
            self.assertTrue(self.tree.is_balanced())
        self.assertEqual(self.tree.size, 30)


# =============================================================================
# ROTACOES — testadas ISOLADAMENTE (RNF07)
# =============================================================================
class TestRotacoes(unittest.TestCase):

    def setUp(self):
        self.tree = AVLTree()

    def test_rotacao_ll(self):
        # Caso LL: insercoes em ordem decrescente (c, b, a).
        # Antes da rotacao a arvore seria uma "escada" para a esquerda;
        # depois, "b" deve virar a raiz.
        for k in ["cc", "bb", "aa"]:
            self.tree.insert(k)
        self.assertEqual(self.tree.root.key, "bb")
        self.assertEqual(self.tree.root.left.key, "aa")
        self.assertEqual(self.tree.root.right.key, "cc")
        self.assertEqual(self.tree.get_height(self.tree.root), 2)
        self.assertEqual(self.tree.rotation_count, 1)  # rotacao simples
        self.assertTrue(self.tree.is_balanced())

    def test_rotacao_rr(self):
        # Caso RR: insercoes em ordem crescente (a, b, c).
        for k in ["aa", "bb", "cc"]:
            self.tree.insert(k)
        self.assertEqual(self.tree.root.key, "bb")
        self.assertEqual(self.tree.root.left.key, "aa")
        self.assertEqual(self.tree.root.right.key, "cc")
        self.assertEqual(self.tree.rotation_count, 1)
        self.assertTrue(self.tree.is_balanced())

    def test_rotacao_lr(self):
        # Caso LR: o desequilibrio esta na direita da esquerda (c, a, b).
        for k in ["cc", "aa", "bb"]:
            self.tree.insert(k)
        self.assertEqual(self.tree.root.key, "bb")
        self.assertEqual(self.tree.root.left.key, "aa")
        self.assertEqual(self.tree.root.right.key, "cc")
        # Rotacao dupla = duas rotacoes simples encadeadas.
        self.assertEqual(self.tree.rotation_count, 2)
        self.assertTrue(self.tree.is_balanced())

    def test_rotacao_rl(self):
        # Caso RL: desequilibrio na esquerda da direita (a, c, b).
        for k in ["aa", "cc", "bb"]:
            self.tree.insert(k)
        self.assertEqual(self.tree.root.key, "bb")
        self.assertEqual(self.tree.root.left.key, "aa")
        self.assertEqual(self.tree.root.right.key, "cc")
        self.assertEqual(self.tree.rotation_count, 2)
        self.assertTrue(self.tree.is_balanced())

    def test_rotacoes_sao_contabilizadas(self):
        # RF10: o contador de rotacoes precisa crescer conforme a arvore
        # se reorganiza.
        self.assertEqual(self.tree.rotation_count, 0)
        for i in range(10):
            self.tree.insert(f"k{i}")
        self.assertGreater(self.tree.rotation_count, 0)


# =============================================================================
# BALANCEAMENTO GERAL (RNF05)
# =============================================================================
class TestBalanceamento(unittest.TestCase):

    def test_fb_valido_apos_cada_insercao(self):
        # Apos CADA operacao de escrita, todos os nos devem ter FB em {-1,0,1}.
        tree = AVLTree()
        for i in range(200):
            tree.insert(f"tag{i:04d}")
            self.assertTrue(tree.is_balanced(), f"desbalanceou na insercao {i}")

    def test_altura_logaritmica(self):
        # A altura de uma AVL com n nos fica limitada a ~1.44 * log2(n+2).
        import math
        tree = AVLTree()
        n = 1000
        for i in range(n):
            tree.insert(f"tag{i:04d}")
        limite = 1.4405 * math.log2(n + 2)
        self.assertLessEqual(tree.get_height(tree.root), limite)


# =============================================================================
# CENARIO DE TESTE OBRIGATORIO DO LEVANTAMENTO (item 5.4)
# =============================================================================
class TestCenarioObrigatorio(unittest.TestCase):
    # Insere aula1..aula20 em ORDEM ALFABETICA ESTRITA — exatamente o padrao
    # que degeneraria uma BST comum em lista encadeada — e comprova que a AVL
    # continua balanceada, com altura proxima de log2(n).

    def setUp(self):
        self.service = TagService()
        # sorted() ordena apenas a ENTRADA do teste. A estrutura usada pelo
        # sistema continua sendo exclusivamente a AVL.
        self.tags = sorted(f"aula{i}" for i in range(1, 21))
        for tag in self.tags:
            self.service.add_tag(tag)

    def test_todas_as_tags_foram_inseridas(self):
        self.assertEqual(self.service.tree.size, 20)

    def test_altura_permanece_logaritmica(self):
        # Uma BST comum teria altura 20 (lista encadeada).
        # A AVL precisa ficar bem abaixo disso: log2(20) ~= 4.32.
        altura = self.service.tree.get_height(self.service.tree.root)
        self.assertLessEqual(altura, 6)
        self.assertLess(altura, 20)

    def test_houve_rotacoes(self):
        # Se nao houve rotacao, o balanceamento nao aconteceu.
        self.assertGreater(self.service.tree.rotation_count, 0)

    def test_todos_os_fatores_de_balanceamento_sao_validos(self):
        # RNF05: 100% dos nos com FB em {-1, 0, 1}.
        self.assertTrue(self.service.tree.is_balanced())

    def test_listagem_permanece_alfabetica(self):
        listagem = [t["key"] for t in self.service.list_tags()]
        self.assertEqual(listagem, self.tags)

    def test_autocompletacao_no_cenario(self):
        # Prefixo "aula1" deve casar com aula1, aula10..aula19 (11 tags).
        sugestoes = self.service.search_prefix("aula1", limit=50)
        self.assertEqual(len(sugestoes), 11)

    def test_relatorio_do_cenario(self):
        # Imprime o relatorio pedido no item 15 do escopo, para a apresentacao.
        metricas = self.service.metrics()
        print("\n--- CENARIO OBRIGATORIO: aula1..aula20 em ordem alfabetica ---")
        print(f"Altura da AVL ....... {metricas['height']}")
        print(f"Numero de nos ....... {metricas['node_count']}")
        print(f"Rotacoes realizadas . {metricas['rotations']}")
        print(f"FB valido em todos .. {metricas['is_balanced']}")
        print("Altura de uma BST comum nesse cenario: 20 (lista encadeada)")
        print("\nEstrutura da arvore:")
        print(self.service.tree.to_text())
        self.assertTrue(metricas["is_balanced"])


# =============================================================================
# API FLASK (teste de fumaca da integracao)
# =============================================================================
class TestAPI(unittest.TestCase):

    def setUp(self):
        from backend.app import create_app
        from backend.routes import service
        service.reset()
        self.client = create_app().test_client()

    def test_fluxo_completo(self):
        # Cadastro
        resp = self.client.post("/api/tags", json={"tag": "Redes"})
        self.assertEqual(resp.status_code, 201)

        # Duplicata (case-insensitive) devolve 200, nao 201
        resp = self.client.post("/api/tags", json={"tag": "REDES"})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.get_json()["created"])

        # RN04
        resp = self.client.post("/api/tags", json={"tag": "a"})
        self.assertEqual(resp.status_code, 400)

        # Busca exata
        self.assertEqual(self.client.get("/api/tags/redes").status_code, 200)
        self.assertEqual(self.client.get("/api/tags/inexistente").status_code, 404)

        # Autocompletacao
        dados = self.client.get("/api/tags/search?q=re").get_json()
        self.assertEqual(len(dados["suggestions"]), 1)

        # RN02 bloqueia remocao (contador = 2)
        self.assertEqual(self.client.delete("/api/tags/redes").status_code, 400)

        # Zera o contador e remove
        self.client.post("/api/tags/redes/unuse")
        self.client.post("/api/tags/redes/unuse")
        self.assertEqual(self.client.delete("/api/tags/redes").status_code, 200)

    def test_endpoints_academicos(self):
        self.client.post("/api/seed")
        metricas = self.client.get("/api/metrics").get_json()
        self.assertEqual(metricas["node_count"], 20)
        self.assertTrue(metricas["is_balanced"])
        self.assertIn("text", self.client.get("/api/avl").get_json())


if __name__ == "__main__":
    unittest.main(verbosity=2)

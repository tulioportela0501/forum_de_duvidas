import random

from avl import ArvoreAVL, normalizar_chave


def chaves(arv):
    return [n.chave for n in arv.em_ordem()]


def montar(*nomes):
    a = ArvoreAVL()
    for n in nomes:
        a.inserir(n)
    return a


def test_normalizar_chave():
    assert normalizar_chave('  Estrutura   de DADOS ') == 'estrutura de dados'
    assert normalizar_chave('Programação') == 'programacao'


def test_insercao_e_busca():
    a = montar('python', 'java', 'c')
    assert a.tamanho == 3
    assert a.buscar('Python').nome == 'python'
    assert a.buscar('rust') is None


def test_duplicada_incrementa_uso_sem_criar_no():
    a = montar('python')
    no, criado = a.inserir('PYTHON')
    assert not criado and no.uso == 2 and a.tamanho == 1


def test_busca_ignora_acento_e_caixa():
    a = montar('Programação')
    assert a.buscar('programacao') is not None


def test_rotacao_LL():
    a = montar('c', 'b', 'a')
    assert a.raiz.chave == 'b' and a.esta_balanceada()
    assert [e['tipo'] for e in a.drenar_rotacoes()] == ['LL']


def test_rotacao_RR():
    a = montar('a', 'b', 'c')
    assert a.raiz.chave == 'b' and a.esta_balanceada()
    assert [e['tipo'] for e in a.drenar_rotacoes()] == ['RR']


def test_rotacao_LR():
    a = montar('c', 'a', 'b')
    assert a.raiz.chave == 'b' and a.esta_balanceada()
    assert [e['tipo'] for e in a.drenar_rotacoes()] == ['LR']


def test_rotacao_RL():
    a = montar('a', 'c', 'b')
    assert a.raiz.chave == 'b' and a.esta_balanceada()
    assert [e['tipo'] for e in a.drenar_rotacoes()] == ['RL']


def test_remover_folha():
    a = montar('m', 'f', 'p')
    assert a.remover('f') and chaves(a) == ['m', 'p'] and a.esta_balanceada()


def test_remover_um_filho():
    a = montar('m', 'f', 'p', 'a')
    assert a.remover('f') and chaves(a) == ['a', 'm', 'p'] and a.esta_balanceada()


def test_remover_dois_filhos():
    a = montar('m', 'f', 'p', 'a', 'h', 'n', 'z')
    assert a.remover('m') and chaves(a) == ['a', 'f', 'h', 'n', 'p', 'z'] and a.esta_balanceada()
    assert a.tamanho == 6


def test_remover_raiz_unica_e_inexistente():
    a = montar('x')
    assert not a.remover('y')
    assert a.remover('x') and a.raiz is None and a.tamanho == 0


def test_remocao_causa_rebalanceamento():
    a = montar('m', 'f', 'p', 'a', 'h', 'n', 'z', 'zz')
    a.drenar_rotacoes()
    for k in ('a', 'f', 'h'):
        a.remover(k)
    assert a.esta_balanceada()


def test_autocompletar_prefixo():
    a = montar('python', 'pytest', 'pandas', 'java', 'pilha', 'fila')
    assert [n.nome for n in a.buscar_prefixo('py')] == ['pytest', 'python']
    assert [n.nome for n in a.buscar_prefixo('P', limite=2)] == ['pandas', 'pilha']
    assert a.buscar_prefixo('zzz') == [] and a.buscar_prefixo('') == []


def test_aula1_aula20_balanceada():
    a = ArvoreAVL()
    for i in range(1, 21):
        a.inserir(f'aula{i}')
        assert a.esta_balanceada()
    assert a.tamanho == 20 and a.altura <= 6
    assert chaves(a) == sorted(f'aula{i}' for i in range(1, 21))


def test_altura_logaritmica_com_sequencia_ordenada():
    a = ArvoreAVL()
    for i in range(1000):
        a.inserir(f'k{i:04d}')
    assert a.altura <= 14  # 1.44 * log2(1000) ~ 14.4


def test_operacoes_aleatorias_mantem_invariante():
    rnd = random.Random(42)
    a, ref = ArvoreAVL(), []
    for _ in range(1500):
        k = f'tag{rnd.randint(0, 300)}'
        if rnd.random() < 0.6:
            a.inserir(k, incrementar=False)
            if k not in ref:
                ref.append(k)
        else:
            assert a.remover(k) == (k in ref)
            if k in ref:
                ref.remove(k)
        assert a.esta_balanceada()
    assert a.tamanho == len(ref) and chaves(a) == sorted(ref)


def test_exportacao_para_dict():
    d = montar('b', 'a', 'c').para_dict()
    assert d['key'] == 'b' and d['height'] == 2 and d['balance'] == 0
    assert d['left']['key'] == 'a' and d['right']['key'] == 'c'

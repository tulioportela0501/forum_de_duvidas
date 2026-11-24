"""Árvore AVL implementada manualmente para o dicionário de tags do fórum.

Regras do projeto:
  * a estrutura de dados é a própria árvore (nós com ponteiros esquerda/direita);
  * não usa dict/set/sorted/bibliotecas prontas como substituto da AVL;
  * busca, inserção e remoção são O(log n) porque a altura é mantida <= 1.44 * log2(n).

Cada nó guarda uma tag: chave normalizada (sem acento, minúscula), nome de exibição,
descrição, contador de uso e altura. Toda rotação executada é registrada em uma fila
de eventos (LL, RR, LR, RL) que o serviço drena para persistir/mostrar no dashboard.
"""
import unicodedata


def normalizar_chave(texto):
    """'  Estrutura   de Dados ' -> 'estrutura de dados' (sem acentos, minúsculo)."""
    if texto is None:
        return ''
    decomposto = unicodedata.normalize('NFKD', str(texto))
    sem_acento = ''.join(c for c in decomposto if not unicodedata.combining(c))
    return ' '.join(sem_acento.casefold().split())


class No:
    __slots__ = ('chave', 'nome', 'descricao', 'uso', 'altura', 'esq', 'dir')

    def __init__(self, chave, nome, descricao='', uso=1):
        self.chave = chave
        self.nome = nome
        self.descricao = descricao
        self.uso = uso
        self.altura = 1
        self.esq = None
        self.dir = None


def _h(no):
    return no.altura if no else 0


def _fb(no):
    """Fator de balanceamento = altura(esquerda) - altura(direita)."""
    return _h(no.esq) - _h(no.dir) if no else 0


def _atualizar(no):
    no.altura = 1 + max(_h(no.esq), _h(no.dir))


class ArvoreAVL:
    def __init__(self):
        self.raiz = None
        self.tamanho = 0
        self._rotacoes = []          # eventos ainda não drenados
        self.total_rotacoes = 0
        self._ultimo_no = None       # nó afetado pela última inserção/atualização
        self._criado = False

    # ------------------------------------------------------------------ rotações
    def _rot_dir(self, y):
        x = y.esq
        y.esq = x.dir
        x.dir = y
        _atualizar(y)
        _atualizar(x)
        return x

    def _rot_esq(self, x):
        y = x.dir
        x.dir = y.esq
        y.esq = x
        _atualizar(x)
        _atualizar(y)
        return y

    def _registrar(self, tipo, no):
        self._rotacoes.append({'tipo': tipo, 'no': no.nome})
        self.total_rotacoes += 1

    def _balancear(self, no):
        _atualizar(no)
        fb = _fb(no)
        if fb > 1:                                   # pesado à esquerda
            if _fb(no.esq) >= 0:                     # LL -> rotação simples à direita
                self._registrar('LL', no)
                return self._rot_dir(no)
            self._registrar('LR', no)                # LR -> esquerda no filho, direita no nó
            no.esq = self._rot_esq(no.esq)
            return self._rot_dir(no)
        if fb < -1:                                  # pesado à direita
            if _fb(no.dir) <= 0:                     # RR -> rotação simples à esquerda
                self._registrar('RR', no)
                return self._rot_esq(no)
            self._registrar('RL', no)                # RL -> direita no filho, esquerda no nó
            no.dir = self._rot_dir(no.dir)
            return self._rot_esq(no)
        return no

    # ------------------------------------------------------------------ inserção
    def inserir(self, nome, descricao='', uso_inicial=1, incrementar=True):
        """Insere a tag. Se já existir, incrementa o uso (quando `incrementar`).

        Retorna (no, criado)."""
        chave = normalizar_chave(nome)
        if not chave:
            raise ValueError('Nome de tag vazio.')
        self._criado = False
        self.raiz = self._inserir(self.raiz, chave, str(nome).strip(), descricao, uso_inicial, incrementar)
        if self._criado:
            self.tamanho += 1
        return self._ultimo_no, self._criado

    def _inserir(self, no, chave, nome, descricao, uso, incrementar):
        if no is None:
            self._criado = True
            self._ultimo_no = No(chave, ' '.join(nome.split()), descricao, uso)
            return self._ultimo_no
        if chave < no.chave:
            no.esq = self._inserir(no.esq, chave, nome, descricao, uso, incrementar)
        elif chave > no.chave:
            no.dir = self._inserir(no.dir, chave, nome, descricao, uso, incrementar)
        else:
            if incrementar:
                no.uso += 1
            self._ultimo_no = no
            return no
        return self._balancear(no)

    # ------------------------------------------------------------------ busca
    def buscar(self, nome):
        chave = normalizar_chave(nome)
        no = self.raiz
        while no is not None:
            if chave < no.chave:
                no = no.esq
            elif chave > no.chave:
                no = no.dir
            else:
                return no
        return None

    def buscar_prefixo(self, prefixo, limite=10):
        """Autocompletar: tags cuja chave começa com `prefixo`, em ordem alfabética.

        Poda a árvore: só desce para o lado que pode conter o prefixo (O(log n + k))."""
        p = normalizar_chave(prefixo)
        achados = []
        if not p:
            return achados

        def visitar(no):
            if no is None or len(achados) >= limite:
                return
            if p < no.chave:
                visitar(no.esq)
            if len(achados) < limite and no.chave.startswith(p):
                achados.append(no)
            if no.chave < p or no.chave.startswith(p):
                visitar(no.dir)

        visitar(self.raiz)
        return achados

    # ------------------------------------------------------------------ remoção
    def remover(self, nome):
        """Remove a tag. Retorna True se existia."""
        chave = normalizar_chave(nome)
        self._removeu = False
        self.raiz = self._remover(self.raiz, chave)
        if self._removeu:
            self.tamanho -= 1
        return self._removeu

    def _remover(self, no, chave):
        if no is None:
            return None
        if chave < no.chave:
            no.esq = self._remover(no.esq, chave)
        elif chave > no.chave:
            no.dir = self._remover(no.dir, chave)
        else:
            self._removeu = True
            if no.esq is None:            # folha ou só filho direito
                return no.dir
            if no.dir is None:            # só filho esquerdo
                return no.esq
            suc = no.dir                  # dois filhos: sucessor in-order
            while suc.esq is not None:
                suc = suc.esq
            no.chave, no.nome, no.descricao, no.uso = suc.chave, suc.nome, suc.descricao, suc.uso
            marcado = self._removeu
            no.dir = self._remover(no.dir, suc.chave)
            self._removeu = marcado
        return self._balancear(no)

    # ------------------------------------------------------------------ consulta
    def em_ordem(self):
        saida = []

        def rec(no):
            if no is None:
                return
            rec(no.esq)
            saida.append(no)
            rec(no.dir)

        rec(self.raiz)
        return saida

    @property
    def altura(self):
        return _h(self.raiz)

    def esta_balanceada(self):
        """Verifica a invariante AVL (usada nos testes)."""
        def rec(no):
            if no is None:
                return 0, True
            he, ok_e = rec(no.esq)
            hd, ok_d = rec(no.dir)
            ok = ok_e and ok_d and abs(he - hd) <= 1 and no.altura == 1 + max(he, hd)
            return 1 + max(he, hd), ok

        return rec(self.raiz)[1]

    def drenar_rotacoes(self):
        eventos, self._rotacoes = self._rotacoes, []
        return eventos

    # ------------------------------------------------------------------ exportação
    @staticmethod
    def no_para_dict(no):
        if no is None:
            return None
        return {
            'key': no.chave,
            'display_name': no.nome,
            'description': no.descricao,
            'usage_count': no.uso,
            'height': no.altura,
            'balance': _fb(no),
            'left': ArvoreAVL.no_para_dict(no.esq),
            'right': ArvoreAVL.no_para_dict(no.dir),
        }

    def para_dict(self):
        return ArvoreAVL.no_para_dict(self.raiz)

    def estatisticas(self):
        nos = self.em_ordem()
        fbs = [_fb(n) for n in nos]
        return {
            'nodes': self.tamanho,
            'height': self.altura,
            'max_balance': max(fbs) if fbs else 0,
            'min_balance': min(fbs) if fbs else 0,
            'balanced': self.esta_balanceada(),
        }

    def texto(self):
        """Representação textual (raiz à esquerda, subárvore direita em cima)."""
        linhas = []

        def rec(no, nivel):
            if no is None:
                return
            rec(no.dir, nivel + 1)
            linhas.append('    ' * nivel + f'{no.nome} (h={no.altura}, fb={_fb(no)})')
            rec(no.esq, nivel + 1)

        rec(self.raiz, 0)
        return '\n'.join(linhas) if linhas else '(árvore vazia)'

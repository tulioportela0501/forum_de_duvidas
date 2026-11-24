"""Regras de negócio. MODELO SERVERLESS: sem estado entre requisições.

O banco (tags) é a fonte da verdade. A cada operação a AVL manual (forum/avl.py) é reconstruída em
memória a partir das tags, a operação é executada NA ÁRVORE (inserção/busca/remoção/rotações/prefixo) e o
resultado é persistido em uma única transação. Custo da reconstrução: O(n log n) para n tags (pequeno).
"""
import re

from forum.avl import ArvoreAVL, normalizar_chave
from forum.db import DbIntegrityError

_TAG_RE = re.compile(r'^[\w#+.\- ]+$', re.UNICODE)


class ErroValidacao(ValueError):
    pass


class Conflito(Exception):
    pass


def validar_tag(nome):
    nome = ' '.join(str(nome or '').split())
    if not nome or len(nome) > 40 or not _TAG_RE.match(nome):
        raise ErroValidacao('Tag inválida: use de 1 a 40 caracteres (letras, números, espaço, # + . - _).')
    return nome


class ServicoForum:
    def __init__(self, repo):
        self.repo = repo

    def _arvore(self):
        """Reconstrói a AVL a partir do banco (sem contar rotações da reconstrução)."""
        arv = ArvoreAVL()
        for t in self.repo.listar_tags():
            arv.inserir(t['display_name'], t['description'], uso_inicial=t['usage_count'], incrementar=False)
        arv.drenar_rotacoes()
        arv.total_rotacoes = 0
        return arv

    @staticmethod
    def _tag_dict(n):
        return {'key': n.chave, 'display_name': n.nome, 'description': n.descricao,
                'usage_count': n.uso, 'height': n.altura}

    # ---- tags
    def listar_tags(self):
        return [self._tag_dict(n) for n in self._arvore().em_ordem()]

    def autocompletar(self, prefixo, limite=8):
        return [self._tag_dict(n) for n in self._arvore().buscar_prefixo(prefixo, limite)]

    def buscar_tag(self, nome):
        no = self._arvore().buscar(nome)
        return self._tag_dict(no) if no else None

    def criar_tag(self, nome, descricao=''):
        nome = validar_tag(nome)
        descricao = str(descricao or '').strip()[:200]
        arv = self._arvore()
        if arv.buscar(nome):
            raise Conflito('Essa tag já existe.')
        no, _ = arv.inserir(nome, descricao, uso_inicial=0)
        rot = arv.drenar_rotacoes()
        try:
            self.repo.criar_tag(no.chave, no.nome, no.descricao, rot)
        except DbIntegrityError:
            raise Conflito('Essa tag já existe.')
        return self._tag_dict(no), rot

    def editar_tag(self, nome, novo_nome, descricao=''):
        existente=validar_tag(nome); novo_nome=validar_tag(novo_nome)
        descricao=str(descricao or '').strip()[:200]
        arv=self._arvore(); antigo=arv.buscar(existente)
        if not antigo: return None
        conflito=arv.buscar(novo_nome)
        if conflito and conflito.chave != antigo.chave: raise Conflito('Essa tag já existe.')
        uso=antigo.uso; chave_antiga=antigo.chave
        arv.remover(existente)
        novo,_=arv.inserir(novo_nome,descricao,uso_inicial=uso,incrementar=False)
        rot=arv.drenar_rotacoes()
        try:self.repo.editar_tag(chave_antiga,novo.chave,antigo.nome,novo.nome,descricao,uso,rot)
        except DbIntegrityError:raise Conflito('Essa tag já existe.')
        return self._tag_dict(novo),rot

    def remover_tag(self, nome):
        arv = self._arvore()
        existente = arv.buscar(nome)
        if not existente:
            return False
        chave = existente.chave
        arv.remover(nome)
        self.repo.remover_tag(chave, arv.drenar_rotacoes())
        return True

    # ---- tópicos
    def criar_topico(self, titulo, descricao, autor, tags):
        titulo = ' '.join(str(titulo or '').split())
        descricao = str(descricao or '').strip()
        autor = ' '.join(str(autor or '').split())[:60]
        if not (3 <= len(titulo) <= 150):
            raise ErroValidacao('O título deve ter entre 3 e 150 caracteres.')
        if len(descricao) > 2000:
            raise ErroValidacao('A descrição pode ter no máximo 2000 caracteres.')
        if not isinstance(tags, list):
            raise ErroValidacao('Tags devem ser enviadas como lista.')
        limpas, vistas = [], []
        for t in tags:
            nome = validar_tag(t)
            chave = normalizar_chave(nome)
            if chave not in vistas:
                vistas.append(chave)
                limpas.append(nome)
        if not limpas:
            raise ErroValidacao('Informe pelo menos uma tag.')
        if len(limpas) > 8:
            raise ErroValidacao('Use no máximo 8 tags por dúvida.')
        arv = self._arvore()
        nos = []
        for nome in limpas:
            no, _ = arv.inserir(nome, uso_inicial=1, incrementar=True)
            nos.append(no)
        return self.repo.criar_topico(titulo, descricao, autor,
                                      [(n.chave, n.nome, n.descricao) for n in nos], arv.drenar_rotacoes())

    # ---- visualização
    def snapshot(self):
        arv = self._arvore()
        return {'root': arv.para_dict(), 'stats': arv.estatisticas(),
                'texto': arv.texto(), 'rotacoes': self.repo.resumo_rotacoes()}

    def dashboard(self):
        arv = self._arvore()
        tags = arv.em_ordem()
        topo = sorted(tags, key=lambda n: (-n.uso, n.chave))[:8]
        return {
            'membros': self.repo.contar('membros'),
            'topicos': self.repo.contar('topicos'),
            'tags': len(tags),
            'tags_usadas': sum(1 for n in tags if n.uso > 0),
            'altura': arv.altura,
            'rotacoes': self.repo.resumo_rotacoes(),
            'top_tags': [{'tag': n.nome, 'usage_count': n.uso} for n in topo if n.uso > 0],
            **self.repo.dashboard_completo(),
        }

    @staticmethod
    def teste_carga(prefixo='aula', quantidade=20):
        """Insere aula1..aulaN em uma árvore TEMPORÁRIA (não toca nos dados reais)."""
        arv = ArvoreAVL()
        passos = []
        for i in range(1, quantidade + 1):
            nome = f'{prefixo}{i}'
            arv.inserir(nome)
            rot = arv.drenar_rotacoes()
            passos.append({'inserida': nome, 'rotacoes': rot, 'altura': arv.altura,
                           'arvore': {'root': arv.para_dict()}})
        por_tipo = {'LL': 0, 'RR': 0, 'LR': 0, 'RL': 0}
        for p in passos:
            for r in p['rotacoes']:
                por_tipo[r['tipo']] += 1
        return {'passos': passos, 'resumo': {'nos': arv.tamanho, 'altura': arv.altura,
                                             'rotacoes': sum(por_tipo.values()), 'por_tipo': por_tipo,
                                             'balanceada': arv.esta_balanceada()}}

"""Regras de negócio: valida entradas, mantém AVL (memória) e SQLite (disco) sincronizados."""
import re
import threading

from avl import ArvoreAVL, normalizar_chave

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
        self.trava = threading.RLock()   # o servidor de desenvolvimento usa threads
        self.arvore = ArvoreAVL()
        self._reconstruir()

    def _reconstruir(self):
        for t in self.repo.listar_tags():
            self.arvore.inserir(t['display_name'], t['description'], uso_inicial=t['usage_count'], incrementar=False)
        self.arvore.drenar_rotacoes()
        self.arvore.total_rotacoes = 0

    def _salvar_no(self, no):
        self.repo.salvar_tag(no.chave, no.nome, no.descricao, no.uso)

    def _persistir_rotacoes(self):
        eventos = self.arvore.drenar_rotacoes()
        if eventos:
            self.repo.registrar_rotacoes(eventos)
        return eventos

    # ---- tags
    def listar_tags(self):
        with self.trava:
            return [self._tag_dict(n) for n in self.arvore.em_ordem()]

    @staticmethod
    def _tag_dict(n):
        return {'key': n.chave, 'display_name': n.nome, 'description': n.descricao,
                'usage_count': n.uso, 'height': n.altura}

    def criar_tag(self, nome, descricao=''):
        nome = validar_tag(nome)
        descricao = str(descricao or '').strip()[:200]
        with self.trava:
            if self.arvore.buscar(nome):
                raise Conflito('Essa tag já existe.')
            no, _ = self.arvore.inserir(nome, descricao, uso_inicial=0)
            self._salvar_no(no)
            rot = self._persistir_rotacoes()
            return self._tag_dict(no), rot

    def remover_tag(self, nome):
        with self.trava:
            existente = self.arvore.buscar(nome)
            if not existente:
                return False
            chave = existente.chave
            self.arvore.remover(nome)
            self.repo.remover_tag(chave)
            self._persistir_rotacoes()
            return True

    def autocompletar(self, prefixo, limite=8):
        with self.trava:
            return [self._tag_dict(n) for n in self.arvore.buscar_prefixo(prefixo, limite)]

    def buscar_tag(self, nome):
        with self.trava:
            no = self.arvore.buscar(nome)
            return self._tag_dict(no) if no else None

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
        with self.trava:
            nomes = []
            for nome in limpas:
                no, _ = self.arvore.inserir(nome, uso_inicial=1, incrementar=True)
                self._salvar_no(no)
                nomes.append(no.nome)
            self._persistir_rotacoes()
            return self.repo.criar_topico(titulo, descricao, autor, nomes)

    # ---- visualização
    def snapshot(self):
        with self.trava:
            return {'root': self.arvore.para_dict(), 'stats': self.arvore.estatisticas(),
                    'texto': self.arvore.texto(), 'rotacoes': self.repo.resumo_rotacoes()}

    def dashboard(self):
        with self.trava:
            tags = self.arvore.em_ordem()
            topo = sorted(tags, key=lambda n: (-n.uso, n.chave))[:8]
            return {
                'membros': len(self.repo.listar_membros()),
                'topicos': len(self.repo.listar_topicos()),
                'tags': len(tags),
                'tags_usadas': sum(1 for n in tags if n.uso > 0),
                'altura': self.arvore.altura,
                'rotacoes': self.repo.resumo_rotacoes(),
                'top_tags': [{'tag': n.nome, 'usage_count': n.uso} for n in topo if n.uso > 0],
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

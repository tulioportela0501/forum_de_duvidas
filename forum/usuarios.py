"""Gestão de contas (somente administradores): cadastro, edição, bloqueio, exclusão e verificação de professores.

Regras (aplicadas aqui, no backend — o front apenas esconde botões):
* O ADMINISTRADOR PRINCIPAL (criado no primeiro acesso) é intocável por outros: não pode ser editado, bloqueado,
  rebaixado nem excluído por ninguém além de si mesmo, e nem ele mesmo pode se bloquear/excluir/mudar de perfil.
  Assim o sistema nunca fica sem administrador.
* Ninguém bloqueia, exclui ou muda o próprio perfil (evita se trancar para fora). A própria senha só muda por
  /api/auth/senha, que exige a senha atual.
* Professor nasce NÃO verificado e não consegue entrar até um administrador usar /verificar. A verificação cai se o
  e-mail do professor mudar ou se ele deixar/voltar a ser professor.
* Bloquear, excluir, redefinir senha, trocar perfil ou revogar verificação derruba as sessões abertas da conta.
"""
from flask import Blueprint, current_app, g, jsonify, request

from forum.auth import (PERFIS, hash_senha, normalizar_email, perfis, validar_dados_conta, validar_senha)
from forum.repo import agora

bp = Blueprint('usuarios', __name__, url_prefix='/api/usuarios')


def _repo():
    return current_app.extensions['repo']


def _erro(msg, codigo):
    return jsonify(erro=msg), codigo


def _alvo(uid):
    return _repo().obter_usuario(uid)


def _log(acao, alvo, extra='ok'):
    _repo().registrar_log(g.usuario['email'], f"{acao} #{alvo['id']} ({alvo['email']})", extra)


def _eh_eu(alvo):
    return alvo['id'] == g.usuario['id']


def _principal_alheio(alvo):
    return alvo['principal'] and not _eh_eu(alvo)


MSG_PRINCIPAL = 'O administrador principal só pode ser alterado por ele mesmo.'


def _publico(u):
    return {**u, 'verificado': bool(u['verificado']), 'principal': bool(u['principal'])}


@bp.get('')
@perfis('admin')
def listar():
    return jsonify([_publico(u) for u in _repo().listar_usuarios()])


@bp.get('/<int:uid>')
@perfis('admin')
def obter(uid):
    u = _alvo(uid)
    return jsonify(_publico(u)) if u else _erro('Usuário não encontrado.', 404)


@bp.post('')
@perfis('admin')
def criar():
    d = request.get_json(silent=True) or {}
    nome, email = ' '.join(str(d.get('nome') or '').split()), normalizar_email(d.get('email'))
    perfil, senha = d.get('perfil'), d.get('senha')
    if perfil not in PERFIS:
        return _erro('Perfil inválido (admin, professor ou aluno).', 400)
    erro = validar_dados_conta(nome, email) or validar_senha(senha, nome, email)
    if erro:
        return _erro(erro, 400)
    uid = _repo().criar_usuario(nome, email, hash_senha(senha), perfil, g.usuario['id'])
    if uid is None:
        return _erro('E-mail já cadastrado.', 409)
    novo = _alvo(uid)
    _log('criar usuário', novo, f'ok ({perfil})')
    return jsonify(_publico(novo)), 201


@bp.patch('/<int:uid>')
@perfis('admin')
def editar(uid):
    repo = _repo()
    alvo = _alvo(uid)
    if not alvo:
        return _erro('Usuário não encontrado.', 404)
    if _principal_alheio(alvo):
        return _erro(MSG_PRINCIPAL, 403)
    d = request.get_json(silent=True) or {}
    campos, revogar = {}, False
    novo_perfil = alvo['perfil']

    if 'nome' in d:
        nome = ' '.join(str(d['nome'] or '').split())
        erro = validar_dados_conta(nome=nome)
        if erro:
            return _erro(erro, 400)
        campos['nome'] = nome
    if 'email' in d:
        email = normalizar_email(d['email'])
        erro = validar_dados_conta(email=email)
        if erro:
            return _erro(erro, 400)
        if email != alvo['email']:
            campos['email'] = email
    if 'perfil' in d and d['perfil'] != alvo['perfil']:
        if d['perfil'] not in PERFIS:
            return _erro('Perfil inválido (admin, professor ou aluno).', 400)
        if _eh_eu(alvo):
            return _erro('Você não pode alterar o seu próprio perfil.', 403)
        novo_perfil = d['perfil']
        campos['perfil'] = novo_perfil
        revogar = True
    if 'senha' in d:
        if _eh_eu(alvo):
            return _erro('Para trocar a sua própria senha use "Minha conta" (exige a senha atual).', 400)
        erro = validar_senha(d['senha'], campos.get('nome', alvo['nome']), campos.get('email', alvo['email']))
        if erro:
            return _erro(erro, 400)
        campos['senha'] = hash_senha(d['senha'])
        revogar = True
    if not campos:
        return _erro('Nenhuma alteração informada.', 400)

    # a verificação vale para UM professor com UM e-mail: qualquer mudança de identidade/função a derruba
    if alvo['verificado'] and (novo_perfil != 'professor' or 'email' in campos):
        campos.update(verificado=0, verificado_em=None, verificado_por=None)
        revogar = True

    if not repo.atualizar_usuario(uid, campos, revogar_sessoes=revogar):
        return _erro('E-mail já cadastrado.', 409)
    _log('editar usuário', alvo, 'ok (' + ', '.join(sorted(k for k in campos if k != 'senha')
                                                   + (['senha redefinida'] if 'senha' in campos else [])) + ')')
    return jsonify(_publico(_alvo(uid)))


@bp.post('/<int:uid>/bloquear')
@perfis('admin')
def bloquear(uid):
    alvo = _alvo(uid)
    if not alvo:
        return _erro('Usuário não encontrado.', 404)
    if alvo['principal']:
        return _erro('O administrador principal não pode ser bloqueado.', 403)
    if _eh_eu(alvo):
        return _erro('Você não pode bloquear a si mesmo.', 403)
    _repo().atualizar_usuario(uid, {'status': 'bloqueado'}, revogar_sessoes=True)
    _log('bloquear usuário', alvo)
    return jsonify(_publico(_alvo(uid)))


@bp.post('/<int:uid>/desbloquear')
@perfis('admin')
def desbloquear(uid):
    alvo = _alvo(uid)
    if not alvo:
        return _erro('Usuário não encontrado.', 404)
    _repo().atualizar_usuario(uid, {'status': 'ativo'})
    _log('desbloquear usuário', alvo)
    return jsonify(_publico(_alvo(uid)))


@bp.delete('/<int:uid>')
@perfis('admin')
def excluir(uid):
    alvo = _alvo(uid)
    if not alvo:
        return _erro('Usuário não encontrado.', 404)
    if alvo['principal']:
        return _erro('O administrador principal não pode ser excluído.', 403)
    if _eh_eu(alvo):
        return _erro('Você não pode excluir a sua própria conta.', 403)
    _repo().excluir_usuario(uid)
    _log('excluir usuário', alvo)
    return jsonify(ok=True)


@bp.post('/<int:uid>/verificar')
@perfis('admin')
def verificar(uid):
    alvo = _alvo(uid)
    if not alvo:
        return _erro('Usuário não encontrado.', 404)
    if alvo['perfil'] != 'professor':
        return _erro('Somente contas de professor passam por verificação.', 400)
    _repo().atualizar_usuario(uid, {'verificado': 1, 'verificado_em': agora(), 'verificado_por': g.usuario['id']})
    _log('verificar professor', alvo)
    return jsonify(_publico(_alvo(uid)))


@bp.post('/<int:uid>/revogar-verificacao')
@perfis('admin')
def revogar_verificacao(uid):
    alvo = _alvo(uid)
    if not alvo:
        return _erro('Usuário não encontrado.', 404)
    if alvo['perfil'] != 'professor':
        return _erro('Somente contas de professor passam por verificação.', 400)
    _repo().atualizar_usuario(uid, {'verificado': 0, 'verificado_em': None, 'verificado_por': None},
                              revogar_sessoes=True)
    _log('revogar verificação', alvo)
    return jsonify(_publico(_alvo(uid)))

"""Cadastro, edição, bloqueio, exclusão e verificação de contas + regras de proteção."""
import pytest

from tests.conftest import SENHA, Cli

NOVO = {'nome': 'Maria Souza', 'email': 'maria@escola.com', 'senha': SENHA, 'perfil': 'aluno'}


def _perfil_de(admin, uid):
    return admin.get(f'/api/usuarios/{uid}').get_json()


# ------------------------------------------------------------ cadastro
def test_admin_cadastra_cada_perfil_e_a_conta_entra(app, admin):
    for perfil in ('aluno', 'admin'):
        r = admin.post('/api/usuarios', {**NOVO, 'perfil': perfil, 'email': f'novo-{perfil}@escola.com'})
        assert r.status_code == 201 and r.get_json()['perfil'] == perfil
        assert 'senha' not in r.get_json()
        assert Cli(app, ip='10.0.1.1').entrar(f'novo-{perfil}@escola.com').status_code == 200
    assert admin.post('/api/usuarios', {**NOVO, 'perfil': 'aluno'}).status_code == 201


@pytest.mark.parametrize('mudanca,codigo', [
    ({'perfil': 'superadmin'}, 400), ({'perfil': None}, 400), ({'perfil': ['admin']}, 400),
    ({'email': 'invalido'}, 400), ({'nome': 'A'}, 400), ({'senha': 'curta'}, 400), ({'senha': 'soletrasaqui'}, 400),
])
def test_cadastro_valida(admin, mudanca, codigo):
    assert admin.post('/api/usuarios', {**NOVO, **mudanca}).status_code == codigo
    assert len(admin.get('/api/usuarios').get_json()) == 1             # só o principal


def test_email_duplicado_e_case_insensitive(admin):
    assert admin.post('/api/usuarios', NOVO).status_code == 201
    assert admin.post('/api/usuarios', {**NOVO, 'email': 'MARIA@escola.COM'}).status_code == 409
    assert admin.post('/api/usuarios', {**NOVO, 'email': 'ADMIN@escola.com'}).status_code == 409


def test_cadastro_ignora_campos_privilegiados_do_cliente(app, admin):
    """Mass assignment: não dá para criar já verificado, como principal ou com status arbitrário."""
    r = admin.post('/api/usuarios', {**NOVO, 'perfil': 'professor', 'verificado': True, 'principal': True,
                                     'status': 'ativo', 'id': 777})
    u = r.get_json()
    assert u['verificado'] is False and u['principal'] is False and u['id'] != 777
    assert Cli(app).entrar('maria@escola.com').status_code == 403         # ainda precisa de verificação


# ------------------------------------------------------------ professor: verificação administrativa
def test_professor_nao_entra_ate_ser_verificado(app, admin):
    uid = admin.post('/api/usuarios', {**NOVO, 'perfil': 'professor'}).get_json()['id']
    c = Cli(app, ip='10.0.1.2')
    r = c.entrar('maria@escola.com')
    assert r.status_code == 403 and 'verificação' in r.get_json()['erro'] and not c.cookie()
    # com senha errada a resposta continua genérica (não vaza o estado da conta)
    assert c.entrar('maria@escola.com', 'errada12345').status_code == 401
    v = admin.post(f'/api/usuarios/{uid}/verificar')
    assert v.status_code == 200 and v.get_json()['verificado'] is True
    assert v.get_json()['verificado_por_nome'] == 'Admin Principal' and v.get_json()['verificado_em']
    assert c.entrar('maria@escola.com').status_code == 200


def test_revogar_verificacao_derruba_sessao_e_impede_novo_login(admin, prof):
    assert prof.get('/api/tags').status_code == 200
    r = admin.post(f'/api/usuarios/{prof.id}/revogar-verificacao')
    assert r.status_code == 200 and r.get_json()['verificado'] is False
    assert prof.get('/api/tags').status_code == 401                    # sessão aberta caiu na hora
    assert prof.entrar('prof@escola.com').status_code == 403


def test_verificacao_so_para_professor(admin, aluno, admin2):
    for alvo in (aluno, admin2):
        assert admin.post(f'/api/usuarios/{alvo.id}/verificar').status_code == 400
        assert admin.post(f'/api/usuarios/{alvo.id}/revogar-verificacao').status_code == 400


def test_professor_nao_se_autoverifica(app, admin):
    uid = admin.post('/api/usuarios', {**NOVO, 'perfil': 'professor'}).get_json()['id']
    c = Cli(app, ip='10.0.1.3')
    assert c.entrar('maria@escola.com').status_code == 403            # sem sessão não há como chamar /verificar
    assert c.post(f'/api/usuarios/{uid}/verificar').status_code == 401
    assert _perfil_de(admin, uid)['verificado'] is False


def test_trocar_email_do_professor_derruba_a_verificacao(admin, prof):
    r = admin.patch(f'/api/usuarios/{prof.id}', {'email': 'novo.prof@escola.com'})
    assert r.status_code == 200 and r.get_json()['verificado'] is False
    assert prof.get('/api/tags').status_code == 401
    assert Cli(prof.app).entrar('novo.prof@escola.com').status_code == 403


def test_deixar_de_ser_professor_zera_verificacao_e_voltar_exige_nova(admin, prof):
    assert admin.patch(f'/api/usuarios/{prof.id}', {'perfil': 'aluno'}).get_json()['verificado'] is False
    assert admin.patch(f'/api/usuarios/{prof.id}', {'perfil': 'professor'}).get_json()['verificado'] is False
    assert Cli(prof.app).entrar('prof@escola.com').status_code == 403


# ------------------------------------------------------------ edição
def test_editar_nome_email_perfil_e_senha(app, admin, aluno):
    r = admin.patch(f'/api/usuarios/{aluno.id}', {'nome': '  Novo   Nome ', 'email': 'NOVO@escola.com'})
    assert r.status_code == 200 and r.get_json()['nome'] == 'Novo Nome' and r.get_json()['email'] == 'novo@escola.com'
    assert admin.patch(f'/api/usuarios/{aluno.id}', {'senha': 'OutraSenha2024'}).status_code == 200
    c = Cli(app, ip='10.0.1.4')
    assert c.entrar('novo@escola.com', SENHA).status_code == 401
    assert c.entrar('novo@escola.com', 'OutraSenha2024').status_code == 200


def test_editar_perfil_e_senha_derrubam_sessoes_do_alvo(admin, aluno):
    assert aluno.get('/api/tags').status_code == 200
    admin.patch(f'/api/usuarios/{aluno.id}', {'perfil': 'professor'})
    assert aluno.get('/api/tags').status_code == 401
    novo = Cli(aluno.app, ip='10.0.1.5')
    admin.post(f'/api/usuarios/{aluno.id}/verificar')
    novo.entrar('aluno@escola.com')
    admin.patch(f'/api/usuarios/{aluno.id}', {'senha': 'OutraSenha2024'})
    assert novo.get('/api/tags').status_code == 401


def test_editar_validacoes(admin, aluno, prof):
    u = f'/api/usuarios/{aluno.id}'
    assert admin.patch(u, {}).status_code == 400
    assert admin.patch(u, {'email': 'ruim'}).status_code == 400
    assert admin.patch(u, {'nome': ''}).status_code == 400
    assert admin.patch(u, {'perfil': 'root'}).status_code == 400
    assert admin.patch(u, {'senha': 'curta'}).status_code == 400
    assert admin.patch(u, {'email': 'prof@escola.com'}).status_code == 409      # já usado por outro
    assert admin.patch('/api/usuarios/99999', {'nome': 'Fulano'}).status_code == 404
    assert _perfil_de(admin, aluno.id)['email'] == 'aluno@escola.com'


def test_patch_ignora_campos_que_nao_pode_alterar(admin, aluno):
    admin.patch(f'/api/usuarios/{aluno.id}', {'nome': 'Nome Novo', 'principal': 1, 'status': 'bloqueado',
                                              'verificado': 1, 'id': 1, 'criado_por': 5})
    u = _perfil_de(admin, aluno.id)
    assert u['principal'] is False and u['status'] == 'ativo' and u['verificado'] is False and u['id'] == aluno.id


# ------------------------------------------------------------ bloqueio
def test_bloquear_derruba_sessao_na_hora_e_impede_login_ate_desbloquear(admin, aluno):
    assert aluno.get('/api/tags').status_code == 200
    r = admin.post(f'/api/usuarios/{aluno.id}/bloquear')
    assert r.status_code == 200 and r.get_json()['status'] == 'bloqueado'
    assert aluno.get('/api/tags').status_code == 401
    novo = Cli(aluno.app, ip='10.0.1.6')
    r = novo.entrar('aluno@escola.com')
    assert r.status_code == 403 and 'bloqueada' in r.get_json()['erro'] and not novo.cookie()
    assert novo.entrar('aluno@escola.com', 'errada12345').status_code == 401      # sem vazar o status
    assert admin.post(f'/api/usuarios/{aluno.id}/desbloquear').get_json()['status'] == 'ativo'
    assert novo.entrar('aluno@escola.com').status_code == 200


def test_sessao_antiga_de_conta_bloqueada_nao_revive_com_desbloqueio(admin, aluno):
    admin.post(f'/api/usuarios/{aluno.id}/bloquear')
    admin.post(f'/api/usuarios/{aluno.id}/desbloquear')
    assert aluno.get('/api/tags').status_code == 401        # a sessão foi apagada no bloqueio


def test_bloqueio_mesmo_sem_revogar_e_checado_a_cada_requisicao(app, admin, aluno):
    """Defesa em profundidade: mesmo que a sessão sobrevivesse, o status é relido do banco a cada chamada."""
    app.extensions['repo'].db.execute("UPDATE usuarios SET status='bloqueado' WHERE id=?", (aluno.id,))
    r = aluno.get('/api/tags')
    assert r.status_code == 403 and 'bloqueada' in r.get_json()['erro']


def test_perfil_e_relido_do_banco_a_cada_requisicao(app, admin, prof):
    assert prof.get('/api/avl').status_code == 200
    app.extensions['repo'].db.execute("UPDATE usuarios SET perfil='aluno' WHERE id=?", (prof.id,))
    assert prof.get('/api/avl').status_code == 403          # rebaixado vale imediatamente, sem novo login


# ------------------------------------------------------------ exclusão
def test_excluir_remove_conta_sessoes_e_libera_email(app, admin, aluno):
    assert admin.delete(f'/api/usuarios/{aluno.id}').status_code == 200
    assert aluno.get('/api/tags').status_code == 401
    assert admin.get(f'/api/usuarios/{aluno.id}').status_code == 404
    assert Cli(app, ip='10.0.1.7').entrar('aluno@escola.com').status_code == 401
    assert app.extensions['repo'].db.execute('SELECT COUNT(*) AS n FROM sessoes WHERE usuario_id=?',
                                             (aluno.id,)).rows[0]['n'] == 0
    assert admin.delete(f'/api/usuarios/{aluno.id}').status_code == 404
    assert admin.post('/api/usuarios', {**NOVO, 'email': 'aluno@escola.com'}).status_code == 201   # e-mail livre de novo


def test_excluir_nao_apaga_o_conteudo_publicado(admin, aluno):
    aluno.post('/api/topicos', {'titulo': 'Dúvida do aluno', 'tags': ['avl']})
    admin.delete(f'/api/usuarios/{aluno.id}')
    t = admin.get('/api/topicos').get_json()
    assert len(t) == 1 and t[0]['autor'] == 'Aluno'


# ------------------------------------------------------------ proteções: principal e auto-proteção
def test_principal_e_intocavel_por_outros_admins(admin, admin2):
    pid = admin.usuario['id']
    for metodo, url, corpo in [('PATCH', f'/api/usuarios/{pid}', {'nome': 'Tomei Conta'}),
                               ('PATCH', f'/api/usuarios/{pid}', {'perfil': 'aluno'}),
                               ('PATCH', f'/api/usuarios/{pid}', {'senha': 'SenhaDoInvasor1'}),
                               ('POST', f'/api/usuarios/{pid}/bloquear', {}),
                               ('DELETE', f'/api/usuarios/{pid}', None)]:
        assert admin2.req(metodo, url, json=corpo).status_code == 403, (metodo, url)
    p = _perfil_de(admin, pid)
    assert p['nome'] == 'Admin Principal' and p['perfil'] == 'admin' and p['status'] == 'ativo'
    assert admin.get('/api/auth/eu').status_code == 200
    assert Cli(admin.app, ip='10.0.1.8').entrar('admin@escola.com').status_code == 200


def test_principal_nao_se_bloqueia_exclui_nem_rebaixa(admin):
    pid = admin.usuario['id']
    assert admin.post(f'/api/usuarios/{pid}/bloquear').status_code == 403
    assert admin.delete(f'/api/usuarios/{pid}').status_code == 403
    assert admin.patch(f'/api/usuarios/{pid}', {'perfil': 'aluno'}).status_code == 403
    assert admin.patch(f'/api/usuarios/{pid}', {'nome': 'Outro Nome Ok'}).status_code == 200   # editar o nome pode
    assert _perfil_de(admin, pid)['perfil'] == 'admin'


def test_admin_comum_nao_se_bloqueia_exclui_nem_muda_o_proprio_perfil(admin, admin2):
    me = admin2.id
    assert admin2.post(f'/api/usuarios/{me}/bloquear').status_code == 403
    assert admin2.delete(f'/api/usuarios/{me}').status_code == 403
    assert admin2.patch(f'/api/usuarios/{me}', {'perfil': 'aluno'}).status_code == 403
    assert admin2.patch(f'/api/usuarios/{me}', {'senha': 'SenhaNova2024x'}).status_code == 400   # usa /api/auth/senha
    assert admin2.patch(f'/api/usuarios/{me}', {'nome': 'Admin Dois'}).status_code == 200
    assert admin2.get('/api/usuarios').status_code == 200


def test_admin_comum_pode_gerir_outros_admins_exceto_o_principal(admin, admin2, criar):
    outro = criar('admin', 'admin3@escola.com')
    assert admin2.post(f'/api/usuarios/{outro.id}/bloquear').status_code == 200
    assert outro.get('/api/usuarios').status_code == 401
    assert admin2.delete(f'/api/usuarios/{outro.id}').status_code == 200
    assert admin.get('/api/auth/eu').status_code == 200      # o principal segue de pé


def test_sempre_resta_ao_menos_um_admin_ativo(admin, admin2):
    for _ in range(2):
        admin2.post(f'/api/usuarios/{admin.usuario["id"]}/bloquear')
        admin2.delete(f'/api/usuarios/{admin.usuario["id"]}')
    ativos = [u for u in admin.get('/api/usuarios').get_json() if u['perfil'] == 'admin' and u['status'] == 'ativo']
    assert len(ativos) == 2


def test_repositorio_nunca_exclui_o_principal_nem_com_chamada_direta(app, admin):
    repo = app.extensions['repo']
    repo.excluir_usuario(admin.usuario['id'])
    assert repo.obter_usuario(admin.usuario['id']) is not None


# ------------------------------------------------------------ listagem
def test_listagem_traz_principal_primeiro_e_sem_segredos(admin, aluno, prof):
    lista = admin.get('/api/usuarios').get_json()
    assert lista[0]['principal'] is True and len(lista) == 3
    assert {'id', 'nome', 'email', 'perfil', 'status', 'verificado', 'principal'} <= set(lista[0])
    assert all('senha' not in u for u in lista)

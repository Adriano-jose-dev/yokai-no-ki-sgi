"""
Testes do domínio Auditoria — Log de segurança (Fase 4).

Cobre as regras do steering (Fase 4):
- registrar gera uma entrada; categoria inferida (sensível × geral);
- ações sensíveis isoladas na categoria 'sensivel';
- visão por aluno (filtro por id_aluno, qualquer categoria);
- retenção: descarta 'geral' com mais de 60 dias;
- poda da fila geral: mantém no máximo 50 (remove as mais antigas);
- integração: ações sensíveis de rotas (editar contrato, pagamento, destrancar)
  geram log; exige admin.
"""

from datetime import datetime, timedelta

from main import Aluno, Contrato, RegistroAuditoria
from business import auditoria


def _aluno(db, id_mat="YNK0001", nome="Bianca", plano="Mensalidade"):
    db.add(Aluno(id_matricula=id_mat, nome=nome, status_atividade="Ativo"))
    db.add(Contrato(id_aluno=id_mat, modelo_plano=plano, dia_vencimento=10))
    db.commit()


# --- Unidade: business puro ---

def test_categoria_inferida():
    assert auditoria.categoria_de("editar_contrato") == "geral"
    assert auditoria.categoria_de("apagar_pagamento") == "sensivel"
    assert auditoria.categoria_de("encerrar_matricula") == "sensivel"


def test_registrar_grava_linha(db_session):
    auditoria.registrar(db_session, acao="editar_contrato", autor="admin", id_aluno="YNK0001")
    db_session.commit()
    regs = db_session.query(RegistroAuditoria).all()
    assert len(regs) == 1
    assert regs[0].categoria == "geral"
    assert regs[0].autor == "admin"


def test_retencao_descarta_mais_de_60_dias(db_session):
    antiga = RegistroAuditoria(
        categoria="geral", acao="editar_contrato", autor="admin",
        criado_em=datetime.now() - timedelta(days=70),
    )
    recente = RegistroAuditoria(
        categoria="geral", acao="editar_contrato", autor="admin",
        criado_em=datetime.now(),
    )
    db_session.add_all([antiga, recente])
    db_session.commit()

    removidas = auditoria.aplicar_retencao(db_session)
    db_session.commit()
    assert removidas == 1
    assert db_session.query(RegistroAuditoria).count() == 1


def test_poda_fila_geral_mantem_50(db_session):
    # 60 entradas 'geral' recentes -> poda deve manter 50.
    base = datetime.now()
    for i in range(60):
        db_session.add(
            RegistroAuditoria(
                categoria="geral", acao="editar_contrato", autor="admin",
                criado_em=base - timedelta(minutes=i),
            )
        )
    db_session.commit()

    auditoria.aplicar_retencao(db_session)
    db_session.commit()
    assert db_session.query(RegistroAuditoria).count() == 50


def test_sensivel_nao_e_podado(db_session):
    base = datetime.now()
    # 60 sensíveis recentes + 1 sensível antiga: nada deve ser removido.
    for i in range(60):
        db_session.add(
            RegistroAuditoria(
                categoria="sensivel", acao="apagar_pagamento", autor="admin",
                criado_em=base - timedelta(minutes=i),
            )
        )
    db_session.add(
        RegistroAuditoria(
            categoria="sensivel", acao="apagar_pagamento", autor="admin",
            criado_em=base - timedelta(days=90),
        )
    )
    db_session.commit()

    auditoria.aplicar_retencao(db_session)
    db_session.commit()
    assert db_session.query(RegistroAuditoria).count() == 61


# --- API: listagem com filtros ---

def test_listar_filtra_por_categoria(client, db_session):
    _aluno(db_session)
    # Gera um 'geral' (editar contrato) e um 'sensivel' (destrancar).
    client.put("/alunos/YNK0001/contrato", json={
        "modelo_plano": "Mensalidade", "valor_base": 20.0, "valor_contratual_fixo": 20.0,
        "inclui_shokubai": False, "dia_vencimento": 10, "observacao_financeira": None,
    })
    client.put("/alunos/YNK0001/destrancar", json={})

    gerais = client.get("/auditoria?categoria=geral").json()
    sensiveis = client.get("/auditoria?categoria=sensivel").json()
    assert any(e["acao"] == "editar_contrato" for e in gerais)
    assert any(e["acao"] == "destrancar_aluno" for e in sensiveis)


def test_visao_por_aluno(client, db_session):
    _aluno(db_session)
    client.put("/alunos/YNK0001/destrancar", json={})
    eventos = client.get("/auditoria/aluno/YNK0001").json()
    assert len(eventos) >= 1
    assert all(e["id_aluno"] == "YNK0001" for e in eventos)


def test_pagamento_gera_auditoria_sensivel(client, db_session):
    _aluno(db_session)
    client.post("/pagamentos/receber", json={
        "id_matricula": "YNK0001", "valor_pago": 100.0, "metodo": "Pix",
    })
    sensiveis = client.get("/auditoria?categoria=sensivel").json()
    assert any(e["acao"] == "receber_pagamento" for e in sensiveis)


def test_auditoria_exige_autenticacao(client_sem_auth, db_session):
    assert client_sem_auth.get("/auditoria").status_code == 401

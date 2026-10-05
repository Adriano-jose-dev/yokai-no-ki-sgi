"""
Testes do Financeiro — Conta Corrente (Fase 2 do roadmap).

Cobre as regras travadas no steering (Fase 2):
- mensalidade = Σ valor_base × horas previstas das ocorrências do mês;
- aula CANCELADA pela escola reduz o valor; falta do aluno NÃO altera;
- débito só existe quando GERADO (vencimento), com data de vencimento;
- crédito (pago a mais) abate débito; sobra permanece como crédito;
- geração idempotente (recalcula, não duplica, preservando o quitado);
- ocorrente não paga (só matriculado mensalista entra no cálculo);
- abono de falta só para mensalistas e não altera o valor;
- exigência de admin.
"""

from datetime import date

from main import Aluno, Contrato, Lancamento, AbonoFalta


# Mês de referência fixo para determinismo (sábados de out/2026: 3,10,17,24,31).
ANO, MES = 2026, 10
PERIODO = {"data_inicio": "2026-10-01", "data_fim": "2026-10-31"}


def _aluno_mensalista(db, id_mat="YNK0001", nome="Bianca", dia_venc=15):
    db.add(Aluno(id_matricula=id_mat, nome=nome, status_atividade="Ativo"))
    db.add(
        Contrato(
            id_aluno=id_mat,
            modelo_plano="Mensalidade",
            valor_base=30.0,
            dia_vencimento=dia_venc,
        )
    )
    db.commit()


def _turma(client, nome="No Mori", valor_base=30.0, tipo="Mensalidade",
           rrule="FREQ=WEEKLY;BYDAY=SA", hi="19:00", hf="21:00"):
    return client.post(
        "/turmas",
        json={
            "nome": nome,
            "tipo_pagamento": tipo,
            "classe": "Dojo",
            "valor_base": valor_base,
            "recorrencia_rrule": rrule,
            "hora_inicio": hi,
            "hora_fim": hf,
        },
    ).json()


def _montar_turma_com_aluno(client, db, id_mat="YNK0001", valor_base=30.0):
    """Mensalista matriculado numa turma de Mensalidade com 5 sábados gerados."""
    _aluno_mensalista(db, id_mat=id_mat)
    t = _turma(client, valor_base=valor_base)
    client.post(f"/turmas/{t['id']}/alunos",
                json={"id_aluno": id_mat, "papel": "matriculado"})
    client.post(f"/turmas/{t['id']}/ocorrencias/gerar", json=PERIODO)
    return t


# --- Cálculo da mensalidade pelo calendário ---

def test_mensalidade_soma_horas_do_calendario(client, db_session):
    # 5 sábados × 2h × R$30 = R$300.
    _montar_turma_com_aluno(client, db_session)
    r = client.get(f"/financeiro/YNK0001/mensalidade/previsao?ano={ANO}&mes={MES}")
    assert r.status_code == 200
    dados = r.json()
    assert dados["aulas"] == 5
    assert dados["horas"] == 10.0
    assert dados["valor"] == 300.0


def test_aula_cancelada_reduz_valor(client, db_session):
    t = _montar_turma_com_aluno(client, db_session)
    oc = client.get("/ocorrencias?inicio=2026-10-01&fim=2026-10-31").json()[0]
    client.post(f"/ocorrencias/{oc['id']}/cancelar")
    # Agora 4 aulas × 2h × 30 = 240.
    dados = client.get(
        f"/financeiro/YNK0001/mensalidade/previsao?ano={ANO}&mes={MES}"
    ).json()
    assert dados["aulas"] == 4
    assert dados["valor"] == 240.0


def test_falta_do_aluno_nao_altera_valor(client, db_session):
    """Marcar ausência (presença=False) não muda o valor da mensalidade."""
    t = _montar_turma_com_aluno(client, db_session)
    oc = client.get("/ocorrencias?inicio=2026-10-01&fim=2026-10-31").json()[0]
    client.post(f"/ocorrencias/{oc['id']}/presenca",
                json={"id_aluno": "YNK0001", "presente": False})
    dados = client.get(
        f"/financeiro/YNK0001/mensalidade/previsao?ano={ANO}&mes={MES}"
    ).json()
    # A ocorrência virou 'realizada' (conta igual) — segue 5 aulas × 60 = 300.
    assert dados["aulas"] == 5
    assert dados["valor"] == 300.0


def test_ocorrente_nao_entra_no_calculo(client, db_session):
    """Aluno ocorrente (não matriculado) não gera cobrança da turma."""
    _aluno_mensalista(db_session, id_mat="YNK0009", nome="Legado")
    t = _turma(client)
    client.post(f"/turmas/{t['id']}/alunos",
                json={"id_aluno": "YNK0009", "papel": "ocorrente", "gratuito": True})
    client.post(f"/turmas/{t['id']}/ocorrencias/gerar", json=PERIODO)
    dados = client.get(
        f"/financeiro/YNK0009/mensalidade/previsao?ano={ANO}&mes={MES}"
    ).json()
    assert dados["valor"] == 0.0
    assert dados["aulas"] == 0


# --- Geração do débito (conta corrente) ---

def test_gerar_mensalidade_cria_debito_com_vencimento(client, db_session):
    _montar_turma_com_aluno(client, db_session)
    r = client.post(f"/financeiro/YNK0001/mensalidade/gerar",
                    json={"ano": ANO, "mes": MES})
    assert r.status_code == 200
    assert r.json()["valor"] == 300.0
    assert r.json()["data_vencimento"] == "2026-10-15"  # dia_vencimento=15

    lanc = (
        db_session.query(Lancamento)
        .filter(Lancamento.categoria == "mensalidade")
        .all()
    )
    assert len(lanc) == 1
    assert lanc[0].tipo == "debito"
    assert lanc[0].valor_aberto == 300.0


def test_gerar_mensalidade_idempotente_recalcula(client, db_session):
    t = _montar_turma_com_aluno(client, db_session)
    client.post(f"/financeiro/YNK0001/mensalidade/gerar", json={"ano": ANO, "mes": MES})
    # Cancela uma aula e gera de novo: deve ATUALIZAR, não duplicar.
    oc = client.get("/ocorrencias?inicio=2026-10-01&fim=2026-10-31").json()[0]
    client.post(f"/ocorrencias/{oc['id']}/cancelar")
    r2 = client.post(f"/financeiro/YNK0001/mensalidade/gerar",
                     json={"ano": ANO, "mes": MES})
    assert r2.json()["valor"] == 240.0

    lanc = (
        db_session.query(Lancamento)
        .filter(Lancamento.categoria == "mensalidade")
        .all()
    )
    assert len(lanc) == 1  # não duplicou
    assert lanc[0].valor == 240.0


# --- Conta corrente: débito × crédito ---

def test_pagamento_abate_debito(client, db_session):
    _montar_turma_com_aluno(client, db_session)
    client.post(f"/financeiro/YNK0001/mensalidade/gerar", json={"ano": ANO, "mes": MES})
    # Paga 300 → quita a mensalidade.
    r = client.post(f"/financeiro/YNK0001/pagar", json={"valor": 300.0, "metodo": "Pix"})
    assert r.status_code == 200
    assert r.json()["credito_restante"] == 0.0

    conta = client.get(f"/financeiro/YNK0001/conta").json()
    assert conta["valores_em_aberto"] == 0.0
    assert conta["credito_disponivel"] == 0.0
    assert conta["saldo_liquido"] == 0.0


def test_pagamento_a_mais_vira_credito(client, db_session):
    _montar_turma_com_aluno(client, db_session)
    client.post(f"/financeiro/YNK0001/mensalidade/gerar", json={"ano": ANO, "mes": MES})
    # Paga 500 numa dívida de 300 → sobra 200 de crédito.
    r = client.post(f"/financeiro/YNK0001/pagar", json={"valor": 500.0, "metodo": "Pix"})
    assert r.json()["credito_restante"] == 200.0

    conta = client.get(f"/financeiro/YNK0001/conta").json()
    assert conta["valores_em_aberto"] == 0.0
    assert conta["credito_disponivel"] == 200.0
    assert conta["saldo_liquido"] == 200.0


def test_credito_abate_debito_gerado_depois(client, db_session):
    """Crédito pré-existente abate um débito gerado em seguida."""
    _montar_turma_com_aluno(client, db_session)
    # Paga 100 adiantado (vira crédito, pois ainda não há débito).
    client.post(f"/financeiro/YNK0001/pagar", json={"valor": 100.0, "metodo": "Pix"})
    conta = client.get(f"/financeiro/YNK0001/conta").json()
    assert conta["credito_disponivel"] == 100.0

    # Gera a mensalidade de 300: o crédito de 100 abate na hora.
    client.post(f"/financeiro/YNK0001/mensalidade/gerar", json={"ano": ANO, "mes": MES})
    conta = client.get(f"/financeiro/YNK0001/conta").json()
    assert conta["valores_em_aberto"] == 200.0  # 300 - 100
    assert conta["credito_disponivel"] == 0.0
    assert conta["saldo_liquido"] == -200.0


# --- Abono de falta ---

def test_abono_apenas_mensalista(client, db_session):
    _montar_turma_com_aluno(client, db_session)
    r = client.post("/financeiro/abono",
                    json={"id_aluno": "YNK0001", "justificativa": "Atestado"})
    assert r.status_code == 200
    assert db_session.query(AbonoFalta).count() == 1


def test_abono_recusa_nao_mensalista(client, db_session):
    db_session.add(Aluno(id_matricula="YNK0002", nome="Horista"))
    db_session.add(Contrato(id_aluno="YNK0002", modelo_plano="Horas Livres"))
    db_session.commit()
    r = client.post("/financeiro/abono",
                    json={"id_aluno": "YNK0002", "justificativa": "x"})
    assert r.status_code == 400


def test_abono_nao_altera_valor_mensalidade(client, db_session):
    _montar_turma_com_aluno(client, db_session)
    client.post("/financeiro/abono",
                json={"id_aluno": "YNK0001", "justificativa": "Atestado"})
    dados = client.get(
        f"/financeiro/YNK0001/mensalidade/previsao?ano={ANO}&mes={MES}"
    ).json()
    assert dados["valor"] == 300.0  # inalterado


# --- Guardas ---

def test_conta_aluno_inexistente_404(client, db_session):
    assert client.get("/financeiro/INEXISTENTE/conta").status_code == 404


def test_pagar_valor_invalido_400(client, db_session):
    _aluno_mensalista(db_session)
    assert client.post("/financeiro/YNK0001/pagar",
                       json={"valor": 0, "metodo": "Pix"}).status_code == 400


def test_financeiro_exige_autenticacao(client_sem_auth, db_session):
    assert client_sem_auth.get("/financeiro/YNK0001/conta").status_code == 401

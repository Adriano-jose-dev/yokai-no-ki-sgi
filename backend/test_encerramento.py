"""
Testes do Encerramento de Matrícula — dossiê PDF, retenção de 30 dias,
revogação e expurgo agendado (Hard Delete).

Cobre:
- Encerrar gera o dossiê PDF, marca o aluno como 'Encerrado' e agenda o expurgo;
- O aluno encerrado some das telas do dia a dia (tatame, presença, lista geral);
- O dossiê pode ser baixado (PDF válido);
- Revogar restaura o aluno ao estado anterior e remove o registro;
- O job de expurgo apaga o registro (e dependentes) após a janela de 30 dias;
- Acesso exige autenticação (rotas protegidas por papel admin).
"""

from datetime import date, datetime, timedelta

from main import Aluno, Contrato, Sessao, Pagamento, Presenca, EncerramentoMatricula
from business.scheduler import varrer_expurgo_matriculas
import business.scheduler as sched


def _criar_aluno(db, id_matricula="YNK0001", nome="Aluno Enc", status="Ativo"):
    db.add(Aluno(id_matricula=id_matricula, nome=nome, status_atividade=status))
    db.add(Contrato(id_aluno=id_matricula, modelo_plano="Horas Livres"))
    db.commit()


def test_encerrar_gera_dossie_e_agenda_expurgo(client, db_session):
    _criar_aluno(db_session)

    resp = client.post("/alunos/YNK0001/encerrar")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "Matrícula encerrada"
    assert body["dossie"].endswith(".pdf")

    aluno = db_session.query(Aluno).filter(Aluno.id_matricula == "YNK0001").first()
    assert aluno.status_atividade == "Encerrado"

    enc = (
        db_session.query(EncerramentoMatricula)
        .filter(EncerramentoMatricula.id_aluno == "YNK0001")
        .first()
    )
    assert enc is not None
    assert enc.estado_anterior == "Ativo"
    assert enc.dossie_pdf is not None and len(enc.dossie_pdf) > 0
    # Expurgo agendado para ~30 dias à frente.
    assert enc.data_expurgo >= date.today() + timedelta(days=29)


def test_dossie_e_um_pdf_valido(client, db_session):
    _criar_aluno(db_session)
    client.post("/alunos/YNK0001/encerrar")

    resp = client.get("/alunos/YNK0001/dossie")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    # Assinatura de arquivo PDF.
    assert resp.content[:4] == b"%PDF"


def test_encerrado_some_das_telas(client, db_session):
    _criar_aluno(db_session, id_matricula="YNK0001", nome="Ativo", status="Ativo")
    _criar_aluno(db_session, id_matricula="YNK0002", nome="Sair", status="Ativo")

    client.post("/alunos/YNK0002/encerrar")

    # Lista geral
    ids_geral = [a["id_matricula"] for a in client.get("/alunos").json()]
    assert "YNK0001" in ids_geral and "YNK0002" not in ids_geral
    # Tatame
    ids_tatame = [a["id_matricula"] for a in client.get("/tatame/ativos").json()]
    assert "YNK0002" not in ids_tatame
    # Presença
    hoje = date.today().isoformat()
    ids_pres = [a["id_matricula"] for a in client.get(f"/presenca/diaria/{hoje}").json()]
    assert "YNK0002" not in ids_pres


def test_encerrada_aparece_na_aba_de_encerradas(client, db_session):
    _criar_aluno(db_session, id_matricula="YNK0009", nome="Encerrado Nove")
    client.post("/alunos/YNK0009/encerrar")

    lista = client.get("/encerramentos").json()
    ids = [e["id_matricula"] for e in lista]
    assert "YNK0009" in ids
    reg = next(e for e in lista if e["id_matricula"] == "YNK0009")
    assert reg["dias_restantes"] >= 29


def test_encerrar_duas_vezes_falha(client, db_session):
    _criar_aluno(db_session)
    client.post("/alunos/YNK0001/encerrar")
    resp = client.post("/alunos/YNK0001/encerrar")
    assert resp.status_code == 400


def test_revogar_restaura_estado_anterior(client, db_session):
    # Aluno estava 'Trancado' antes de encerrar; revogar deve devolver a 'Trancado'.
    _criar_aluno(db_session, id_matricula="YNK0007", nome="Volta", status="Trancado")
    client.post("/alunos/YNK0007/encerrar")

    resp = client.post("/alunos/YNK0007/revogar-encerramento")
    assert resp.status_code == 200
    assert resp.json()["estado_restaurado"] == "Trancado"

    aluno = db_session.query(Aluno).filter(Aluno.id_matricula == "YNK0007").first()
    assert aluno.status_atividade == "Trancado"
    # O registro de encerramento foi removido.
    assert (
        db_session.query(EncerramentoMatricula)
        .filter(EncerramentoMatricula.id_aluno == "YNK0007")
        .first()
        is None
    )


def test_expurgo_apaga_apos_janela(client, db_session, monkeypatch):
    _criar_aluno(db_session, id_matricula="YNK0005", nome="Expurgar")
    db_session.add(Pagamento(id_aluno="YNK0005", valor=50.0, metodo="Pix"))
    db_session.add(Presenca(id_aluno="YNK0005", data=date.today(), status="Presente"))
    db_session.commit()

    client.post("/alunos/YNK0005/encerrar")

    # Força o vencimento da janela: coloca a data_expurgo no passado.
    enc = (
        db_session.query(EncerramentoMatricula)
        .filter(EncerramentoMatricula.id_aluno == "YNK0005")
        .first()
    )
    enc.data_expurgo = date.today() - timedelta(days=1)
    db_session.commit()

    # O job abre a própria sessão via SessionLocal; apontamos para o banco de teste.
    monkeypatch.setattr(sched, "SessionLocal", lambda: db_session)
    # Evita que o job feche a sessão compartilhada do teste.
    monkeypatch.setattr(db_session, "close", lambda: None)

    expurgados = varrer_expurgo_matriculas()
    assert expurgados == 1

    # Aluno e dependentes eliminados do banco.
    assert (
        db_session.query(Aluno).filter(Aluno.id_matricula == "YNK0005").first() is None
    )
    assert (
        db_session.query(Pagamento).filter(Pagamento.id_aluno == "YNK0005").count() == 0
    )
    assert (
        db_session.query(EncerramentoMatricula)
        .filter(EncerramentoMatricula.id_aluno == "YNK0005")
        .first()
        is None
    )


def test_encerrar_exige_autenticacao(client_sem_auth, db_session):
    _criar_aluno(db_session)
    resp = client_sem_auth.post("/alunos/YNK0001/encerrar")
    assert resp.status_code == 401

"""
Testes do cálculo de custo de sessão (Tatame) — Tarefa 2.4 / Requisitos 1.2, 1.3.

Valida a hierarquia de cobrança do steering `regras-negocio-ykr.md` (seção 1.1):
- hora_flexivel: horas * valor_base
- Mensalidade: (horas - franquia) * valor_base, com custo 0 dentro da franquia
- Intensivão: horas * (valor_base * 1.5)
- Horas Livres: horas * valor_base
- desconto aplicado; custo nunca negativo.

O custo é apurado em `POST /sessao/stop`, que define `hora_saida = agora`. Para
tornar as horas decorridas determinísticas, cada teste cria a sessão diretamente
no banco com `hora_entrada = agora - N horas`.
"""

from datetime import datetime, timedelta

from main import Aluno, Contrato, Sessao


def _criar_aluno_contrato(
    db,
    id_matricula="YNK0001",
    modelo_plano="Horas Livres",
    valor_base=20.0,
    horas_franquia=3,
    hora_flexivel=False,
    status="Ativo",
):
    aluno = Aluno(
        id_matricula=id_matricula,
        nome="Aluno Cobranca",
        status_atividade=status,
        hora_flexivel=hora_flexivel,
    )
    contrato = Contrato(
        id_aluno=id_matricula,
        modelo_plano=modelo_plano,
        valor_base=valor_base,
        horas_franquia=horas_franquia,
    )
    db.add(aluno)
    db.add(contrato)
    db.commit()
    return aluno, contrato


def _abrir_sessao(db, id_matricula, horas_atras):
    """Cria uma sessão aberta com entrada `horas_atras` horas no passado."""
    sessao = Sessao(
        id_aluno=id_matricula,
        hora_entrada=datetime.now() - timedelta(hours=horas_atras),
        hora_saida=None,
    )
    db.add(sessao)
    db.commit()


def _finalizar(client, id_matricula, desconto=0.0):
    resp = client.post(
        "/sessao/stop",
        json={"id_matricula": id_matricula, "desconto_aplicado": desconto},
    )
    assert resp.status_code == 200
    return resp.json()["valor"]


def test_horas_livres(client, db_session):
    _criar_aluno_contrato(db_session, modelo_plano="Horas Livres", valor_base=20.0)
    _abrir_sessao(db_session, "YNK0001", horas_atras=2)
    valor = _finalizar(client, "YNK0001")
    # 2h * 20 = 40 (tolerância por causa dos milissegundos decorridos)
    assert abs(valor - 40.0) < 0.5


def test_mensalidade_dentro_da_franquia(client, db_session):
    """Dentro da franquia de 3h o custo deve ser 0."""
    _criar_aluno_contrato(
        db_session, modelo_plano="Mensalidade", valor_base=20.0, horas_franquia=3
    )
    _abrir_sessao(db_session, "YNK0001", horas_atras=2)
    valor = _finalizar(client, "YNK0001")
    assert valor == 0.0


def test_mensalidade_exatamente_na_franquia(client, db_session):
    """Exatamente na franquia (<= 3h) o custo continua 0, nunca negativo."""
    _criar_aluno_contrato(
        db_session, modelo_plano="Mensalidade", valor_base=20.0, horas_franquia=3
    )
    # 2.999h para garantir <= 3h mesmo com os milissegundos decorridos.
    _abrir_sessao(db_session, "YNK0001", horas_atras=2.999)
    valor = _finalizar(client, "YNK0001")
    assert valor == 0.0


def test_mensalidade_fora_da_franquia(client, db_session):
    """Acima da franquia cobra apenas o excedente: (5 - 3) * 20 = 40."""
    _criar_aluno_contrato(
        db_session, modelo_plano="Mensalidade", valor_base=20.0, horas_franquia=3
    )
    _abrir_sessao(db_session, "YNK0001", horas_atras=5)
    valor = _finalizar(client, "YNK0001")
    assert abs(valor - 40.0) < 0.5


def test_mensalidade_usa_franquia_do_contrato(client, db_session):
    """A franquia vem do contrato: com franquia 3, 4h geram (4-3)*20 = 20.

    (Se ainda usasse o 4 antigo hard-coded, o custo seria 0.)
    """
    _criar_aluno_contrato(
        db_session, modelo_plano="Mensalidade", valor_base=20.0, horas_franquia=3
    )
    _abrir_sessao(db_session, "YNK0001", horas_atras=4)
    valor = _finalizar(client, "YNK0001")
    assert abs(valor - 20.0) < 0.5


def test_intensivao(client, db_session):
    """Intensivão: horas * (valor_base * 1.5) = 2 * 30 = 60."""
    _criar_aluno_contrato(
        db_session, modelo_plano="Intensivão", valor_base=20.0
    )
    _abrir_sessao(db_session, "YNK0001", horas_atras=2)
    valor = _finalizar(client, "YNK0001")
    assert abs(valor - 60.0) < 0.75


def test_hora_flexivel_ignora_plano(client, db_session):
    """hora_flexivel cobra horas * valor_base mesmo sendo Mensalidade."""
    _criar_aluno_contrato(
        db_session,
        modelo_plano="Mensalidade",
        valor_base=20.0,
        horas_franquia=3,
        hora_flexivel=True,
    )
    _abrir_sessao(db_session, "YNK0001", horas_atras=2)
    valor = _finalizar(client, "YNK0001")
    assert abs(valor - 40.0) < 0.5


def test_desconto_aplicado(client, db_session):
    """Desconto reduz o custo: 2h*20 = 40, menos 10 = 30."""
    _criar_aluno_contrato(db_session, modelo_plano="Horas Livres", valor_base=20.0)
    _abrir_sessao(db_session, "YNK0001", horas_atras=2)
    valor = _finalizar(client, "YNK0001", desconto=10.0)
    assert abs(valor - 30.0) < 0.5


def test_desconto_nunca_deixa_negativo(client, db_session):
    """Desconto maior que o custo resulta em 0, nunca negativo."""
    _criar_aluno_contrato(db_session, modelo_plano="Horas Livres", valor_base=20.0)
    _abrir_sessao(db_session, "YNK0001", horas_atras=2)
    valor = _finalizar(client, "YNK0001", desconto=1000.0)
    assert valor == 0.0

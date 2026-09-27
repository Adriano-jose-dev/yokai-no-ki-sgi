"""
Geração do Dossiê PDF do aluno — SGI-YKR (Encerramento de matrícula).

O dossiê é a **prova documental completa** gerada no ato do encerramento: um
espelho de tudo que o sistema conhece sobre o aluno (ficha, graduação, contrato,
histórico de sessões, pagamentos e presenças). Depois do expurgo (Hard Delete
após 30 dias), este PDF é o único registro que resta — por isso precisa ser
completo.

Implementado com reportlab (puro-Python), retornando os bytes do PDF para que o
chamador decida onde guardar (aqui, guardamos no próprio registro de
encerramento no banco).
"""

from __future__ import annotations

import io
import json
from datetime import date, datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from models import Aluno, Contrato, Sessao, Pagamento, Presenca

# Cores da identidade YKR (carmim e índigo).
_CARMESIM = colors.HexColor("#b32a3f")
_SUMI = colors.HexColor("#1c2044")
_SUMI_CLARO = colors.HexColor("#e6e8f5")


def _fmt_data(valor) -> str:
    if valor is None:
        return "—"
    if isinstance(valor, (date, datetime)):
        return valor.strftime("%d/%m/%Y")
    return str(valor)


def _fmt_moeda(valor) -> str:
    try:
        return f"R$ {float(valor or 0):.2f}".replace(".", ",")
    except (TypeError, ValueError):
        return "R$ 0,00"


def _sim_nao(v) -> str:
    return "Sim" if v else "Não"


def gerar_dossie_pdf(db, aluno: Aluno) -> bytes:
    """Monta o dossiê PDF completo do aluno e retorna os bytes.

    Args:
        db: sessão SQLAlchemy ativa (para buscar contrato/sessões/pagamentos).
        aluno: instância de `Aluno`.

    Returns:
        bytes do arquivo PDF.
    """
    contrato = (
        db.query(Contrato).filter(Contrato.id_aluno == aluno.id_matricula).first()
    )
    sessoes = (
        db.query(Sessao)
        .filter(Sessao.id_aluno == aluno.id_matricula)
        .order_by(Sessao.hora_entrada.desc())
        .all()
    )
    pagamentos = (
        db.query(Pagamento)
        .filter(Pagamento.id_aluno == aluno.id_matricula)
        .order_by(Pagamento.data_pagamento.desc())
        .all()
    )
    presencas = (
        db.query(Presenca)
        .filter(Presenca.id_aluno == aluno.id_matricula)
        .order_by(Presenca.data.desc())
        .all()
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title=f"Dossiê — {aluno.nome}",
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    estilos = getSampleStyleSheet()
    titulo = ParagraphStyle(
        "TituloYKR",
        parent=estilos["Title"],
        textColor=_SUMI,
        fontSize=18,
    )
    subtitulo = ParagraphStyle(
        "SubYKR",
        parent=estilos["Heading2"],
        textColor=_CARMESIM,
        fontSize=12,
        spaceBefore=14,
        spaceAfter=6,
    )
    normal = estilos["Normal"]
    rodape = ParagraphStyle(
        "RodapeYKR", parent=estilos["Normal"], fontSize=8, textColor=colors.grey
    )

    elementos = []

    # --- Cabeçalho ---
    elementos.append(Paragraph("Dossiê de Matrícula — Yōkai no Ki Ryūha", titulo))
    elementos.append(
        Paragraph(
            f"Documento gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')} · "
            f"Matrícula <b>{aluno.id_matricula}</b>",
            rodape,
        )
    )
    elementos.append(Spacer(1, 0.3 * cm))

    def secao(titulo_txt, linhas):
        """Adiciona uma seção com uma tabela de duas colunas (rótulo | valor)."""
        elementos.append(Paragraph(titulo_txt, subtitulo))
        dados = [[Paragraph(f"<b>{r}</b>", normal), Paragraph(str(v), normal)] for r, v in linhas]
        t = Table(dados, colWidths=[5.5 * cm, 10.5 * cm])
        t.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.25, _SUMI_CLARO),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        elementos.append(t)

    # --- Dados pessoais ---
    secao(
        "1. Dados Pessoais",
        [
            ("Nome", aluno.nome or "—"),
            ("Data de nascimento", _fmt_data(aluno.data_nascimento)),
            ("WhatsApp", aluno.whatsapp or "—"),
            ("E-mail", aluno.email or "—"),
            ("Endereço", aluno.endereco or "—"),
            ("Nacionalidade", aluno.nacionalidade or "—"),
            ("Naturalidade", aluno.naturalidade or "—"),
            ("Nome do pai", aluno.nome_pai or "—"),
            ("Nome da mãe", aluno.nome_mae or "—"),
        ],
    )

    # --- Contato de emergência ---
    secao(
        "2. Contato de Emergência",
        [
            ("Nome", aluno.contato_emergencia_nome or "—"),
            ("Parentesco", aluno.contato_emergencia_parentesco or "—"),
            ("Telefone", aluno.contato_emergencia_telefone or "—"),
        ],
    )

    # --- Perfil marcial ---
    secao(
        "3. Perfil Marcial",
        [
            ("Graduação atual", aluno.graduacao_atual or "—"),
            ("Data de início", _fmt_data(aluno.data_inicio)),
            ("Última graduação", _fmt_data(aluno.data_ultima_graduacao)),
            ("Modo de treino", aluno.modo_treino or "—"),
            ("Histórico marcial", aluno.historico_marcial or "—"),
            ("Equipamento próprio", _sim_nao(aluno.equipamento_proprio)),
            ("Termo de risco assinado", _sim_nao(aluno.termo_risco_assinado)),
            ("Autorização de imagem", _sim_nao(aluno.autorizacao_imagem)),
            ("Restrição médica", aluno.restricao_medica or "—"),
        ],
    )

    # --- Contrato ---
    if contrato:
        secao(
            "4. Contrato",
            [
                ("Plano", contrato.modelo_plano or "—"),
                ("Valor base (hora)", _fmt_moeda(contrato.valor_base)),
                ("Valor contratual fixo", _fmt_moeda(contrato.valor_contratual_fixo)),
                ("Taxa de admissão pendente", _fmt_moeda(contrato.taxa_admissao_saldo)),
                ("Dia de vencimento", contrato.dia_vencimento or "—"),
                ("Inclui Shokubai", _sim_nao(contrato.inclui_shokubai)),
                ("Observação financeira", contrato.observacao_financeira or "—"),
            ],
        )

    # --- Diário pedagógico ---
    elementos.append(Paragraph("5. Diário Pedagógico", subtitulo))
    try:
        notas = json.loads(aluno.diario_pedagogico or "[]")
    except (ValueError, TypeError):
        notas = []
    if notas:
        for nota in notas:
            elementos.append(
                Paragraph(
                    f"<b>{nota.get('data', '')} — {nota.get('titulo', '')}</b>: "
                    f"{nota.get('texto', '')}",
                    normal,
                )
            )
            elementos.append(Spacer(1, 0.1 * cm))
    else:
        elementos.append(Paragraph("Sem anotações pedagógicas.", normal))

    # --- Histórico de sessões ---
    elementos.append(Paragraph("6. Histórico de Sessões (Tatame)", subtitulo))
    if sessoes:
        linhas = [["Entrada", "Saída", "Valor", "Desconto", "Pago"]]
        for s in sessoes:
            linhas.append(
                [
                    _fmt_data(s.hora_entrada)
                    + (s.hora_entrada.strftime(" %H:%M") if s.hora_entrada else ""),
                    (s.hora_saida.strftime("%d/%m/%Y %H:%M") if s.hora_saida else "Em aberto"),
                    _fmt_moeda(s.valor_apurado),
                    _fmt_moeda(s.desconto_aplicado),
                    _sim_nao(s.pago),
                ]
            )
        _tabela_listagem(elementos, linhas)
    else:
        elementos.append(Paragraph("Sem sessões registradas.", normal))

    # --- Pagamentos ---
    elementos.append(Paragraph("7. Histórico de Pagamentos", subtitulo))
    if pagamentos:
        linhas = [["Data", "Valor", "Método"]]
        for p in pagamentos:
            linhas.append([_fmt_data(p.data_pagamento), _fmt_moeda(p.valor), p.metodo or "—"])
        _tabela_listagem(elementos, linhas)
    else:
        elementos.append(Paragraph("Sem pagamentos registrados.", normal))

    # --- Presenças ---
    elementos.append(Paragraph("8. Histórico de Presenças", subtitulo))
    if presencas:
        linhas = [["Data", "Status"]]
        for pr in presencas:
            linhas.append([_fmt_data(pr.data), pr.status or "—"])
        _tabela_listagem(elementos, linhas)
    else:
        elementos.append(Paragraph("Sem presenças registradas.", normal))

    elementos.append(Spacer(1, 0.5 * cm))
    elementos.append(
        Paragraph(
            "Documento emitido pelo SGI-YKR para fins de comprovação do histórico "
            "da matrícula encerrada. Após a emissão, os dados pessoais do aluno "
            "são removidos do sistema conforme a política de retenção.",
            rodape,
        )
    )

    doc.build(elementos)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def _tabela_listagem(elementos, linhas):
    """Renderiza uma tabela de listagem com cabeçalho estilizado."""
    t = Table(linhas, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _SUMI),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, _SUMI_CLARO),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _SUMI_CLARO]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    elementos.append(t)

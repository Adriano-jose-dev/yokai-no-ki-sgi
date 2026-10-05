"""
Rotas de domínio Aluno/Secretaria — SGI-YKR.

Matrícula, upgrade, edição de ficha e contrato, valor base, trava/destrava,
progresso, promoção, status, soft delete, notas e diário pedagógico.
Comportamento idêntico ao monolito original.
"""

import re
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Aluno, Contrato, Sessao, Pagamento, Presenca, Usuario
from schemas import (
    NovoAlunoRequest,
    EditarFichaRequest,
    EditarContratoRequest,
    AtualizarValorBaseRequest,
    PromoverRequest,
    StatusRequest,
    UpdateNotaRequest,
)
from business.trava import avaliar_trava_inadimplencia
from business.helpers import formata_hora, encerrar_sessao_aberta
from business.auth import requer_papel, get_usuario_atual
from business import auditoria

router = APIRouter(
    tags=["Alunos & Secretaria"], dependencies=[Depends(requer_papel("admin"))]
)


@router.get(
    "/alunos",
    summary="Listar todos os alunos",
    description=(
        "Retorna a lista resumida de alunos (id, nome, status e modo de "
        "treino), incluindo `Inativo` — o front decide o que exibir."
    ),
)
def listar_todos_alunos(db: Session = Depends(get_db)):
    return [
        {
            "id_matricula": a.id_matricula,
            "nome": a.nome,
            "status_atividade": a.status_atividade,
            "modo_treino": a.modo_treino,
        }
        # Alunos "Encerrado" não aparecem na lista geral — vivem na aba
        # "Matrículas encerradas" até o expurgo.
        for a in db.query(Aluno).filter(Aluno.status_atividade != "Encerrado").all()
    ]


@router.post(
    "/alunos/matricula",
    summary="Matricular novo aluno",
    description=(
        "Cria um aluno e seu contrato associado.\n\n"
        "- Gera o `id_matricula` no formato `YNK<AAAAMM><sequencial>`.\n"
        "- Para **Aula Experimental**, a autorização de imagem é forçada a "
        "`false`.\n"
        "- O `dia_vencimento` só é relevante para o plano **Mensalidade**.\n"
        "- Menores de 18 anos exigem `nome_pai` e `nome_mae` (validação de "
        "menoridade da secretaria)."
    ),
)
def matricular_aluno(req: NovoAlunoRequest, db: Session = Depends(get_db)):
    hoje = date.today()
    total_escola = db.query(Aluno).count()
    id_gerado = f"YNK{hoje.strftime('%Y%m')}{total_escola + 1:03d}"
    permissao_imagem = (
        req.autorizacao_imagem if req.status_atividade != "Aula Experimental" else False
    )

    novo_aluno = Aluno(
        id_matricula=id_gerado,
        nome=req.nome,
        data_nascimento=req.data_nascimento,
        whatsapp=req.whatsapp,
        email=req.email,
        endereco=req.endereco,
        nacionalidade=req.nacionalidade,
        naturalidade=req.naturalidade,
        nome_pai=req.nome_pai,
        nome_mae=req.nome_mae,
        contato_emergencia_nome=req.contato_emergencia_nome,
        contato_emergencia_parentesco=req.contato_emergencia_parentesco,
        contato_emergencia_telefone=req.contato_emergencia_telefone,
        historico_marcial=req.historico_marcial,
        equipamento_proprio=req.equipamento_proprio,
        termo_risco_assinado=req.termo_risco_assinado,
        restricao_medica=req.restricao_medica,
        autorizacao_imagem=permissao_imagem,
        data_inicio=hoje,
        data_ultima_graduacao=hoje,
        status_atividade=req.status_atividade,
        diario_pedagogico="[]",
        modo_treino=req.modo_treino,
        acordo_contratual=req.acordo_contratual,
    )
    db.add(novo_aluno)
    db.add(
        Contrato(
            id_aluno=id_gerado,
            modelo_plano=req.modelo_plano,
            valor_base=req.valor_base_contrato,
            valor_contratual_fixo=req.valor_base_contrato,
            taxa_admissao_saldo=req.taxa_admissao_valor,
            inclui_shokubai=req.inclui_shokubai,
            dia_vencimento=req.dia_vencimento,
        )
    )
    db.commit()
    return {"id_matricula": id_gerado, "nome": req.nome}


@router.put(
    "/alunos/{id_matricula}/upgrade",
    summary="Converter/atualizar cadastro completo (ficha + contrato)",
    description=(
        "Atualiza de uma vez os dados de ficha e de contrato — usado, por "
        "exemplo, para promover uma Aula Experimental a matrícula completa."
    ),
)
def upgrade_aluno(
    id_matricula: str, req: NovoAlunoRequest, db: Session = Depends(get_db)
):
    aluno = db.query(Aluno).filter(Aluno.id_matricula == id_matricula).first()
    contrato = db.query(Contrato).filter(Contrato.id_aluno == id_matricula).first()
    aluno.nome = req.nome
    aluno.data_nascimento = req.data_nascimento
    aluno.whatsapp = req.whatsapp
    aluno.email = req.email
    aluno.endereco = req.endereco
    aluno.nacionalidade = req.nacionalidade
    aluno.naturalidade = req.naturalidade
    aluno.nome_pai = req.nome_pai
    aluno.nome_mae = req.nome_mae
    aluno.historico_marcial = req.historico_marcial
    aluno.equipamento_proprio = req.equipamento_proprio
    aluno.termo_risco_assinado = req.termo_risco_assinado
    aluno.restricao_medica = req.restricao_medica
    aluno.autorizacao_imagem = req.autorizacao_imagem
    aluno.status_atividade = req.status_atividade
    aluno.modo_treino = req.modo_treino
    aluno.acordo_contratual = req.acordo_contratual
    contrato.modelo_plano = req.modelo_plano
    contrato.valor_base = req.valor_base_contrato
    contrato.valor_contratual_fixo = req.valor_base_contrato
    contrato.inclui_shokubai = req.inclui_shokubai
    contrato.taxa_admissao_saldo = req.taxa_admissao_valor
    contrato.dia_vencimento = req.dia_vencimento
    db.commit()
    return {"status": "Upgrade concluído"}


@router.put(
    "/alunos/{id_matricula}/editar",
    summary="Editar ficha cadastral do aluno",
    description="Atualiza apenas os dados pessoais/cadastrais (sem tocar no contrato).",
)
def editar_aluno(
    id_matricula: str, req: EditarFichaRequest, db: Session = Depends(get_db)
):
    aluno = db.query(Aluno).filter(Aluno.id_matricula == id_matricula).first()
    aluno.nome = req.nome
    aluno.data_nascimento = req.data_nascimento
    aluno.whatsapp = req.whatsapp
    aluno.email = req.email
    aluno.endereco = req.endereco
    aluno.nacionalidade = req.nacionalidade
    aluno.naturalidade = req.naturalidade
    aluno.nome_pai = req.nome_pai
    aluno.nome_mae = req.nome_mae
    aluno.equipamento_proprio = req.equipamento_proprio
    aluno.historico_marcial = req.historico_marcial
    aluno.restricao_medica = req.restricao_medica
    aluno.modo_treino = req.modo_treino
    aluno.graduacao_atual = req.graduacao_atual
    aluno.acordo_contratual = req.acordo_contratual
    db.commit()
    return {"status": "Ficha atualizada"}


@router.put(
    "/alunos/{id_matricula}/contrato",
    summary="Editar contrato e reavaliar inadimplência",
    description=(
        "Atualiza os dados do contrato (plano, valores, vencimento, "
        "observação financeira) e reavalia a **trava de inadimplência**:\n\n"
        "- Se o plano for **Mensalidade**, chama a regra única de trava "
        "(bloqueia se atrasado > 5 dias e sem `[ACORDO]`; reverte se em dia).\n"
        "- Se o aluno **saiu** da Mensalidade e estava travado "
        "automaticamente, a trava é revertida (deixa de fazer sentido)."
    ),
)
def editar_contrato(
    id_matricula: str,
    req: EditarContratoRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    contrato = db.query(Contrato).filter(Contrato.id_aluno == id_matricula).first()
    aluno = db.query(Aluno).filter(Aluno.id_matricula == id_matricula).first()

    contrato.modelo_plano = req.modelo_plano
    contrato.valor_base = req.valor_base
    contrato.valor_contratual_fixo = req.valor_contratual_fixo
    contrato.inclui_shokubai = req.inclui_shokubai
    contrato.dia_vencimento = req.dia_vencimento
    contrato.observacao_financeira = req.observacao_financeira

    auditoria.registrar(
        db,
        acao="editar_contrato",
        autor=usuario.username,
        id_aluno=id_matricula,
        descricao=f"Contrato editado (plano {req.modelo_plano}).",
    )

    hoje = date.today()
    if contrato.modelo_plano == "Mensalidade":
        avaliar_trava_inadimplencia(db, aluno, contrato, hoje)
    elif aluno.status_atividade == "Trancado" and "[TRAVA AUTOMÁTICA]" in (
        contrato.observacao_financeira or ""
    ):
        # Aluno saiu da Mensalidade (ex.: Horas Livres/Intensivão): a trava
        # automática deixa de fazer sentido, então revertemos.
        aluno.status_atividade = "Ativo"
        contrato.observacao_financeira = re.sub(
            r"\[TRAVA AUTOMÁTICA\].*?\. ", "", contrato.observacao_financeira
        )

    db.commit()
    return {"status": "Contrato Atualizado"}


@router.put(
    "/alunos/{id_matricula}/valor-base",
    summary="Atualizar valor base do contrato",
    description=(
        "Ajusta apenas o `valor_base` (valor da hora) usado no cálculo de "
        "custo das sessões. Retorna **404** se o aluno ou o contrato não "
        "existir."
    ),
)
def atualizar_valor_base(
    id_matricula: str, req: AtualizarValorBaseRequest, db: Session = Depends(get_db)
):
    aluno = db.query(Aluno).filter(Aluno.id_matricula == id_matricula).first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    contrato = db.query(Contrato).filter(Contrato.id_aluno == id_matricula).first()
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")

    contrato.valor_base = req.valor_base
    db.commit()
    return {"status": "Valor base atualizado", "valor_base": contrato.valor_base}


@router.put(
    "/alunos/{id_matricula}/destrancar",
    summary="Destrancar aluno (liberar por acordo)",
    description=(
        "Libera manualmente um aluno trancado: volta o status para `Ativo`, "
        "remove o prefixo `[TRAVA AUTOMÁTICA]` e insere `[ACORDO]` na "
        "observação financeira, o que passa a fazer **bypass** da trava "
        "automática nas próximas avaliações."
    ),
)
def destrancar_aluno(
    id_matricula: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    aluno = db.query(Aluno).filter(Aluno.id_matricula == id_matricula).first()
    contrato = db.query(Contrato).filter(Contrato.id_aluno == id_matricula).first()
    aluno.status_atividade = "Ativo"
    nota_atual = contrato.observacao_financeira or ""
    if "[ACORDO]" not in nota_atual:
        nota_limpa = re.sub(r"\[TRAVA AUTOMÁTICA\].*?\. ", "", nota_atual)
        contrato.observacao_financeira = f"[ACORDO] Liberado após trava. {nota_limpa}"
    auditoria.registrar(
        db,
        acao="destrancar_aluno",
        autor=usuario.username,
        id_aluno=id_matricula,
        descricao="Aluno destrancado (acordo registrado).",
    )
    db.commit()
    return {"status": "Destrancado"}


@router.get(
    "/alunos/{id_matricula}/progresso",
    summary="Painel completo do aluno (progresso, pendências e histórico)",
    description=(
        "Retorna a visão consolidada do aluno: ficha, progressão marcial, "
        "pendências financeiras, histórico de sessões, pagamentos e "
        "presenças.\n\n"
        "- **Meta de graduação**: 5 meses para Gakusei (Ashigaru/Kyu) e 12 "
        "meses para Bushi/Dan; o campo `meses_faltantes` indica quanto falta "
        "para o próximo exame.\n"
        "- **Avaliação sob demanda (lazy)** da trava de inadimplência: esta "
        "rota reavalia e aplica a trava caso o aluno esteja em atraso."
    ),
)
def obter_progresso(id_matricula: str, db: Session = Depends(get_db)):
    aluno = db.query(Aluno).filter(Aluno.id_matricula == id_matricula).first()
    contrato = db.query(Contrato).filter(Contrato.id_aluno == id_matricula).first()
    hoje = date.today()
    idade = (
        (
            hoje.year
            - aluno.data_nascimento.year
            - (
                (hoje.month, hoje.day)
                < (aluno.data_nascimento.month, aluno.data_nascimento.day)
            )
        )
        if aluno.data_nascimento
        else None
    )

    data_base_grad = aluno.data_ultima_graduacao or aluno.data_inicio
    meses_na_grad = (
        (hoje.year - data_base_grad.year) * 12 + hoje.month - data_base_grad.month
    )

    is_gakusei = (
        "ashigaru" in aluno.graduacao_atual.lower()
        or "kyu" in aluno.graduacao_atual.lower()
    )
    meta_meses = 5 if is_gakusei else 12
    prog_pct = (
        min(100, int((meses_na_grad / meta_meses) * 100)) if meta_meses > 0 else 100
    )
    apto = meses_na_grad >= meta_meses
    meses_faltantes = max(0, meta_meses - meses_na_grad)

    atraso_critico = avaliar_trava_inadimplencia(db, aluno, contrato, hoje)
    db.commit()

    sessoes = (
        db.query(Sessao)
        .filter(Sessao.id_aluno == id_matricula, Sessao.hora_saida != None)
        .all()
    )
    historico, total_horas = [], 0.0
    for s in sessoes:
        horas_dec = (s.hora_saida - s.hora_entrada).total_seconds() / 3600
        total_horas += horas_dec
        historico.append(
            {
                "data": s.hora_entrada.strftime("%d/%m/%Y"),
                "horario": f"{s.hora_entrada.strftime('%H:%M:%S')} às {s.hora_saida.strftime('%H:%M:%S')}",
                "horas_treinadas_formatadas": formata_hora(horas_dec),
                "valor": s.valor_apurado,
                "desconto": s.desconto_aplicado,
                "diario_sensei": s.diario_sensei,
                "pago": s.pago,
                "status_pagamento": (
                    "PRESENÇA"
                    if (contrato.modelo_plano == "Mensalidade" and s.valor_apurado == 0)
                    else ("PAGO" if s.pago else "PENDENTE")
                ),
            }
        )

    painel_pendencias = []
    if contrato and contrato.taxa_admissao_saldo > 0:
        painel_pendencias.append(
            {
                "nome": (
                    "Restante Matrícula + Shokubai"
                    if contrato.inclui_shokubai
                    else "Restante Matrícula"
                ),
                "valor": contrato.taxa_admissao_saldo,
            }
        )

    if contrato and contrato.modelo_plano == "Mensalidade":
        data_venc = date(hoje.year, hoje.month, contrato.dia_vencimento)
        valor_com_juros = contrato.valor_contratual_fixo
        if hoje > data_venc:
            dias_atraso = (hoje - data_venc).days
            valor_com_juros += dias_atraso * 0.50
        painel_pendencias.append(
            {
                "nome": f"Mensalidade Ref. {hoje.strftime('%m/%Y')} (Venc. {contrato.dia_vencimento:02d})",
                "valor": round(valor_com_juros, 2),
            }
        )

    for s in sessoes:
        if not s.pago and s.valor_apurado > 0:
            painel_pendencias.append(
                {
                    "nome": f"Hora Extra ({s.hora_entrada.strftime('%d/%m')})",
                    "valor": s.valor_apurado,
                }
            )

    pagamentos_db = (
        db.query(Pagamento)
        .filter(Pagamento.id_aluno == id_matricula)
        .order_by(Pagamento.data_pagamento.desc())
        .all()
    )
    presencas_db = (
        db.query(Presenca)
        .filter(Presenca.id_aluno == id_matricula)
        .order_by(Presenca.data.desc())
        .all()
    )

    return {
        "aluno": {
            "nome": aluno.nome,
            "idade": idade,
            "data_nascimento": (
                aluno.data_nascimento.isoformat() if aluno.data_nascimento else ""
            ),
            "whatsapp": aluno.whatsapp,
            "email": aluno.email,
            "endereco": aluno.endereco,
            "nacionalidade": aluno.nacionalidade,
            "naturalidade": aluno.naturalidade,
            "nome_pai": aluno.nome_pai,
            "nome_mae": aluno.nome_mae,
            "contato_emergencia_nome": aluno.contato_emergencia_nome,
            "contato_emergencia_parentesco": aluno.contato_emergencia_parentesco,
            "contato_emergencia_telefone": aluno.contato_emergencia_telefone,
            "historico_marcial": aluno.historico_marcial,
            "equipamento_proprio": aluno.equipamento_proprio,
            "termo_risco_assinado": aluno.termo_risco_assinado,
            "restricao_medica": aluno.restricao_medica,
            "autorizacao_imagem": aluno.autorizacao_imagem,
            "status_atividade": aluno.status_atividade,
            "diario_pedagogico": aluno.diario_pedagogico,
            "modelo_plano": contrato.modelo_plano if contrato else "Horas Livres",
            "valor_base": contrato.valor_base if contrato else 0.0,
            "valor_contratual_fixo": (
                contrato.valor_contratual_fixo if contrato else 0.0
            ),
            "taxa_admissao_pendente": contrato.taxa_admissao_saldo if contrato else 0.0,
            "observacao_financeira": contrato.observacao_financeira if contrato else "",
            "inclui_shokubai": contrato.inclui_shokubai if contrato else False,
            "graduacao_atual": aluno.graduacao_atual,
            "total_horas_treinadas": formata_hora(total_horas),
            "meses_na_graduacao": meses_na_grad,
            "meta_meses": meta_meses,
            "progresso_percentual": prog_pct,
            "apto_exame": apto,
            "meses_faltantes": meses_faltantes,
            "modo_treino": aluno.modo_treino,
            "dia_vencimento": contrato.dia_vencimento if contrato else 10,
            "atraso_critico": atraso_critico,
            "acordo_contratual": (
                aluno.acordo_contratual if aluno.acordo_contratual else ""
            ),
            "hora_flexivel": aluno.hora_flexivel,
        },
        "historico_pagamentos": historico,
        "painel_pendencias": painel_pendencias,
        "extrato_recebimentos": [
            {
                "data": p.data_pagamento.strftime("%d/%m/%Y %H:%M"),
                "valor": p.valor,
                "metodo": p.metodo,
            }
            for p in pagamentos_db
        ],
        "historico_presencas": [
            {"data": p.data.strftime("%d/%m/%Y"), "status": p.status}
            for p in presencas_db
        ],
    }


@router.put(
    "/alunos/{id_matricula}/promover",
    summary="Promover graduação do aluno",
    description=(
        "Registra a nova graduação e reinicia a contagem de tempo de faixa "
        "(atualiza `data_ultima_graduacao` para hoje)."
    ),
)
def promover_aluno(
    id_matricula: str, req: PromoverRequest, db: Session = Depends(get_db)
):
    aluno = db.query(Aluno).filter(Aluno.id_matricula == id_matricula).first()
    aluno.graduacao_atual = req.nova_graduacao
    aluno.data_ultima_graduacao = date.today()
    db.commit()
    return {"status": "promovido"}


@router.put(
    "/alunos/{id_matricula}/status",
    summary="Alterar status de atividade do aluno",
    description=(
        "Define o status manualmente. Ao mudar para `Trancado` ou `Inativo`, "
        "encerra imediatamente uma eventual sessão de tatame aberta."
    ),
)
def alterar_status(
    id_matricula: str,
    req: StatusRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    aluno = db.query(Aluno).filter(Aluno.id_matricula == id_matricula).first()
    aluno.status_atividade = req.novo_status
    if req.novo_status in ["Trancado", "Inativo"]:
        encerrar_sessao_aberta(db, id_matricula)
    auditoria.registrar(
        db,
        acao="alterar_status",
        autor=usuario.username,
        id_aluno=id_matricula,
        descricao=f"Status alterado para {req.novo_status}.",
    )
    db.commit()
    return {"status": "Atualizado"}


@router.put(
    "/alunos/{id_matricula}/desativar",
    summary="Desativar aluno (soft delete)",
    description=(
        "**Soft delete**: marca o aluno como `Inativo` e encerra eventual "
        "sessão aberta. O registro **nunca** é removido do banco — o histórico "
        "é preservado. Retorna **404** se o aluno não existir."
    ),
)
def desativar_aluno(
    id_matricula: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Soft Delete: marca o aluno como `Inativo`, encerrando eventual sessão
    aberta. Nunca remove o registro do banco (preserva histórico)."""
    aluno = db.query(Aluno).filter(Aluno.id_matricula == id_matricula).first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    aluno.status_atividade = "Inativo"
    encerrar_sessao_aberta(
        db, id_matricula, nota="[SISTEMA] Cronômetro cortado pela desativação."
    )
    auditoria.registrar(
        db,
        acao="desativar_aluno",
        autor=usuario.username,
        id_aluno=id_matricula,
        descricao="Aluno suspenso (soft delete).",
    )
    db.commit()
    return {"status": "Aluno desativado"}


@router.put(
    "/alunos/{id_matricula}/nota-financeira",
    summary="Atualizar observação financeira do contrato",
    description=(
        "Salva a observação financeira livre. Marcadores especiais têm efeito "
        "na trava: `[ACORDO]` faz bypass; `[TRAVA AUTOMÁTICA]` é gerido pelo "
        "sistema."
    ),
)
def atualizar_nota(
    id_matricula: str, req: UpdateNotaRequest, db: Session = Depends(get_db)
):
    db.query(Contrato).filter(
        Contrato.id_aluno == id_matricula
    ).first().observacao_financeira = req.nota
    db.commit()
    return {"status": "Nota salva"}


@router.put(
    "/alunos/{id_matricula}/diario-pedagogico",
    summary="Atualizar diário pedagógico do aluno",
    description="Salva o diário pedagógico (anotações de evolução do aluno).",
)
def atualizar_diario(
    id_matricula: str, req: UpdateNotaRequest, db: Session = Depends(get_db)
):
    db.query(Aluno).filter(
        Aluno.id_matricula == id_matricula
    ).first().diario_pedagogico = req.nota
    db.commit()
    return {"status": "Diário updated"}


@router.put(
    "/alunos/{id_matricula}/hora-flexivel",
    summary="Alternar cobrança por hora flexível",
    description=(
        "Liga/desliga o modo **hora flexível**. Quando ativo, o custo da "
        "sessão passa a ser `horas × valor_base`, ignorando a franquia da "
        "Mensalidade e o acréscimo do Intensivão."
    ),
)
def toggle_hora_flexivel(id_matricula: str, db: Session = Depends(get_db)):
    aluno = db.query(Aluno).filter(Aluno.id_matricula == id_matricula).first()
    aluno.hora_flexivel = not aluno.hora_flexivel
    db.commit()
    return {"status": "Atualizado"}

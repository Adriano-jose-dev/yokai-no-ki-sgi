"""
Funções utilitárias compartilhadas entre rotas — SGI-YKR.

- `formata_hora`: converte horas decimais em "HH:MM:SS".
- `encerrar_sessao_aberta`: encerra a sessão de tatame aberta de um aluno.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from models import Sessao


def formata_hora(h_dec: float) -> str:
    h = int(h_dec)
    m = int((h_dec - h) * 60)
    s = int((((h_dec - h) * 60) - m) * 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def encerrar_sessao_aberta(
    db: Session,
    id_matricula: str,
    nota: str = "[SISTEMA] Cronômetro cortado pelo status.",
) -> bool:
    """Encerra uma sessão de tatame aberta do aluno, se houver.

    Reutilizado por `alterar_status` e `desativar_aluno` para garantir que um
    aluno trancado/inativado não fique com sessão pendurada. Não faz commit.
    Retorna `True` se uma sessão foi encerrada.
    """
    sessao_aberta = (
        db.query(Sessao)
        .filter(Sessao.id_aluno == id_matricula, Sessao.hora_saida == None)  # noqa: E711
        .first()
    )
    if sessao_aberta:
        sessao_aberta.hora_saida = datetime.now()
        sessao_aberta.diario_sensei = nota
        return True
    return False

"""
Script de correção de dados legados — SGI-YKR (Tarefa 2.3 / Requisito 1.5).

Contratos antigos foram criados com `horas_franquia = 4`, divergindo da regra de
negócio do steering (franquia da Mensalidade é de 3 horas). Este script varre o
banco e corrige todos os contratos com `horas_franquia = 4` para `3`.

Uso (na pasta YnkBD/, com o venv ativo):

    python fix_horas_franquia.py

É idempotente: rodar de novo não muda nada se já estiver corrigido.

Na Fase A esta correção será formalizada como uma migration do Alembic
(Requisito 9.3); este script é a versão da Fase B para o banco SQLite atual.
"""

from main import SessionLocal, Contrato


def corrigir_franquia_legada() -> int:
    """Atualiza contratos com horas_franquia == 4 para 3. Retorna quantos foram
    alterados."""
    db = SessionLocal()
    try:
        contratos_legados = (
            db.query(Contrato).filter(Contrato.horas_franquia == 4).all()
        )
        total = len(contratos_legados)
        for contrato in contratos_legados:
            contrato.horas_franquia = 3
        db.commit()
        return total
    finally:
        db.close()


if __name__ == "__main__":
    alterados = corrigir_franquia_legada()
    print(f"Contratos corrigidos (horas_franquia 4 -> 3): {alterados}")

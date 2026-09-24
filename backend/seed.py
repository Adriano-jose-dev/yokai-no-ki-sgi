from main import SessionLocal, Aluno, Contrato
from datetime import date

# Lista legada fornecida pela PO
alunos_legados = [
    {"id": "YKRSSB2302001", "nome": "Matheus P.", "data": date(2023, 2, 1)},
    {"id": "YKRSSB2308002", "nome": "Alan h.", "data": date(2023, 8, 1)},
    {"id": "YKRSSB2604003", "nome": "Emmanuel G.", "data": date(2026, 4, 1)},
    {"id": "YKRSSB2606004", "nome": "Lucas h.", "data": date(2026, 6, 1)},
]

def popular_banco():
    db = SessionLocal()
    
    try:
        for dados in alunos_legados:
            # Verifica se o aluno já existe para não duplicar
            existe = db.query(Aluno).filter(Aluno.id_matricula == dados["id"]).first()
            if not existe:
                # 1. Cria o Aluno com o ID legado e a data retroativa
                novo_aluno = Aluno(
                    id_matricula=dados["id"], 
                    nome=dados["nome"], 
                    data_inicio=dados["data"]
                )
                db.add(novo_aluno)
                
                # 2. Cria o Contrato padrão associado a ele
                novo_contrato = Contrato(
                    id_aluno=dados["id"], 
                    valor_base=20.00, # Valor fictício, você pode alterar depois
                    taxa_admissao_saldo=50.00
                )
                db.add(novo_contrato)
                
                print(f"✅ Aluno {dados['nome']} ({dados['id']}) migrado com sucesso!")
            else:
                print(f"⚠️ Aluno {dados['nome']} já estava no banco.")
                
        db.commit()
        print("\n🎉 Carga inicial finalizada!")
        
    except Exception as e:
        db.rollback()
        print(f"Erro durante a migração: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    popular_banco()
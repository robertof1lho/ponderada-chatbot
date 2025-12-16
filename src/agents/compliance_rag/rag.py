import os
import chromadb
from sentence_transformers import SentenceTransformer

# CONFIGURAÇÃO 
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../../"))
db_path = os.path.join(project_root, "chroma_db")

def buscar_resposta(pergunta):
    
    print(f"PERGUNTA: {pergunta}")
    
    # 1. Conectar ao Banco
    try:
        client = chromadb.PersistentClient(path=db_path)
        collection = client.get_collection(name="regras_compliance")
    except Exception as e:
        print(f"Erro ao conectar: {e}")
        return

    # 2. Gerar Embedding
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embedding = model.encode([pergunta]).tolist()

    # 3. Buscar
    resultados = collection.query(
        query_embeddings=embedding,
        n_results=3  # Traz os top 3 trechos
    )

    # 4. Exibir Resultados Limpos
    documentos = resultados['documents'][0]
    
    if not documentos:
        print("Nenhum trecho relevante encontrado.")
    else:
        print(f"Encontrei {len(documentos)} trechos relevantes:\n")
        for i, doc in enumerate(documentos):
            print(f"Trecho {i+1}:")
            print(f"{doc.strip()}") # .strip() remove espaços extras
            print("\n")

if __name__ == "__main__":

    buscar_resposta("Quais são as regras sobre presentes e brindes?")
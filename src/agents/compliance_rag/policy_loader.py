import os
import chromadb
from sentence_transformers import SentenceTransformer
# Importando a ferramenta de corte inteligente
from langchain_text_splitters import RecursiveCharacterTextSplitter

current_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(current_dir, "chroma_db")

project_root = os.path.abspath(os.path.join(current_dir, "../../../"))
file_path = os.path.join(project_root, "assets", "politica_compliance.txt")

def carregar_dados():
    print("INICIANDO O PROCESSO")
    
    # 1. Verifica se o arquivo existe
    if not os.path.exists(file_path):
        print(f"ERRO: Arquivo não encontrado em: {file_path}")
        return

    # 2. Ler o arquivo de texto
    print(f"Lendo arquivo: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        texto_completo = f.read()

    # 3. Quebrar o texto em pedaços (Chunking OTIMIZADO)
    print("Dividindo o texto inteligentemente...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,      # Pedaços maiores (pega mais contexto)
        chunk_overlap=200,    # Sobreposição (repete 200 chars para não perder o fio da meada)
        separators=["\n\n", "\n", ".", " ", ""] # Tenta quebrar primeiro em parágrafos, depois frases
    )
    chunks = text_splitter.split_text(texto_completo)
    
    print(f"Texto dividido em {len(chunks)} pedaços robustos.")

    # 4. Inicializar Modelo e Banco de Dados
    print("Carregando modelo e banco de dados...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    client = chromadb.PersistentClient(path=db_path)

    try:
        client.delete_collection(name="regras_compliance")
        print("Coleção antiga apagada para atualização.")
    except:
        pass

    collection = client.create_collection(name="regras_compliance")

    # 5. Gerar Embeddings e Salvar
    print("Gerando matemática e salvando...")
    
    ids = [f"id_{i}" for i in range(len(chunks))]
    embeddings = model.encode(chunks).tolist()

    collection.add(
        documents=chunks,
        embeddings=embeddings,
        ids=ids
    )

    print(f"SUCESSO! {len(chunks)} documentos salvos em {db_path}")

if __name__ == "__main__":
    carregar_dados()
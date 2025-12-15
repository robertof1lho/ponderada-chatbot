import os
import chromadb
from sentence_transformers import SentenceTransformer
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    print("ERRO: Chave da API não encontrada! Verifique seu arquivo .env")
    exit()

NOME_BOT = "Dunder Bot"
CARGO_BOT = "Assistente de Compliance da Dunder Mifflin"

current_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(current_dir, "chroma_db")

print("Ligando o servidor na mesa do Dwight... (Aguarde)")

try:
    # 1. Conecta no Banco de Dados
    client_db = chromadb.PersistentClient(path=db_path)
    collection = client_db.get_collection(name="regras_compliance")
    
    # 2. Carrega o modelo de tradução (Texto -> Números)
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # 3. Conecta na Inteligência Artificial
    client_groq = Groq(api_key=GROQ_API_KEY)
    
    print("Sistema Online! Cuidado com o que você pergunta.\n")
    
except Exception as e:
    print(f"ERRO: Não consegui carregar os arquivos.")
    print(f"Detalhe do erro: {e}")
    print("Dica: Verifique se a pasta 'chroma_db' existe e se o 'policy_loader.py' foi rodado.")
    exit()

def processar_pergunta(pergunta):
    # 1. Busca no Banco
    embedding = model.encode([pergunta]).tolist()
    resultados = collection.query(query_embeddings=embedding, n_results=8)

    trechos = resultados['documents'][0]
    
    # Se o banco não achar nada, avisa
    if not trechos:
        return "Olha, revirei os arquivos e não encontrei nada sobre isso nas políticas da empresa. Deve ser coisa do Jim."

    contexto = "\n\n".join(trechos)
    
    # 2. Pergunta para a IA
    prompt_sistema = f"""
    Você é o {NOME_BOT}, o {CARGO_BOT} da Dunder Mifflin.
    
    SUA PERSONALIDADE:
    - Você é intenso, leal à empresa e odeia desperdício de tempo.
    - Você tem um senso de humor seco e sarcástico.
    - Seja breve. Não divague ou enrole. 
    - Sempre adicione uma frase sarcástica ou engraçada no final da resposta.
    - Seja útil, mas faça o usuário sentir que ele deveria saber a regra.
    
    SUAS INSTRUÇÕES:
    1. Responda a dúvida baseada ESTRITAMENTE no contexto: {contexto}
    2. Se a pergunta for idiota, diga que é idiota.
    3. Responda em Português.

    Exemplo de tom desejado:
    "É proibido. O reembolso só ocorre com nota fiscal. Se tentar enganar o sistema, você será demitido."
    """

    prompt_usuario = f"""
    Contexto: {contexto}
    Pergunta: {pergunta}
    """

    try:
        chat_completion = client_groq.chat.completions.create(
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": prompt_usuario}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Falha no sistema. O computador pegou fogo? {e}"

if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')

    print(f"👓 {NOME_BOT.upper()} ONLINE 👓")

    print(f"\n🤖 {NOME_BOT}: Saudações, cidadão!")
    print(f"   Eu sou o {NOME_BOT}, {CARGO_BOT}.")
    print("   Eu conheço todas as regras deste escritório. Teste-me.")
    print("   (Ou digite 'sair' para voltar ao trabalho, que é o que você deveria estar fazendo.)\n")
    print("-" * 60)


    while True:
        # O input faz o terminal PAUSAR e esperar você digitar
        pergunta = input("Você: ")
        
        # Comando para fechar
        if pergunta.lower() in ['sair', 'exit', 'tchau']:
            print(f"\n{NOME_BOT}: Finalmente. Vá produzir papel!\n")
            break
        
        # Pula linha vazia
        if not pergunta.strip():
            continue
            
        print("\n🤖 Dunder pensando...", end="\r") 
        
        resposta = processar_pergunta(pergunta)
        
        print(f"\n🤖 {NOME_BOT}: {resposta}\n")
        print("-" * 60)
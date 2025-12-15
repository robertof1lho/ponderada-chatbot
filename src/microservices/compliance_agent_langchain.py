import os
from typing import List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from utils.config import Config
from .compliance_tools_langchain import ComplianceToolsLangChain

class ComplianceAgentLangChain:
    def __init__(self):
        Config.validate()
        
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            google_api_key=Config.GOOGLE_API_KEY,
            temperature=0.1,
            convert_system_message_to_human=True
        )
        
        self.tools_instance = ComplianceToolsLangChain()
        self.chat_history = []
    
    def _get_available_commands(self) -> str:
        """Retorna lista de comandos disponíveis"""
        return """
        Comandos disponíveis:
        1. Verificar aprovação: "Verifique a aprovacao da transacao TX_XXXX"
        2. Detectar fraudes: "Detecte fraudes combinadas" ou "Detecte fraudes via email"
        3. Validar refeição: "Valide a refeicao da transacao TX_XXXX"  
        4. Obter contexto: "Analise o contexto da transacao TX_XXXX"
        """
    
    def query(self, question: str) -> str:
        """
        Processa uma pergunta do usuario de forma simplificada.
        Identifica qual tool usar baseado nas palavras-chave.
        
        Args:
            question: Pergunta do usuario
        
        Returns:
            Resposta do agente
        """
        try:
            question_lower = question.lower()
            
            # Identifica qual ferramenta usar baseado em palavras-chave
            if "aprovacao" in question_lower or "aprovar" in question_lower:
                # Extrai ID da transação
                import re
                tx_id_match = re.search(r'TX_\d+', question, re.IGNORECASE)
                if tx_id_match:
                    tx_id = tx_id_match.group()
                    result = self.tools_instance.audit_transaction_approval(tx_id)
                    self.chat_history.append(f"User: {question}")
                    self.chat_history.append(f"Agent: {result}")
                    return result
                else:
                    return "Por favor, especifique o ID da transacao (ex: TX_1296)"
            
            elif ("fraude" in question_lower or "fraud" in question_lower) and ("combinada" in question_lower or "email" in question_lower or "empresa" in question_lower):
                # Detecta fraudes via email
                result = self.tools_instance.detect_email_based_fraud("")
                self.chat_history.append(f"User: {question}")
                self.chat_history.append(f"Agent: {result}")
                return result
            
            elif "refeicao" in question_lower or "meal" in question_lower:
                # Valida refeição
                import re
                tx_id_match = re.search(r'TX_\d+', question, re.IGNORECASE)
                if tx_id_match:
                    tx_id = tx_id_match.group()
                    result = self.tools_instance.validate_business_meal(tx_id)
                    self.chat_history.append(f"User: {question}")
                    self.chat_history.append(f"Agent: {result}")
                    return result
                else:
                    return "Por favor, especifique o ID da transacao (ex: TX_1006)"
            
            elif "contexto" in question_lower or "context" in question_lower:
                # Obtém contexto
                import re
                tx_id_match = re.search(r'TX_\d+', question, re.IGNORECASE)
                if tx_id_match:
                    tx_id = tx_id_match.group()
                    result = self.tools_instance.get_transaction_context(tx_id)
                    self.chat_history.append(f"User: {question}")
                    self.chat_history.append(f"Agent: {result}")
                    return result
                else:
                    return "Por favor, especifique o ID da transacao"
            
            else:
                # Resposta genérica usando LLM
                prompt = ChatPromptTemplate.from_messages([
                    ("system", """Voce e um agente de auditoria de compliance da Dunder Mifflin.
                    Voce pode ajudar com:
                    1. Verificar aprovacao de transacoes (use: "Verifique a aprovacao da transacao TX_XXXX")
                    2. Detectar fraudes via email (use: "Detecte fraudes combinadas")
                    3. Validar refeicoes corporativas (use: "Valide a refeicao da transacao TX_XXXX")
                    4. Obter contexto de transacoes (use: "Analise o contexto da transacao TX_XXXX")
                    """),
                    ("human", "{input}")
                ])
                
                chain = prompt | self.llm
                response = chain.invoke({"input": question})
                result = response.content
                
                self.chat_history.append(f"User: {question}")
                self.chat_history.append(f"Agent: {result}")
                return result
                
        except Exception as e:
            return f"Erro ao processar pergunta: {str(e)}"
    
    def get_conversation_history(self) -> List[str]:
        """
        Retorna historico da conversa.
        
        Returns:
            Lista de mensagens do historico
        """
        return self.chat_history

def main():
    """
    Funcao principal para execucao do agente via linha de comando.
    """
    print("=" * 70)
    print("AGENTE DE AUDITORIA - DUNDER MIFFLIN (LangChain + Gemini)")
    print("=" * 70)
    print("\nComandos exemplo:")
    print("  - Verifique a aprovacao da transacao TX_1296")
    print("  - Detecte fraudes combinadas na empresa")
    print("  - Valide a refeicao da transacao TX_1006")
    print("  - Analise o contexto da transacao TX_1094")
    print("  - Sair")
    print("\n" + "=" * 70)
    
    agent = ComplianceAgentLangChain()
    
    while True:
        try:
            user_input = input("\nToby: ").strip()
            
            if user_input.lower() in ['sair', 'exit', 'quit', 'q']:
                print("\nEncerrando agente de auditoria. Boa sorte, Toby!")
                break
            
            if not user_input:
                continue
            
            print("\n" + "-" * 70)
            print("Agente:", end=" ")
            
            response = agent.query(user_input)
            print(response)
            print("-" * 70)
        
        except KeyboardInterrupt:
            print("\n\nAgente interrompido.")
            break
        except Exception as e:
            print(f"\nErro: {e}")

if __name__ == "__main__":
    main()
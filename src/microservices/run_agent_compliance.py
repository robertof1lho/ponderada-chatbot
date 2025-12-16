#!/usr/bin/env python3
"""
Script principal para executar o sistema completo de auditoria.
Execute este arquivo de dentro da pasta src/microservices.
"""

import sys
import os
from pathlib import Path

# Adiciona o diretorio src ao path (subindo 1 nivel)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def main():
    print("SISTEMA DE AUDITORIA DE COMPLIANCE - DUNDER MIFFLIN")
    print("=" * 70)
    print("\nEscolha uma opcao:")
    print("1. Executar auditoria CSV (Desafio 3.1)")
    print("2. Executar agente LangChain com Gemini (Desafio 3.2)")
    print("3. Sair")
    
    while True:
        try:
            choice = input("\nOpcao (1-3): ").strip()
            
            if choice == '1':
                print("\n" + "=" * 70)
                print("EXECUTANDO AUDITORIA CSV (DESAFIO 3.1)")
                print("=" * 70)
                
                from compliance_validator import executar_auditoria_final
                
                # Define o caminho do CSV (subindo 2 níveis: microservices -> src -> raiz)
                project_root = Path(__file__).parent.parent.parent
                csv_path = project_root / 'data' / 'transacoes_bancarias.csv'
                
                if not csv_path.exists():
                    print(f"\nERRO: Arquivo nao encontrado: {csv_path}")
                    print("Certifique-se de que o arquivo existe em data/transacoes_bancarias.csv")
                    continue
                
                resultado = executar_auditoria_final(str(csv_path))
                print(f"\n✅ Auditoria concluida! Total de violacoes: {len(resultado)}")
            
            
            elif choice == '2':
                print("\n" + "=" * 70)
                print("INICIANDO AGENTE LANGCHAIN + GEMINI (DESAFIO 3.2)")
                print("=" * 70)
                
                from compliance_agent_langchain import main as agent_main
                agent_main()
            
            elif choice == '3':
                print("\nSaindo do sistema. Ate mais!")
                break
            
            else:
                print("Opcao invalida. Escolha 1, 2 ou 3.")
        
        except KeyboardInterrupt:
            print("\n\nSistema interrompido.")
            break
        except Exception as e:
            print(f"\nErro: {e}")
            print("Certifique-se de que:")
            print("1. O arquivo .env existe com GOOGLE_API_KEY")
            print("2. Os arquivos de dados estao em data/")
            print("3. As dependencias estao instaladas (pip install -r requirements.txt)")

if __name__ == "__main__":
    main()
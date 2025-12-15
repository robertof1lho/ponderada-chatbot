import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict
import sys

# Importa os módulos de detecção
sys.path.append(str(Path(__file__).parent))
from compliance_validator import executar_auditoria_final
from contextual_fraud_detector import ContextualFraudDetector


class FraudOrchestrator:
    """Orquestra detecção de fraudes diretas + contextuais e gera relatório consolidado"""
    
    def __init__(self):
        self.detector_contextual = ContextualFraudDetector()
    
    def executar_auditoria_completa(
        self,
        caminho_csv: str,
        caminho_emails: str,
        usar_llm: bool = True
    ) -> Dict:
        """Pipeline completo de auditoria (3.1 + 3.2)"""
        
        print("=" * 80)
        print(" " * 20 + "AUDITORIA COMPLETA - DUNDER MIFFLIN")
        print("=" * 80)
        print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"CSV: {caminho_csv}")
        print(f"Emails: {caminho_emails}")
        print("=" * 80)
        
        # FASE 1: Violações diretas (CSV puro)
        print("\n" + "█" * 80)
        print("FASE 1: VIOLAÇÕES DIRETAS (apenas CSV)")
        print("█" * 80)
        
        df_violacoes_diretas = executar_auditoria_final(caminho_csv)
        
        # FASE 2: Fraudes contextuais (email + transação)
        print("\n" + "█" * 80)
        print("FASE 2: FRAUDES CONTEXTUAIS (email + transação)")
        print("█" * 80)
        
        df_fraudes_contextuais = self.detector_contextual.executar_deteccao_contextual(
            caminho_csv=caminho_csv,
            caminho_emails=caminho_emails,
            usar_llm=usar_llm,
            max_analises=50  # Limita a 50 análises para otimizar tempo
        )
        
        # CONSOLIDAÇÃO
        print("\n" + "=" * 80)
        print("CONSOLIDAÇÃO DE RESULTADOS")
        print("=" * 80)
        
        # Remove duplicatas (transações que aparecem em ambas as fases)
        ids_diretas = set(df_violacoes_diretas['id_transacao']) if not df_violacoes_diretas.empty else set()
        ids_contextuais = set(df_fraudes_contextuais['id_transacao']) if not df_fraudes_contextuais.empty else set()
        
        ids_duplicados = ids_diretas.intersection(ids_contextuais)
        
        if ids_duplicados:
            print(f"\n⚠ {len(ids_duplicados)} transações detectadas em ambas as fases")
            print("  (mantendo apenas a violação direta para evitar duplicidade)")
            
            # Remove duplicatas do df contextual
            df_fraudes_contextuais = df_fraudes_contextuais[
                ~df_fraudes_contextuais['id_transacao'].isin(ids_duplicados)
            ]
        
        # Estatísticas consolidadas
        total_violacoes = len(df_violacoes_diretas) + len(df_fraudes_contextuais)
        valor_total = (
            df_violacoes_diretas['valor'].sum() if not df_violacoes_diretas.empty else 0
        ) + (
            df_fraudes_contextuais['valor'].sum() if not df_fraudes_contextuais.empty else 0
        )
        
        print(f"\n📊 RESUMO EXECUTIVO:")
        print(f"  • Violações diretas: {len(df_violacoes_diretas)}")
        print(f"  • Fraudes contextuais: {len(df_fraudes_contextuais)}")
        print(f"  • TOTAL DE IRREGULARIDADES: {total_violacoes}")
        print(f"  • VALOR TOTAL ENVOLVIDO: US$ {valor_total:,.2f}")
        
        # Identifica funcionários mais problemáticos
        funcionarios_problematicos = {}
        
        if not df_violacoes_diretas.empty:
            for func, qtd in df_violacoes_diretas['funcionario'].value_counts().items():
                funcionarios_problematicos[func] = funcionarios_problematicos.get(func, 0) + qtd
        
        if not df_fraudes_contextuais.empty:
            for func, qtd in df_fraudes_contextuais['funcionario'].value_counts().items():
                funcionarios_problematicos[func] = funcionarios_problematicos.get(func, 0) + qtd
        
        if funcionarios_problematicos:
            print("\n🚨 TOP 5 FUNCIONÁRIOS COM MAIS IRREGULARIDADES:")
            for i, (func, qtd) in enumerate(
                sorted(funcionarios_problematicos.items(), key=lambda x: x[1], reverse=True)[:5], 
                1
            ):
                print(f"  {i}. {func}: {qtd} irregularidades")
        
        # Gerar relatório consolidado
        self._gerar_relatorio_final(
            df_violacoes_diretas,
            df_fraudes_contextuais,
            total_violacoes,
            valor_total,
            funcionarios_problematicos
        )
        
        return {
            'violacoes_diretas': df_violacoes_diretas,
            'fraudes_contextuais': df_fraudes_contextuais,
            'total_irregularidades': total_violacoes,
            'valor_total': valor_total,
            'funcionarios_problematicos': funcionarios_problematicos
        }
    
    def _gerar_relatorio_final(
        self,
        df_diretas: pd.DataFrame,
        df_contextuais: pd.DataFrame,
        total: int,
        valor_total: float,
        func_prob: Dict
    ):
        """Gera relatório consolidado em CSV e TXT"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 1. CSV consolidado
        arquivo_csv = f"relatorio_auditoria_completa_{timestamp}.csv"
        
        if not df_diretas.empty and not df_contextuais.empty:
            # Normaliza colunas para merge
            df_diretas_norm = df_diretas.copy()
            df_diretas_norm['origem'] = 'VIOLACAO_DIRETA'
            df_diretas_norm['tipo_fraude'] = df_diretas_norm.get('tipo', 'N/A')
            
            df_contextuais_norm = df_contextuais.copy()
            df_contextuais_norm['origem'] = 'FRAUDE_CONTEXTUAL'
            df_contextuais_norm['violacoes'] = df_contextuais_norm['tipo_fraude']
            
            # Merge
            df_consolidado = pd.concat([df_diretas_norm, df_contextuais_norm], ignore_index=True)
            
        elif not df_diretas.empty:
            df_consolidado = df_diretas.copy()
            df_consolidado['origem'] = 'VIOLACAO_DIRETA'
            
        elif not df_contextuais.empty:
            df_consolidado = df_contextuais.copy()
            df_consolidado['origem'] = 'FRAUDE_CONTEXTUAL'
        
        else:
            print("\n✓ Nenhuma irregularidade detectada - Nenhum relatório gerado")
            return
        
        df_consolidado.to_csv(arquivo_csv, index=False, encoding='utf-8-sig')
        
        # 2. Relatório executivo em TXT
        arquivo_txt = f"relatorio_executivo_{timestamp}.txt"
        
        with open(arquivo_txt, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("RELATÓRIO DE AUDITORIA - DUNDER MIFFLIN SCRANTON\n")
            f.write("=" * 80 + "\n")
            f.write(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Auditor: Toby Flenderson (RH)\n")
            f.write("=" * 80 + "\n\n")
            
            f.write("📊 RESUMO EXECUTIVO\n")
            f.write("-" * 80 + "\n")
            f.write(f"Total de irregularidades detectadas: {total}\n")
            f.write(f"Valor total envolvido: US$ {valor_total:,.2f}\n\n")
            
            f.write("🔍 DETALHAMENTO POR TIPO\n")
            f.write("-" * 80 + "\n")
            f.write(f"Violações diretas (CSV): {len(df_diretas)}\n")
            f.write(f"Fraudes contextuais (email + transação): {len(df_contextuais)}\n\n")
            
            if func_prob:
                f.write("🚨 FUNCIONÁRIOS COM MAIS IRREGULARIDADES\n")
                f.write("-" * 80 + "\n")
                for i, (func, qtd) in enumerate(
                    sorted(func_prob.items(), key=lambda x: x[1], reverse=True)[:10],
                    1
                ):
                    f.write(f"{i:2d}. {func:30s} - {qtd} irregularidades\n")
                f.write("\n")
            
            if not df_diretas.empty:
                f.write("📋 VIOLAÇÕES DIRETAS (Top 10)\n")
                f.write("-" * 80 + "\n")
                for _, row in df_diretas.sort_values('valor', ascending=False).head(10).iterrows():
                    f.write(f"\nID: {row['id_transacao']}\n")
                    f.write(f"Funcionário: {row['funcionario']} ({row['cargo']})\n")
                    f.write(f"Valor: US$ {row['valor']:,.2f}\n")
                    f.write(f"Descrição: {row['descricao']}\n")
                    f.write(f"Violação: {str(row['violacoes'])[:200]}...\n")
            
            if not df_contextuais.empty:
                f.write("\n\n🕵️ FRAUDES CONTEXTUAIS (Top 10)\n")
                f.write("-" * 80 + "\n")
                for _, row in df_contextuais.sort_values('valor', ascending=False).head(10).iterrows():
                    f.write(f"\nID: {row['id_transacao']}\n")
                    f.write(f"Funcionário: {row['funcionario']} ({row['cargo']})\n")
                    f.write(f"Valor: US$ {row['valor']:,.2f}\n")
                    f.write(f"Tipo de fraude: {row['tipo_fraude']}\n")
                    if 'confianca' in row:
                        f.write(f"Confiança: {row['confianca']}%\n")
                    if 'evidencia_email' in row:
                        f.write(f"Evidência: {str(row['evidencia_email'])[:200]}...\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("FIM DO RELATÓRIO\n")
            f.write("=" * 80 + "\n")
        
        print(f"\n✓ Relatórios gerados:")
        print(f"  • CSV consolidado: {arquivo_csv}")
        print(f"  • Relatório executivo: {arquivo_txt}")


def main():
    """Função principal para execução standalone"""
    from pathlib import Path
    
    # Paths
    project_root = Path(__file__).parent.parent.parent
    csv_path = project_root / 'data' / 'transacoes_bancarias.csv'
    emails_path = project_root / 'data' / 'emails.txt'
    
    # Verifica se arquivos existem
    if not csv_path.exists():
        print(f"❌ ERRO: Arquivo não encontrado: {csv_path}")
        return
    
    if not emails_path.exists():
        print(f"❌ ERRO: Arquivo não encontrado: {emails_path}")
        return
    
    # Executa auditoria completa
    orchestrator = FraudOrchestrator()
    
    resultado = orchestrator.executar_auditoria_completa(
        caminho_csv=str(csv_path),
        caminho_emails=str(emails_path),
        usar_llm=True  # Mude para False para desabilitar análise LLM
    )
    
    print("\n" + "=" * 80)
    print("✅ AUDITORIA COMPLETA - CONCLUÍDA COM SUCESSO")
    print("=" * 80)
    print(f"\nTotal de irregularidades: {resultado['total_irregularidades']}")
    print(f"Valor total: US$ {resultado['valor_total']:,.2f}")
    
    if resultado['funcionarios_problematicos']:
        func_top = max(resultado['funcionarios_problematicos'].items(), key=lambda x: x[1])
        print(f"\nFuncionário mais problemático: {func_top[0]} ({func_top[1]} irregularidades)")


if __name__ == "__main__":
    main()
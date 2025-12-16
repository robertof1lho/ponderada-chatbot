import pandas as pd
import re
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
import os
from dotenv import load_dotenv

load_dotenv()

class ContextualFraudDetector:
    """Detecta fraudes que precisam de contexto de emails para serem identificadas"""
    
    def __init__(self, model_name="llama-3.3-70b-versatile"):
        # Usa Groq em vez de Anthropic - com configuração para retornar JSON
        self.llm = ChatGroq(
            model=model_name,
            temperature=0,
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model_kwargs={
                "response_format": {"type": "json_object"}
            }
        )
        
        # Padrões de colusão conhecidos (baseado nos emails fornecidos)
        self.colusion_patterns = {
            'creed_kevin': ['creed', 'kevin'],
            'ryan_kelly': ['ryan', 'kelly'],
            'michael_dwight': ['michael', 'dwight'],
            'michael_jan': ['michael', 'jan']
        }
        
        # Palavras-chave que indicam fraude em emails
        self.fraud_keywords = [
            'lançar como', 'categorize como', 'mascarar', 'dividir',
            'abaixo de 50', 'angela nem olha', 'wallace nunca vai saber',
            'tech solutions', 'wcs supplies', 'cartão corporativo',
            'aprovar verbalmente', 'sem recibo', 'não conte para',
            'destruir evidências', 'deletar', 'operação fênix'
        ]
    
    def carregar_emails(self, caminho_arquivo: str) -> List[Dict]:
        """Parse do arquivo de emails em estrutura utilizável"""
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            conteudo = f.read()
        
        # Separa emails pelo delimitador
        blocos = conteudo.split('-------------------------------------------------------------------------------')
        emails = []
        
        for bloco in blocos:
            if not bloco.strip() or 'DUMP DE SERVIDOR' in bloco:
                continue
            
            email = {}
            linhas = bloco.strip().split('\n')
            
            for linha in linhas:
                if linha.startswith('De:'):
                    match = re.search(r'<(.+?)>', linha)
                    if match:
                        email['remetente'] = match.group(1)
                    else:
                        # Pega o nome se não tiver email
                        email['remetente'] = linha.split('De:')[1].strip()
                
                elif linha.startswith('Para:'):
                    match = re.search(r'<(.+?)>', linha)
                    if match:
                        email['destinatario'] = match.group(1)
                    else:
                        email['destinatario'] = linha.split('Para:')[1].strip()
                
                elif linha.startswith('Data:'):
                    data_str = linha.split('Data:')[1].strip()
                    try:
                        email['data'] = datetime.strptime(data_str, '%Y-%m-%d %H:%M')
                    except:
                        email['data'] = None
                
                elif linha.startswith('Assunto:'):
                    email['assunto'] = linha.split('Assunto:')[1].strip()
                
                elif linha.startswith('Mensagem:'):
                    idx = linhas.index(linha)
                    email['mensagem'] = '\n'.join(linhas[idx+1:])
                    break
            
            if 'remetente' in email and 'mensagem' in email:
                emails.append(email)
        
        return emails
    
    def extrair_valores_de_texto(self, texto: str) -> List[float]:
        """Extrai valores monetários mencionados no texto"""
        # Padrões: $5,000 ou US$ 5.000 ou 5000.00 ou $5k
        patterns = [
            r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # $5,000.00
            r'US\$\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)',  # US$ 5.000,00
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*d[oó]lar',  # 5000 dólares
            r'\$(\d+)k'  # $5k
        ]
        
        valores = []
        for pattern in patterns:
            matches = re.findall(pattern, texto.lower())
            for match in matches:
                try:
                    # Remove vírgulas e converte k para mil
                    valor_str = match.replace(',', '')
                    if 'k' in valor_str:
                        valores.append(float(valor_str.replace('k', '')) * 1000)
                    else:
                        valores.append(float(valor_str))
                except:
                    continue
        
        return valores
    
    def buscar_emails_suspeitos(self, emails: List[Dict]) -> List[Dict]:
        """Filtra emails que contêm indicadores de fraude"""
        emails_suspeitos = []
        
        for email in emails:
            texto_completo = f"{email.get('assunto', '')} {email.get('mensagem', '')}".lower()
            
            # Verifica palavras-chave de fraude
            keywords_encontradas = [kw for kw in self.fraud_keywords if kw in texto_completo]
            
            # Verifica padrões de colusão
            remetente = email.get('remetente', '').lower()
            destinatario = email.get('destinatario', '').lower()
            
            colusao_detectada = None
            for nome_dupla, membros in self.colusion_patterns.items():
                if any(m in remetente for m in membros) and any(m in destinatario for m in membros):
                    colusao_detectada = nome_dupla
                    break
            
            # Extrai valores mencionados
            valores_mencionados = self.extrair_valores_de_texto(texto_completo)
            
            if keywords_encontradas or colusao_detectada or valores_mencionados:
                email['keywords_fraude'] = keywords_encontradas
                email['colusao'] = colusao_detectada
                email['valores_mencionados'] = valores_mencionados
                email['score_suspeita'] = len(keywords_encontradas) + (2 if colusao_detectada else 0)
                emails_suspeitos.append(email)
        
        return sorted(emails_suspeitos, key=lambda x: x['score_suspeita'], reverse=True)
    
    def cruzar_email_com_transacoes(
        self, 
        email: Dict, 
        df_transacoes: pd.DataFrame,
        janela_dias: int = 7
    ) -> List[Tuple[Dict, pd.Series]]:
        """Cruza um email suspeito com transações próximas no tempo"""
        pares_suspeitos = []
        
        if email.get('data') is None:
            return pares_suspeitos
        
        # Filtra transações na janela de tempo
        data_inicio = email['data'] - timedelta(days=janela_dias)
        data_fim = email['data'] + timedelta(days=janela_dias)
        
        df_filtrado = df_transacoes[
            (df_transacoes['data'] >= data_inicio) & 
            (df_transacoes['data'] <= data_fim)
        ]
        
        # Extrai nomes de funcionários mencionados no email
        texto_email = f"{email.get('assunto', '')} {email.get('mensagem', '')}".lower()
        
        for _, transacao in df_filtrado.iterrows():
            score_match = 0
            razoes = []
            
            # 1. Funcionário mencionado no email?
            func_nome = transacao['funcionario'].lower()
            if any(parte in texto_email for parte in func_nome.split()):
                score_match += 3
                razoes.append('funcionario_mencionado')
            
            # 2. Remetente/destinatário é o autor da transação?
            if func_nome in email.get('remetente', '').lower() or \
               func_nome in email.get('destinatario', '').lower():
                score_match += 2
                razoes.append('autor_envolvido')
            
            # 3. Valor mencionado no email coincide?
            for valor_email in email.get('valores_mencionados', []):
                if abs(valor_email - transacao['valor']) < 1.0:  # tolerância de $1
                    score_match += 5
                    razoes.append(f'valor_exato:{valor_email}')
                    break
            
            # 4. Fornecedor mencionado no email?
            fornecedor = str(transacao.get('fornecedor', '')).lower()
            if fornecedor and fornecedor in texto_email:
                score_match += 4
                razoes.append('fornecedor_mencionado')
            
            # 5. Categoria/descrição mencionada?
            if any(palavra in texto_email for palavra in 
                   str(transacao['categoria']).lower().split()):
                score_match += 1
                razoes.append('categoria_mencionada')
            
            if score_match >= 3:  # Threshold mínimo
                pares_suspeitos.append((
                    email, 
                    transacao,
                    score_match,
                    razoes
                ))
        
        return pares_suspeitos
    
    def analisar_fraude_com_llm(
        self, 
        email: Dict, 
        transacao: pd.Series,
        razoes_cruzamento: List[str]
    ) -> Dict:
        """Usa LLM para análise contextual profunda"""
        
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""Você é um auditor especializado em detecção de fraudes corporativas.
Analise o email e a transação fornecidos e determine se há evidências de fraude.

Tipos de fraude a considerar:
1. COLUSÃO: Funcionários combinando desvios de verba
2. SMURFING: Divisão intencional de compras para evitar aprovação
3. CONFLITO DE INTERESSES: Uso de verba da empresa para negócios paralelos
4. MASCARAMENTO: Lançamento de despesas com descrições falsas
5. APROVAÇÃO FRAUDULENTA: Processar pagamentos sem autorização adequada

Responda APENAS no formato JSON:
{
    "is_fraud": true/false,
    "fraud_type": "tipo de fraude",
    "confidence": 0-100,
    "evidence": "evidência específica do email",
    "justification": "justificativa de 1-2 linhas"
}"""),
            HumanMessage(content=f"""EMAIL:
De: {email.get('remetente', 'N/A')}
Para: {email.get('destinatario', 'N/A')}
Data: {email.get('data', 'N/A')}
Assunto: {email.get('assunto', 'N/A')}
Mensagem: {email.get('mensagem', 'N/A')[:500]}...

TRANSAÇÃO:
ID: {transacao['id_transacao']}
Funcionário: {transacao['funcionario']}
Cargo: {transacao['cargo']}
Data: {transacao['data']}
Descrição: {transacao['descricao']}
Valor: US$ {transacao['valor']:.2f}
Categoria: {transacao['categoria']}

RAZÕES DO CRUZAMENTO: {', '.join(razoes_cruzamento)}

Analise se esta transação é fraudulenta baseado no contexto do email.""")
        ])
        
        try:
            response = self.llm.invoke(prompt.format_messages())
            
            # Limpa a resposta removendo markdown se houver
            content = response.content.strip()
            if content.startswith('```'):
                # Remove blocos de código markdown
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
                content = content.strip()
            
            # Parse do JSON retornado pelo LLM
            resultado = json.loads(content)
            
            return {
                'is_fraud': resultado.get('is_fraud', False),
                'fraud_type': resultado.get('fraud_type', 'DESCONHECIDO'),
                'confidence': resultado.get('confidence', 0),
                'evidence': resultado.get('evidence', ''),
                'justification': resultado.get('justification', ''),
                'email_id': f"{email.get('remetente', '')}_{email.get('data', '')}",
                'score_cruzamento': sum(razoes_cruzamento.count(r) for r in razoes_cruzamento)
            }
        
        except json.JSONDecodeError as e:
            print(f"Erro ao parsear JSON da resposta LLM: {e}")
            print(f"Conteúdo recebido: {response.content[:200] if response and response.content else 'Vazio'}")
            return {
                'is_fraud': False,
                'fraud_type': 'ERRO_JSON',
                'confidence': 0,
                'evidence': str(e),
                'justification': 'Erro ao parsear resposta do LLM',
                'email_id': '',
                'score_cruzamento': 0
            }
        except Exception as e:
            print(f"Erro na análise LLM: {e}")
            return {
                'is_fraud': False,
                'fraud_type': 'ERRO',
                'confidence': 0,
                'evidence': '',
                'justification': f'Erro na análise: {str(e)}',
                'email_id': '',
                'score_cruzamento': 0
            }
    
    def executar_deteccao_contextual(
        self, 
        caminho_csv: str,
        caminho_emails: str,
        usar_llm: bool = True,
        max_analises: int = 100
    ) -> pd.DataFrame:
        """Pipeline completo de detecção contextual
        
        Args:
            caminho_csv: Caminho para o CSV de transações
            caminho_emails: Caminho para o arquivo de emails
            usar_llm: Se deve usar LLM para análise detalhada
            max_analises: Número máximo de análises LLM (para evitar custos/timeouts)
        """
        
        print("=" * 70)
        print("DETECÇÃO DE FRAUDES CONTEXTUAIS (3.2)")
        print("=" * 70)
        
        # 1. Carregar dados
        print("\n[1/5] Carregando transações...")
        df_transacoes = pd.read_csv(caminho_csv)
        df_transacoes['data'] = pd.to_datetime(df_transacoes['data'])
        df_transacoes['fornecedor'] = df_transacoes['descricao'].apply(
            lambda x: x.split(' - ')[0] if ' - ' in x else x
        )
        print(f"   ✓ {len(df_transacoes)} transações carregadas")
        
        print("\n[2/5] Carregando e parseando emails...")
        emails = self.carregar_emails(caminho_emails)
        print(f"   ✓ {len(emails)} emails parseados")
        
        # 2. Filtrar emails suspeitos
        print("\n[3/5] Identificando emails suspeitos...")
        emails_suspeitos = self.buscar_emails_suspeitos(emails)
        print(f"   ✓ {len(emails_suspeitos)} emails com indicadores de fraude")
        
        # 3. Cruzar com transações
        print("\n[4/5] Cruzando emails com transações...")
        todos_pares = []
        for email in emails_suspeitos:
            pares = self.cruzar_email_com_transacoes(email, df_transacoes)
            todos_pares.extend(pares)
        
        print(f"   ✓ {len(todos_pares)} pares (email + transação) identificados")
        
        # 4. Análise com LLM (se habilitado)
        fraudes_contextuais = []
        
        if usar_llm and todos_pares:
            # Ordena pares por score (maior primeiro) e limita quantidade
            todos_pares_ordenados = sorted(todos_pares, key=lambda x: x[2], reverse=True)
            pares_para_analisar = todos_pares_ordenados[:max_analises]
            
            print(f"\n[5/5] Analisando {len(pares_para_analisar)} pares com LLM (de {len(todos_pares)} total)...")
            print(f"   (Limitado a {max_analises} análises para otimizar tempo/custo)")
            
            import time
            erros_consecutivos = 0
            max_erros_consecutivos = 5
            
            for i, (email, transacao, score, razoes) in enumerate(pares_para_analisar):
                print(f"   Analisando par {i+1}/{len(pares_para_analisar)}... ", end='', flush=True)
                
                try:
                    analise = self.analisar_fraude_com_llm(email, transacao, razoes)
                    erros_consecutivos = 0  # Reset contador de erros
                    
                    if analise['is_fraud'] and analise['confidence'] > 50:
                        print(f"✓ FRAUDE (confiança: {analise['confidence']}%)")
                    else:
                        print(f"○ OK")
                    
                    # Pequena pausa entre chamadas para evitar rate limiting
                    time.sleep(0.1)
                    
                except Exception as e:
                    erros_consecutivos += 1
                    print(f"✗ ERRO: {str(e)[:50]}")
                    
                    if erros_consecutivos >= max_erros_consecutivos:
                        print(f"\n   ⚠ Muitos erros consecutivos. Abortando análise LLM.")
                        break
                    
                    analise = {
                        'is_fraud': False,
                        'fraud_type': 'ERRO_ANALISE',
                        'confidence': 0,
                        'evidence': str(e)[:100],
                        'justification': 'Erro na análise',
                        'email_id': '',
                        'score_cruzamento': 0
                    }
                
                # Só adiciona se LLM confirmar fraude com alta confiança
                if analise['is_fraud'] and analise['confidence'] >= 70:
                    fraudes_contextuais.append({
                        'id_transacao': transacao['id_transacao'],
                        'data': transacao['data'],
                        'funcionario': transacao['funcionario'],
                        'cargo': transacao['cargo'],
                        'descricao': transacao['descricao'],
                        'valor': transacao['valor'],
                        'categoria': transacao['categoria'],
                        'fornecedor': transacao.get('fornecedor', ''),
                        'tipo_fraude': analise['fraud_type'],
                        'confianca': analise['confidence'],
                        'evidencia_email': analise['evidence'][:200],
                        'justificativa': analise['justification'],
                        'email_remetente': email.get('remetente', ''),
                        'email_data': email.get('data', ''),
                        'score_cruzamento': score,
                        'tipo': 'FRAUDE CONTEXTUAL'
                    })
            
            print(f"\n   ✓ {len(fraudes_contextuais)} fraudes contextuais confirmadas")
        
        else:
            print("\n[5/5] Análise LLM desabilitada - retornando apenas cruzamentos")
            for email, transacao, score, razoes in todos_pares:
                fraudes_contextuais.append({
                    'id_transacao': transacao['id_transacao'],
                    'data': transacao['data'],
                    'funcionario': transacao['funcionario'],
                    'cargo': transacao['cargo'],
                    'descricao': transacao['descricao'],
                    'valor': transacao['valor'],
                    'categoria': transacao['categoria'],
                    'fornecedor': transacao.get('fornecedor', ''),
                    'tipo_fraude': 'CRUZAMENTO_SUSPEITO',
                    'confianca': score * 10,
                    'evidencia_email': ', '.join(razoes),
                    'justificativa': 'Email suspeito vinculado à transação',
                    'email_remetente': email.get('remetente', ''),
                    'email_data': email.get('data', ''),
                    'score_cruzamento': score,
                    'tipo': 'FRAUDE CONTEXTUAL'
                })
        
        df_fraudes = pd.DataFrame(fraudes_contextuais)
        
        # 5. Relatório
        print("\n" + "=" * 70)
        print("RESULTADOS - FRAUDES CONTEXTUAIS")
        print("=" * 70)
        
        if not df_fraudes.empty:
            print(f"\nFraudes contextuais detectadas: {len(df_fraudes)}")
            print(f"Valor total: US$ {df_fraudes['valor'].sum():,.2f}")
            
            print("\nTop 3 tipos de fraude:")
            for tipo, qtd in df_fraudes['tipo_fraude'].value_counts().head(3).items():
                df_tipo = df_fraudes[df_fraudes['tipo_fraude'] == tipo]
                print(f"  {tipo}: {qtd} casos (US$ {df_tipo['valor'].sum():,.2f})")
            
            print(f"\nTop 3 funcionários envolvidos:")
            for func, qtd in df_fraudes['funcionario'].value_counts().head(3).items():
                print(f"  {func}: {qtd} fraudes")
            
            # Salvar relatório
            arquivo_saida = f"fraudes_contextuais_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df_fraudes.to_csv(arquivo_saida, index=False, encoding='utf-8-sig')
            print(f"\nRelatório salvo: {arquivo_saida}")
            
            # Mostrar amostra
            print("\nAmostra (3 casos de maior valor):")
            for _, fraude in df_fraudes.sort_values('valor', ascending=False).head(3).iterrows():
                print(f"\n  ID: {fraude['id_transacao']} | {fraude['funcionario']}")
                print(f"  Valor: US$ {fraude['valor']:.2f}")
                print(f"  Tipo: {fraude['tipo_fraude']} (Confiança: {fraude['confianca']}%)")
                print(f"  Evidência: {fraude['evidencia_email'][:100]}...")
        
        else:
            print("\nNenhuma fraude contextual detectada.")
        
        return df_fraudes


if __name__ == "__main__":
    from pathlib import Path
    
    # Paths
    project_root = Path(__file__).parent.parent.parent
    csv_path = project_root / 'data' / 'transacoes_bancarias.csv'
    emails_path = project_root / 'data' / 'emails.txt'
    
    # Executar detecção
    detector = ContextualFraudDetector()
    resultado = detector.executar_deteccao_contextual(
        caminho_csv=str(csv_path),
        caminho_emails=str(emails_path),
        usar_llm=True  # Mude para False se quiser apenas cruzamentos sem LLM
    )
    
    print("\n" + "=" * 70)
    print("DETECÇÃO CONTEXTUAL - CONCLUÍDA")
    print("=" * 70)
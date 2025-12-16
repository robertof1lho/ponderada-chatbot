import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import json

from utils.email_parser import EmailParser
from utils.config import Config

class ComplianceToolsLangChain:
    def __init__(self):
        self.csv_path = Config.CSV_PATH
        self.email_path = Config.EMAIL_PATH
        
        self.df = pd.read_csv(self.csv_path)
        self.df['data'] = pd.to_datetime(self.df['data'])
        self.df['fornecedor'] = self.df['descricao'].apply(
            lambda x: x.split(' - ')[0] if ' - ' in x else x
        )
        
        self.email_parser = EmailParser(self.email_path)
    
    def audit_transaction_approval(self, transaction_id: str) -> str:
        """
        Verifica se uma transacao foi devidamente aprovada conforme as regras de alçada.
        
        Args:
            transaction_id: ID da transacao (ex: TX_1001)
        
        Returns:
            String com analise da aprovacao
        """
        transacao = self.df[self.df['id_transacao'] == transaction_id]
        
        if transacao.empty:
            return f"Transacao {transaction_id} nao encontrada."
        
        transacao = transacao.iloc[0]
        valor = float(transacao['valor'])
        funcionario = transacao['funcionario']
        data_str = transacao['data'].strftime('%Y-%m-%d')
        fornecedor = transacao['fornecedor']
        
        emails = self.email_parser.get_emails_by_transaction_context(
            funcionario, transacao['data'], fornecedor, valor
        )
        
        resultado = {
            'transaction_id': transaction_id,
            'funcionario': funcionario,
            'valor': valor,
            'data': data_str,
            'fornecedor': fornecedor,
            'categoria': transacao['categoria']
        }
        
        if valor <= 50:
            # Verifica emails suspeitos que mencionam burlar limites
            emails_suspeitos = []
            palavras_suspeitas = ['abaixo de 50', 'angela nem olha', 'não precisa de recibo', 
                                 'passa o cartão', 'apenas pague', 'nem olha']
            
            for email in emails:
                mensagem_lower = email.get('mensagem', '').lower()
                if any(palavra in mensagem_lower for palavra in palavras_suspeitas):
                    emails_suspeitos.append(email)
            
            if emails_suspeitos:
                resultado['status'] = 'SUSPEITA DE FRAUDE'
                resultado['detalhes'] = f'ALERTA: Valor estrategicamente abaixo de $50. Encontrados {len(emails_suspeitos)} emails com indicios de manipulacao do limite de aprovacao automatica.'
                resultado['fraude_detectada'] = 'COLUSION - Manipulacao intencional de valores para evitar aprovacao'
                resultado['emails_suspeitos'] = [
                    {
                        'de': e.get('de_nome', 'Desconhecido'),
                        'para': e.get('para_nome', 'Desconhecido'),
                        'trecho_suspeito': next((palavra for palavra in palavras_suspeitas if palavra in e.get('mensagem', '').lower()), '')
                    }
                    for e in emails_suspeitos[:2]  # Mostra até 2 exemplos
                ]
            else:
                resultado['status'] = 'APROVACAO AUTOMATICA'
                resultado['detalhes'] = 'Valor dentro da autonomia do funcionario (ate US$ 50)'
        
        elif valor <= 500:
            emails_aprovacao = [
                e for e in emails 
                if 'Michael Scott' in e['de_nome'] or 'Toby Flenderson' in e['de_nome']
            ]
            
            if emails_aprovacao:
                resultado['status'] = 'APROVADO'
                resultado['detalhes'] = f'Encontrados {len(emails_aprovacao)} emails de aprovacao'
                resultado['exemplo_email'] = emails_aprovacao[0]['assunto']
            else:
                resultado['status'] = 'NAO APROVADO'
                resultado['detalhes'] = 'Nenhum email de aprovacao encontrado para valor US$ 50-500'
        
        else:
            emails_cfo = [e for e in emails if 'David Wallace' in e['de_nome']]
            
            if emails_cfo:
                resultado['status'] = 'APROVADO PELO CFO'
                resultado['detalhes'] = f'PO do CFO encontrado em {len(emails_cfo)} emails'
                resultado['exemplo_email'] = emails_cfo[0]['assunto'] if emails_cfo else None
            else:
                resultado['status'] = 'NAO APROVADO'
                resultado['detalhes'] = 'Nenhum PO do CFO encontrado para valor acima de US$ 500'
        
        resultado['total_emails_relacionados'] = len(emails)
        
        return json.dumps(resultado, indent=2, ensure_ascii=False)
    
    def detect_email_based_fraud(self, transaction_id: Optional[str] = None) -> str:
        """
        Detecta fraudes combinadas via analise de emails.
        
        Args:
            transaction_id: ID especifico para analise, ou None para geral
        
        Returns:
            String com analise de fraudes
        """
        fraudes_detectadas = []
        
        if transaction_id:
            transacao = self.df[self.df['id_transacao'] == transaction_id]
            if not transacao.empty:
                fraudes_detectadas.extend(
                    self._analyze_single_transaction(transacao.iloc[0])
                )
        else:
            fraudes_detectadas.extend(self._analyze_wcs_supplies_fraud())
            fraudes_detectadas.extend(self._analyze_tech_solutions_fraud())
            fraudes_detectadas.extend(self._analyze_serenity_candles_fraud())
        
        if not fraudes_detectadas:
            return "Nenhuma fraude combinada detectada via analise de emails."
        
        resultado = {
            'total_fraudes_detectadas': len(fraudes_detectadas),
            'fraudes': fraudes_detectadas
        }
        
        return json.dumps(resultado, indent=2, ensure_ascii=False)
    
    def _analyze_single_transaction(self, transacao: pd.Series) -> List[Dict]:
        fraudes = []
        
        emails = self.email_parser.get_emails_by_transaction_context(
            transacao['funcionario'], transacao['data'], transacao['fornecedor'], transacao['valor']
        )
        
        for email in emails:
            if 'WCS Supplies' in email['mensagem'] and transacao['fornecedor'] == 'WCS Supplies':
                fraude = {
                    'tipo': 'FRAUDE_WCS_SUPPLIES',
                    'transacao_id': transacao['id_transacao'],
                    'valor': transacao['valor'],
                    'funcionario': transacao['funcionario'],
                    'evidencia_email': email['assunto'],
                    'data_email': email['data'].strftime('%Y-%m-%d')
                }
                fraudes.append(fraude)
            
            if 'Tech Solutions' in email['mensagem'] and 'Ryan' in email['de_nome']:
                fraude = {
                    'tipo': 'CONFLITO_INTERESSES_TECH_SOLUTIONS',
                    'transacao_id': transacao['id_transacao'],
                    'valor': transacao['valor'],
                    'funcionario': transacao['funcionario'],
                    'evidencia_email': email['assunto'],
                    'detalhes': 'Possivel desvio para WUPHF.com'
                }
                fraudes.append(fraude)
        
        return fraudes
    
    def _analyze_wcs_supplies_fraud(self) -> List[Dict]:
        fraudes = []
        
        emails_creed_kevin = self.email_parser.search_emails(
            from_name='Creed Bratton',
            to_name='Kevin Malone',
            keywords=['WCS', 'Supplies', 'qualidade', 'cola']
        )
        
        if emails_creed_kevin:
            transacoes_wcs = self.df[
                self.df['fornecedor'].str.contains('WCS', case=False, na=False)
            ]
            
            for _, tx in transacoes_wcs.iterrows():
                fraude = {
                    'tipo': 'FRAUDE_COMBINADA_WCS',
                    'transacao_id': tx['id_transacao'],
                    'valor': tx['valor'],
                    'funcionario': tx['funcionario'],
                    'fornecedor': tx['fornecedor'],
                    'evidencia_emails': len(emails_creed_kevin),
                    'exemplo_assunto': emails_creed_kevin[0]['assunto']
                }
                fraudes.append(fraude)
        
        return fraudes
    
    def _analyze_tech_solutions_fraud(self) -> List[Dict]:
        fraudes = []
        
        emails_ryan = self.email_parser.search_emails(
            from_name='Ryan Howard',
            keywords=['Tech Solutions', 'WUPHF', 'servidor', 'AWS']
        )
        
        if emails_ryan:
            transacoes_tech = self.df[
                self.df['fornecedor'].str.contains('Tech Solutions', case=False, na=False)
            ]
            
            for _, tx in transacoes_tech.iterrows():
                fraude = {
                    'tipo': 'CONFLITO_INTERESSES_TECH',
                    'transacao_id': tx['id_transacao'],
                    'valor': tx['valor'],
                    'funcionario': tx['funcionario'],
                    'evidencia_emails': len(emails_ryan),
                    'exemplo_assunto': emails_ryan[0]['assunto'],
                    'detalhes': 'Ryan Howard desviando verba para startup pessoal WUPHF'
                }
                fraudes.append(fraude)
        
        return fraudes
    
    def _analyze_serenity_candles_fraud(self) -> List[Dict]:
        fraudes = []
        
        emails_jan = self.email_parser.search_emails(
            from_name='Jan Levinson',
            keywords=['Serenity', 'vela', 'candle']
        )
        
        emails_michael_jan = self.email_parser.search_emails(
            from_name='Michael Scott',
            to_name='Jan Levinson',
            keywords=['vela', 'Serenity']
        )
        
        if emails_jan or emails_michael_jan:
            transacoes_velas = self.df[
                self.df['descricao'].str.contains('vela|serenity|candle', case=False, na=False)
            ]
            
            for _, tx in transacoes_velas.iterrows():
                fraude = {
                    'tipo': 'CONFLITO_INTERESSES_SERENITY',
                    'transacao_id': tx['id_transacao'],
                    'valor': tx['valor'],
                    'funcionario': tx['funcionario'],
                    'evidencia_emails': len(emails_jan) + len(emails_michael_jan),
                    'detalhes': 'Compra de velas da empresa de Jan Levinson (Serenity by Jan)'
                }
                fraudes.append(fraude)
        
        return fraudes
    
    def validate_business_meal(self, transaction_id: str) -> str:
        """
        Valida se uma refeicao corporativa teve objetivo legitimo de negocio.
        
        Args:
            transaction_id: ID da transacao
        
        Returns:
            String com validacao
        """
        transacao = self.df[self.df['id_transacao'] == transaction_id]
        
        if transacao.empty:
            return f"Transacao {transaction_id} nao encontrada."
        
        transacao = transacao.iloc[0]
        
        if 'Refeicao' not in transacao['categoria']:
            return f"Transacao {transaction_id} nao e uma refeicao corporativa."
        
        emails = self.email_parser.get_emails_by_transaction_context(
            transacao['funcionario'], transacao['data'], transacao['fornecedor'], transacao['valor']
        )
        
        emails_cliente = [
            e for e in emails 
            if any(keyword in e['mensagem'].lower() 
                  for keyword in ['cliente', 'negocio', 'reuniao', 'venda', 'contrato', 'proposta'])
        ]
        
        if emails_cliente:
            resultado = {
                'transaction_id': transaction_id,
                'status': 'VALIDO',
                'detalhes': f'Encontrados {len(emails_cliente)} emails relacionados a clientes/negocios',
                'exemplo_assunto': emails_cliente[0]['assunto'],
                'recomendacao': 'Refeicao parece ter objetivo legitimo de negocio'
            }
        else:
            resultado = {
                'transaction_id': transaction_id,
                'status': 'SUSPEITO',
                'detalhes': 'Nenhum email sobre clientes ou negocios encontrado proximo a data',
                'recomendacao': 'Investigar manualmente com o funcionario e RH'
            }
        
        return json.dumps(resultado, indent=2, ensure_ascii=False)
    
    def get_transaction_context(self, transaction_id: str) -> str:
        """
        Obtem contexto completo de uma transacao incluindo emails relacionados.
        
        Args:
            transaction_id: ID da transacao
        
        Returns:
            String com contexto completo
        """
        transacao = self.df[self.df['id_transacao'] == transaction_id]
        
        if transacao.empty:
            return f"Transacao {transaction_id} nao encontrada."
        
        transacao = transacao.iloc[0]
        
        emails = self.email_parser.get_emails_by_transaction_context(
            transacao['funcionario'], transacao['data'], transacao['fornecedor'], transacao['valor']
        )
        
        resultado = {
            'transacao': {
                'id': transacao['id_transacao'],
                'funcionario': transacao['funcionario'],
                'cargo': transacao['cargo'],
                'data': transacao['data'].strftime('%Y-%m-%d'),
                'descricao': transacao['descricao'],
                'valor': float(transacao['valor']),
                'categoria': transacao['categoria'],
                'fornecedor': transacao['fornecedor']
            },
            'emails_relacionados': len(emails),
            'emails': [
                {
                    'de': email['de_nome'],
                    'para': email['para_nome'],
                    'data': email['data'].strftime('%Y-%m-%d %H:%M'),
                    'assunto': email['assunto'],
                    'mensagem_resumo': email['mensagem'][:200] + '...'
                }
                for email in emails[:3]
            ]
        }
        
        return json.dumps(resultado, indent=2, ensure_ascii=False)
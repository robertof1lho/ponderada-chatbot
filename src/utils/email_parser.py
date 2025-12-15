import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple

class EmailParser:
    def __init__(self, email_file_path: str):
        self.email_file_path = email_file_path
        self.emails: List[Dict] = []
        self._parse_emails()
    
    def _parse_emails(self):
        with open(self.email_file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        email_sections = content.split('-------------------------------------------------------------------------------')
        
        for section in email_sections:
            if not section.strip() or 'DUMP DE SERVIDOR' in section:
                continue
            
            email_data = self._extract_email_data(section)
            if email_data:
                self.emails.append(email_data)
    
    def _extract_email_data(self, section: str) -> Optional[Dict]:
        patterns = {
            'de': r'De:\s*(.+)',
            'para': r'Para:\s*(.+)',
            'data': r'Data:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})',
            'assunto': r'Assunto:\s*(.+)',
            'mensagem': r'Mensagem:\s*(.+)'
        }
        
        matches = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, section, re.DOTALL)
            matches[key] = match.group(1).strip() if match else None
        
        if all(matches.values()):
            return {
                'de': matches['de'],
                'para': matches['para'],
                'data': datetime.strptime(matches['data'], '%Y-%m-%d %H:%M'),
                'assunto': matches['assunto'],
                'mensagem': matches['mensagem'],
                'de_nome': self._extract_name(matches['de']),
                'para_nome': self._extract_name(matches['para'])
            }
        return None
    
    def _extract_name(self, email_string: str) -> str:
        match = re.match(r'([^<]+)<', email_string)
        return match.group(1).strip() if match else email_string
    
    def search_emails(self, 
                     from_name: Optional[str] = None,
                     to_name: Optional[str] = None,
                     date_range: Optional[Tuple[datetime, datetime]] = None,
                     keywords: Optional[List[str]] = None) -> List[Dict]:
        
        results = self.emails
        
        if from_name:
            results = [e for e in results if from_name.lower() in e['de_nome'].lower()]
        
        if to_name:
            results = [e for e in results if to_name.lower() in e['para_nome'].lower()]
        
        if date_range:
            start, end = date_range
            results = [e for e in results if start <= e['data'] <= end]
        
        if keywords:
            filtered = []
            for email in results:
                email_text = f"{email['assunto']} {email['mensagem']}".lower()
                if any(keyword.lower() in email_text for keyword in keywords):
                    filtered.append(email)
            results = filtered
        
        return results
    
    def get_emails_by_transaction_context(self, 
                                         funcionario: str,
                                         data_transacao: datetime,
                                         fornecedor: str,
                                         valor: float) -> List[Dict]:
        
        data_inicio = data_transacao.replace(hour=0, minute=0, second=0)
        data_fim = data_transacao.replace(hour=23, minute=59, second=59)
        
        emails_encontrados = []
        
        emails_encontrados.extend(
            self.search_emails(
                from_name=funcionario,
                date_range=(data_inicio, data_fim)
            )
        )
        
        fornecedor_keywords = fornecedor.split()[:2]
        emails_encontrados.extend(
            self.search_emails(
                date_range=(data_inicio, data_fim),
                keywords=fornecedor_keywords
            )
        )
        
        if valor > 100:
            emails_encontrados.extend(
                self.search_emails(
                    keywords=[str(int(valor)), f"${int(valor)}"]
                )
            )
        
        emails_unicos = []
        vistos = set()
        for email in emails_encontrados:
            ident = f"{email['de']}_{email['assunto']}_{email['data'].timestamp()}"
            if ident not in vistos:
                vistos.add(ident)
                emails_unicos.append(email)
        
        return emails_unicos
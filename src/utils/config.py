import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    CSV_PATH = os.getenv('CSV_PATH', 'data/transacoes_bancarias.csv')
    EMAIL_PATH = os.getenv('EMAIL_PATH', 'data/emails.txt')
    POLICY_PATH = os.getenv('POLICY_PATH', 'data/politica_compliance.txt')
    
    @classmethod
    def validate(cls):
        if not cls.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY não encontrada no .env")
        return True
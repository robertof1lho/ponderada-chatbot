# Auditoria do Toby


## Vídeo de Demonstração e Explicação dos Algoritmos

Assista à demonstração do projeto e à explicação detalhada do projeto no vídeo abaixo:

[Link do vídeo de Demonstração e Explicação no Drive](https://drive.google.com/file/d/1vYURawdQV-0r-_sZBHGdTZweUDDNbihW/view?usp=sharing)

## Visão geral

Este projeto tem três frentes principais para apoiar a investigação do Toby Flenderson:

- **Chatbot de Compliance (RAG)**: um agente híbrido que indexa a `politica_compliance.txt` com embeddings e usa a API da Groq para responder dúvidas sobre regras, citando trechos relevantes.
- **Agente de auditoria com LangChain/Gemini**: um microserviço que combina ferramentas programáticas (planilha e parser de emails) com um LLM para validar aprovações, analisar contextos e detectar fraudes combinadas.
- **Pipeline de conspiração**: análise estatística + LLMs para examinar o dump `emails.txt` e indicar se Michael Scott trama contra Toby.

## Arquitetura dos agentes e ferramentas

1. **Compliance RAG** (`src/agents/compliance_rag`):
   - `policy_loader.py` chunka `politica_compliance.txt`, gera embeddings (SentenceTransformer) e popula um banco Chroma.
   - `compliance_agent.py` consulta o banco, adiciona contexto e chama a API da Groq (`llama-3.3-70b`) para responder com tom sarcástico.
2. **Microservices LangChain** (`src/microservices`):
   - `ComplianceToolsLangChain` encapsula regras da planilha `transacoes_bancarias.csv` e usa o `EmailParser` (`src/utils/email_parser.py`) para localizar provas contextuais nos emails.
   - `ComplianceAgentLangChain` expõe comandos (aprovação, fraudes, validação de refeições, contexto) e decide se usa ferramentas ou o LLM `Google Gemini`.
   - `compliance_validator.py` executa auditoria offline (violação direta, smurfing, categorias proibidas) para os casos que não dependem de contexto textual.
   - `run_agent_compliance.py` orquestra os três desafios via terminal em menu único.
3. **Pipeline de conspiração** (`src/conspiration`):
   - Usa pipelines Hugging Face (`sentiment`, `zero-shot`) para pontuar emails e agrupar clusters suspeitos.
   - `llm_agent.py` aciona o LLM NVIDIA (Llama 3.3) para narrativas por cluster.
   - `report_generator.py` sintetiza um relatório final e salva em `src/conspiration/output/final_report.txt`.

## Dados fornecidos

Os arquivos oficiais ficam em `data/`:

- `politica_compliance.txt`: regras base para o RAG.
- `transacoes_bancarias.csv`: extrato usado nas validações e na detecção de fraudes.
- `emails.txt`: dump analisado nos módulos de conspiração e nas ferramentas de contexto.
- `scores_cache.json`: cache das pontuações da análise de emails para acelerar execuções.

## Configuração de ambiente

Crie um `.env` na raiz com pelo menos:

```
GOOGLE_API_KEY=...
NVIDIA_API_KEY=...
GROQ_API_KEY=...
CSV_PATH=data/transacoes_bancarias.csv
EMAIL_PATH=data/emails.txt
POLICY_PATH=data/politica_compliance.txt
```

> As chaves nunca devem ir ao repositório (use gitignore) e cada componente falha com mensagem amigável se não encontrar a chave esperada.

## Como executar

### 1. Chatbot de regras (RAG)
```bash
python -m src.agents.compliance_rag.policy_loader
python -m src.agents.compliance_rag.compliance_agent
```
Este fluxo prepara a base de conhecimento e inicia o bot conversacional que responde dúvidas da política de compliance.

### 2. Auditoria e detecção de fraudes combinadas
```bash
python -m src.microservices.run_agent_compliance
```
Escolha a opção correspondente no menu (1 para auditoria CSV, 2 para o agente LangChain). O menu inclui exemplos de perguntas e encerra com `sair`.

### 3. Verificação de conspiração contra Toby

#### Instalação

```bash
python -m venv .venv
source .venv/bin/activate  # ou .venv\\Scripts\\activate no Windows
pip install -r requirements.txt
```

> Para os componentes da pasta `conspiration`, instale adicionalmente `transformers` e o modelo `nlptown/bert-base-multilingual-uncased-sentiment` (já referenciado via `transformers`).

```bash
python3 -m src.conspiration.main
```
Processa os emails, utiliza cache (`data/scores_cache.json`) e salva um relatório final em `src/conspiration/output/final_report.txt`.
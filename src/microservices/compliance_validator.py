import pandas as pd
from datetime import datetime

def carregar_dados(caminho_arquivo):
    """Carrega os dados do CSV e prepara colunas auxiliares"""
    df = pd.read_csv(caminho_arquivo)
    df['data'] = pd.to_datetime(df['data'])
    # extrai o nome do fornecedor da descricao (parte antes do " - ")
    df['fornecedor'] = df['descricao'].apply(lambda x: x.split(' - ')[0] if ' - ' in x else x)
    return df

def verificar_violacoes_individuais(transacao):
    """Verifica uma transacao individual contra regras validaveis apenas com CSV"""
    violacoes = []
    # converte tudo para minusculo para facilitar comparacoes
    descricao = str(transacao['descricao']).lower()
    fornecedor = str(transacao['fornecedor']).lower()
    categoria = str(transacao['categoria']).lower()
    
    # categoria diversos nao pode ter valor acima de $5
    if transacao['categoria'] == 'Diversos' and transacao['valor'] > 5.0:
        violacoes.append('Categoria "Diversos" com valor > US$ 5.00')
    
    # hooters e um local explicitamente proibido
    if 'hooters' in descricao:
        violacoes.append('Restaurante Hooters e proibido')
    
    # carros conversiveis sao proibidos (especialmente o chrysler sebring)
    if 'chrysler sebring' in descricao or 'convertible' in descricao:
        violacoes.append('Carro conversivel (Chrysler Sebring) proibido')
    
    # verifica itens da lista negra organizados por categoria
    palavras_proibidas = {
        'entretenimento_ilegal': ['magica', 'algema', 'corrente', 'fumaca em po', 'stripper', 
                                  'baralho marcado', 'kit de ilusionismo', 'houdini', 'escapismo', 'pombo treinado'],
        'armas_armadilhas': ['arma', 'armadilha', 'espada', 'katana', 'estrela ninja', 'nunchaku',
                            'spray de pimenta', 'camuflagem', 'vigilancia', 'binoculos noturnos',
                            'walkie talkie', 'detetive', 'seguranca tatica'],
        'conflito_interesses': ['wuphf', 'serenity', 'vela', 'beterraba', 'tech solutions', 
                               'wcs supplies', 'controle de qualidade de cola', 
                               'auditoria de textura de papel', 'dunder infinity', 'serenity by jan']
    }
    
    for grupo, palavras in palavras_proibidas.items():
        for palavra in palavras:
            if palavra in descricao:
                mensagem = 'CONFLITO DE INTERESSES: Negocio paralelo relacionado' if grupo == 'conflito_interesses' else f'Item proibido ({grupo})'
                violacoes.append(mensagem)
                break
    
    # refeicoes corporativas devem ser em locais pre-aprovados
    if 'refei' in categoria:
        locais_aprovados = ["chili's", "cugino's", "cooper's seafood", "poor richard's pub"]
        local_aprovado = any(local in fornecedor for local in locais_aprovados)
        
        # poor richard's pub so e permitido para almoco
        if local_aprovado and 'poor richard' in fornecedor:
            violacoes.append('Poor Richards Pub: Verificar se e almoco (apenas almoco permitido)')
        elif not local_aprovado:
            violacoes.append(f'Refeicao em local nao aprovado: {transacao["fornecedor"]}')
    
    return violacoes

def detectar_smurfing(df, janela_dias=3, limite_valor=500):
    """Detecta possivel smurfing (divisao de compras para burlar limites)"""
    df = df.sort_values(['funcionario', 'fornecedor', 'data'])
    casos_smurfing = []
    
    # agrupa transacoes por funcionario e fornecedor
    for (funcionario, fornecedor), grupo in df.groupby(['funcionario', 'fornecedor']):
        grupo = grupo.sort_values('data')
        i = 0
        
        while i < len(grupo):
            trans_inicial = grupo.iloc[i]
            ids_agrupados = [trans_inicial['id_transacao']]
            valor_total = trans_inicial['valor']
            
            # busca transacoes subsequentes dentro da janela de tempo
            j = i + 1
            while j < len(grupo) and (grupo.iloc[j]['data'] - trans_inicial['data']).days <= janela_dias:
                ids_agrupados.append(grupo.iloc[j]['id_transacao'])
                valor_total += grupo.iloc[j]['valor']
                j += 1
            
            # smurfing: multiplas compras pequenas que somadas excedem o limite
            if len(ids_agrupados) >= 2 and valor_total > limite_valor:
                trans_individuais = grupo[grupo['id_transacao'].isin(ids_agrupados)]
                
                # verifica se cada transacao individual e menor que 80% do limite
                if trans_individuais['valor'].max() < (limite_valor * 0.8):
                    motivo = f"SMURFING: {len(ids_agrupados)} transacoes com {fornecedor}"
                    casos_smurfing.extend([{'id_transacao': tx_id, 'motivo_smurfing': motivo} for tx_id in ids_agrupados])
            
            i = j
    
    return pd.DataFrame(casos_smurfing) if casos_smurfing else pd.DataFrame()

def executar_auditoria_final(caminho_csv):
    """Executa auditoria final com todas as correcoes"""
    print("=" * 70)
    print("AUDITORIA FINAL - COM TODAS AS CORRECOES")
    print("=" * 70)
    
    df = carregar_dados(caminho_csv)
    print(f"Transacoes carregadas: {len(df)}")
    
    # primeira passada: verifica violacoes individuais em cada transacao
    print("Verificando violacoes individuais...")
    violacoes_individuais = [
        {
            'id_transacao': row['id_transacao'],
            'data': row['data'],
            'funcionario': row['funcionario'],
            'cargo': row['cargo'],
            'descricao': row['descricao'],
            'valor': row['valor'],
            'categoria': row['categoria'],
            'fornecedor': row['fornecedor'],
            'violacoes': ' | '.join(motivos),
            'tipo': 'VIOLACAO DIRETA'
        }
        for idx, row in df.iterrows()
        if (motivos := verificar_violacoes_individuais(row))
    ]
    
    df_viol_ind = pd.DataFrame(violacoes_individuais)
    
    # segunda passada: busca padroes de smurfing
    print("Detectando padroes de smurfing...")
    df_smurfing = detectar_smurfing(df)
    
    todas_violacoes = df_viol_ind.copy()
    
    # mescla violacoes de smurfing com as violacoes individuais
    if not df_smurfing.empty:
        for _, smurf in df_smurfing.iterrows():
            transacao = df[df['id_transacao'] == smurf['id_transacao']]
            if transacao.empty:
                continue
                
            trans = transacao.iloc[0]
            
            # se a transacao ja tem outra violacao, adiciona o smurfing
            if smurf['id_transacao'] in todas_violacoes['id_transacao'].values:
                idx = todas_violacoes[todas_violacoes['id_transacao'] == smurf['id_transacao']].index[0]
                todas_violacoes.at[idx, 'violacoes'] += f" | {smurf['motivo_smurfing']}"
            else:
                # caso contrario, cria uma nova entrada de violacao
                nova_violacao = pd.DataFrame([{
                    'id_transacao': trans['id_transacao'],
                    'data': trans['data'],
                    'funcionario': trans['funcionario'],
                    'cargo': trans['cargo'],
                    'descricao': trans['descricao'],
                    'valor': trans['valor'],
                    'categoria': trans['categoria'],
                    'fornecedor': trans['fornecedor'],
                    'violacoes': smurf['motivo_smurfing'],
                    'tipo': 'SMURFING'
                }])
                todas_violacoes = pd.concat([todas_violacoes, nova_violacao], ignore_index=True)
    
    print("\n" + "=" * 70)
    print("RESULTADOS FINAIS")
    print("=" * 70)
    
    if not todas_violacoes.empty:
        print(f"Violacoes detectadas: {todas_violacoes['id_transacao'].nunique()} transacoes")
        print(f"Valor total em violacoes: US$ {todas_violacoes['valor'].sum():,.2f}")
        
        print("\nCategorias de violacao:")
        
        # classifica cada violacao em uma categoria para analise
        def classificar_violacao(viol):
            if 'CONFLITO' in viol:
                return 'CONFLITO'
            elif 'Diversos' in viol:
                return 'DIVERSOS'
            elif 'local nao aprovado' in viol.lower() or 'hooters' in viol.lower():
                return 'LOCAL PROIBIDO'
            elif 'SMURFING' in viol:
                return 'SMURFING'
            elif 'Item proibido' in viol:
                return 'ITEM PROIBIDO'
            return 'OUTRO'
        
        todas_violacoes['categoria_violacao'] = todas_violacoes['violacoes'].apply(classificar_violacao)
        
        for cat in ['CONFLITO', 'LOCAL PROIBIDO', 'DIVERSOS', 'SMURFING', 'ITEM PROIBIDO']:
            df_cat = todas_violacoes[todas_violacoes['categoria_violacao'] == cat]
            if not df_cat.empty:
                print(f"  {cat}: {len(df_cat)} transacoes (US$ {df_cat['valor'].sum():,.2f})")
        
        print(f"\nTop 3 funcionarios problematicos:")
        for func, qtd in todas_violacoes['funcionario'].value_counts().head(3).items():
            print(f"  {func}: {qtd} violacoes")
        
        arquivo_saida = f"auditoria_final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        todas_violacoes.to_csv(arquivo_saida, index=False, encoding='utf-8-sig')
        print(f"\nRelatorio salvo em: {arquivo_saida}")
        
        print(f"\nAmostra (5 maiores valores):")
        for _, viol in todas_violacoes.sort_values('valor', ascending=False).head(5).iterrows():
            print(f"  ID: {viol['id_transacao']} | {viol['funcionario']}")
            print(f"  Valor: US$ {viol['valor']:.2f} | Fornecedor: {viol['fornecedor']}")
            print(f"  Violacao: {viol['violacoes'].split(' | ')[0]}\n")
    
    else:
        print("\nNenhuma violacao detectada.")
    
    print("\n" + "=" * 70)
    print("TRANSAÇÕES PARA REVISÃO MANUAL (Precisam de contexto)")
    print("=" * 70)
    
    # separa transacoes que precisam de analise adicional com emails
    ids_violacoes = set(todas_violacoes['id_transacao']) if not todas_violacoes.empty else set()
    df_revisao = df[(df['valor'] > 50) & (df['valor'] <= 500) & (~df['id_transacao'].isin(ids_violacoes))]
    df_revisao = df_revisao[~df_revisao['fornecedor'].str.contains('Dunkin', case=False, na=False)]
    
    if not df_revisao.empty:
        print(f"\n{len(df_revisao)} transacoes para revisao (valor entre US$ 50-500)")
        print("   Necessitam verificar aprovacao do Gerente Regional")
        print(df_revisao[['id_transacao', 'funcionario', 'descricao', 'valor']].head(5).to_string(index=False))
    else:
        print("\nNenhuma transacao para revisao manual (todas as problematicas ja sao violacoes)")
    
    return todas_violacoes

if __name__ == "__main__":
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent.parent
    csv_path = project_root / 'data' / 'transacoes_bancarias.csv'
    resultado = executar_auditoria_final(str(csv_path))
    
    print("\n" + "=" * 70)
    print("AUDITORIA COMPLETA - CONCLUIDA")
    print("=" * 70)
    print(f"\nVerificacao final: Total de violacoes detectadas: {resultado.shape[0]}")
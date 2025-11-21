import streamlit as st
import pandas as pd
import datetime
import time
import json
import calendar 
import os
import random
from datetime import timedelta
import plotly.express as px

# --- FIREBASE IMPORTS ---
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# --- CONFIGURAÇÃO GERAL ---
st.set_page_config(page_title="Gestão Leiteira Enterprise (Cloud)", layout="wide", page_icon="☁️")

# --- CONSTANTES E PARÂMETROS ---
DIAS_PVE = 45           
DIAS_DIAGNOSTICO = 30   
DIAS_SECAGEM = 60       
GESTACAO = 283
DIAS_DESMAME = 90 
PRECO_PADRAO_LEITE = 2.50 

CATEGORIAS_RECEITA = ["Venda de Leite", "Venda de Animais", "Serviços", "Outras Receitas"]
CATEGORIAS_DESPESA = ["Ração / Nutrição", "Medicamento / Sanitário", "Infraestrutura", 
                      "Mão de Obra", "Energia", "Compra de Animais", "Outros"]
CATEGORIAS_FINANCEIRAS = CATEGORIAS_RECEITA + CATEGORIAS_DESPESA

TIPOS_SANITARIOS = ["Vacina", "Vermífugo", "Antibiótico", "Hormônio", "Casqueamento", "Outros"]

# --- 1. CONEXÃO E GERENCIAMENTO FIREBASE ---

@st.cache_resource
def init_firebase():
    """Inicializa a conexão com o Firebase (Singleton)"""
    if not firebase_admin._apps:
        try:
            # 1. Tenta carregar dos Segredos do Streamlit (Nuvem)
            if "FIREBASE_KEY" in st.secrets:
                key_content = st.secrets["FIREBASE_KEY"]
                # Se for string JSON, converte para dict
                if isinstance(key_content, str):
                    key_dict = json.loads(key_content)
                else:
                    key_dict = key_content
                cred = credentials.Certificate(key_dict)
                firebase_admin.initialize_app(cred)
            
            # 2. Se não tiver segredo, tenta arquivo local (PC)
            elif os.path.exists("firebase_key.json"):
                cred = credentials.Certificate("firebase_key.json")
                firebase_admin.initialize_app(cred)
            
            else:
                st.error("❌ Chave do Firebase não encontrada! Configure os 'Secrets' na nuvem ou coloque o arquivo json localmente.")
                st.stop()
            
        except Exception as e:
            st.error(f"Erro crítico na conexão Firebase: {e}")
            st.stop()
            
    return firestore.client()

# Inicializa o banco
try:
    db_firestore = init_firebase()
except Exception as e:
    st.error("Erro ao iniciar Firebase. Verifique se o arquivo json da chave está na pasta.")
    st.stop()

# --- FUNÇÕES DE CRUD (CREATE, READ, UPDATE, DELETE) ---

def carregar_dados_firestore():
    """Carrega todas as coleções do Firestore para o Session State (Cache Local)"""
    if 'db' not in st.session_state:
        st.session_state.db = {
            "animais": [],
            "financeiro": [],
            "estoque": [],
            "producao": [],
            "sanitario": []
        }
        
        colecoes = ["animais", "financeiro", "estoque", "producao", "sanitario"]
        
        for col in colecoes:
            docs = db_firestore.collection(col).stream()
            items = []
            for doc in docs:
                d = doc.to_dict()
                d['doc_id'] = doc.id # Guarda o ID do documento para updates futuros
                items.append(d)
            
            st.session_state.db[col] = items

def adicionar_item(colecao, dados):
    """Adiciona um novo item ao Firestore e atualiza o cache"""
    ref = db_firestore.collection(colecao).add(dados)
    dados['doc_id'] = ref[1].id
    st.session_state.db[colecao].append(dados)

def atualizar_item(colecao, doc_id, novos_dados):
    """Atualiza um item existente no Firestore e no cache"""
    db_firestore.collection(colecao).document(doc_id).update(novos_dados)
    
    # Atualiza na lista local
    for i, item in enumerate(st.session_state.db[colecao]):
        if item.get('doc_id') == doc_id:
            st.session_state.db[colecao][i].update(novos_dados)
            break

def deletar_item(colecao, doc_id):
    """Remove do Firestore e do cache"""
    db_firestore.collection(colecao).document(doc_id).delete()
    st.session_state.db[colecao] = [d for d in st.session_state.db[colecao] if d.get('doc_id') != doc_id]

def salvar_lote_dataframe(colecao, dados_editados, chave_primaria='doc_id'):
    """Salva edições feitas em tabelas (st.data_editor) de uma vez só"""
    batch = db_firestore.batch()
    count = 0
    
    for row in dados_editados:
        if row.get(chave_primaria):
            ref = db_firestore.collection(colecao).document(row[chave_primaria])
            batch.set(ref, row, merge=True)
            count += 1
            
    if count > 0:
        batch.commit()
        del st.session_state.db
        st.rerun()

def limpar_banco_completo():
    """PERIGO: Apaga todos os dados de todas as coleções"""
    colecoes = ["animais", "financeiro", "estoque", "producao", "sanitario"]
    batch = db_firestore.batch()
    count = 0
    
    for col in colecoes:
        docs = db_firestore.collection(col).list_documents()
        for doc in docs:
            batch.delete(doc)
            count += 1
            if count >= 400: # Limite do Firestore por batch
                batch.commit()
                batch = db_firestore.batch()
                count = 0
    
    if count > 0:
        batch.commit()
    
    # Limpa memória local
    del st.session_state.db
    st.success("Banco de dados resetado com sucesso! Sistema pronto para uso real.")
    time.sleep(2)
    st.rerun()

# Carrega os dados ao iniciar
carregar_dados_firestore()

# --- CÁLCULO DE SALDO ---
def calcular_saldo_atual():
    df = pd.DataFrame(st.session_state.db['financeiro'])
    if df.empty: return 0, 0, 0
    receitas = df[df['cat'].isin(CATEGORIAS_RECEITA)]['valor'].sum()
    despesas = df[df['cat'].isin(CATEGORIAS_DESPESA)]['valor'].sum()
    return receitas - despesas, receitas, despesas

# --- 2. MOTOR DE REGRAS (ADAPTADO PARA FIREBASE) ---
def processar_alertas():
    hoje = datetime.date.today()
    alertas = []
    for index, animal in enumerate(st.session_state.db["animais"]):
        doc_id = animal.get('doc_id')
        
        if animal['status'] in ['Lactação', 'Seca']:
            d_insem = datetime.datetime.strptime(animal['dt_insem'], "%Y-%m-%d").date() if animal.get('dt_insem') else None
            d_parto = datetime.datetime.strptime(animal['dt_parto'], "%Y-%m-%d").date() if animal.get('dt_parto') else None
            
            if d_insem and not animal.get('prenhez'):
                if (hoje - d_insem).days >= DIAS_DIAGNOSTICO:
                    alertas.append({"nivel": "critico", "msg": f"CONFIRMAR PRENHEZ: {animal['nome']}", "detalhe": f"Inseminada há {(hoje - d_insem).days} dias", "acao": "diagnostico", "doc_id": doc_id})
            
            if not animal.get('prenhez') and not d_insem and d_parto and animal['status'] == 'Lactação':
                if (hoje - d_parto).days > DIAS_PVE:
                    alertas.append({"nivel": "critico", "msg": f"INSEMINAR: {animal['nome']}", "detalhe": f"Vazia há {(hoje - d_parto).days} dias", "acao": "inseminar", "doc_id": doc_id})

            if animal.get('prenhez') and d_insem and animal['status'] == 'Lactação':
                prev_parto = d_insem + timedelta(days=GESTACAO)
                dias_secar = (prev_parto - timedelta(days=DIAS_SECAGEM) - hoje).days
                if dias_secar <= 0:
                    alertas.append({"nivel": "critico", "msg": f"SECAR VACA: {animal['nome']}", "detalhe": "Risco para o bezerro!", "acao": "secar", "doc_id": doc_id})

        if animal['status'] == 'Bezerro':
            d_nasc_str = animal.get('nasc', str(hoje))
            if not d_nasc_str: d_nasc_str = str(hoje)
            d_nasc = datetime.datetime.strptime(d_nasc_str, "%Y-%m-%d").date()
            idade = (hoje - d_nasc).days
            if idade <= 2 and not animal.get('colostro'):
                alertas.append({"nivel": "critico", "msg": f"DAR COLOSTRO: {animal['nome']}", "detalhe": "Recém-nascido!", "acao": "colostro", "doc_id": doc_id})
            if idade >= DIAS_DESMAME:
                alertas.append({"nivel": "atencao", "msg": f"DESMAME: {animal['nome']}", "detalhe": f"Idade: {idade} dias", "acao": "desmamar", "doc_id": doc_id})
    return alertas

# --- 3. HELPER BI (LÓGICA DE PREÇO REALIZADO) ---
def calcular_bi(df_prod, df_fin, periodo_ini, periodo_fim):
    if df_prod.empty: return None
    
    total_leite = df_prod['leite'].sum()
    total_racao_kg = df_prod['racao'].sum()
    
    receita_leite = 0.0
    p_ini_str = str(periodo_ini)
    p_fim_str = str(periodo_fim)

    if not df_fin.empty:
        for index, row in df_fin.iterrows():
            if row['cat'] == "Venda de Leite":
                if 'ref_ini' in row and pd.notnull(row['ref_ini']) and str(row['ref_ini']) != 'None' and str(row['ref_ini']) != 'NaT':
                    if str(row['ref_ini']) >= p_ini_str and str(row['ref_ini']) <= p_fim_str:
                        receita_leite += row['valor']
                elif str(row['data']) >= p_ini_str and str(row['data']) <= p_fim_str:
                    if 'ref_ini' not in row or pd.isnull(row['ref_ini']) or str(row['ref_ini']) == 'None' or str(row['ref_ini']) == 'NaT':
                        receita_leite += row['valor']
    
    gastos_fixos = 0.0
    if not df_fin.empty:
        mask_despesa = (df_fin['cat'].isin(CATEGORIAS_DESPESA)) & \
                       (df_fin['data'] >= periodo_ini) & \
                       (df_fin['data'] <= periodo_fim)
        gastos_fixos = df_fin[mask_despesa]['valor'].sum()

    custo_racao_estimado = total_racao_kg * 2.00 
    
    custo_total_operacao = custo_racao_estimado + gastos_fixos
    preco_medio_recebido = receita_leite / total_leite if total_leite > 0 else 0.0
    custo_litro = custo_total_operacao / total_leite if total_leite > 0 else 0.0
    lucro_liquido = receita_leite - custo_total_operacao
    
    return {
        "receita": receita_leite, 
        "custo_racao": custo_racao_estimado, 
        "gastos_extras": gastos_fixos,
        "custo_total": custo_total_operacao, 
        "lucro": lucro_liquido,
        "custo_litro": custo_litro, 
        "preco_medio": preco_medio_recebido,
        "producao_total": total_leite
    }

# --- MENU LATERAL ---
st.sidebar.title("Gestor Cloud ☁️")
menu = st.sidebar.radio("Módulos", [
    "📊 BI & Inteligência", 
    "🧬 Veterinária & Reprodução", 
    "💉 Sanidade (Novo)", 
    "👶 Berçário", 
    "💰 Financeiro 360", 
    "📦 Armazém Avançado", 
    "🐄 Rebanho Geral", 
    "📅 Calendário & Agenda",
    "⚙️ Configurações"
])

# ==============================================================================
# MÓDULO 1: BI & INTELIGÊNCIA
# ==============================================================================
if menu == "📊 BI & Inteligência":
    st.title("Business Intelligence (BI)")
    
    tab_macro, tab_micro, tab_tabela = st.tabs(["🏢 Dashboard Geral", "🐄 Raio-X Individual", "📑 Relatório Comparativo"])
    
    df_prod = pd.DataFrame(st.session_state.db["producao"])
    df_fin = pd.DataFrame(st.session_state.db["financeiro"])
    
    if not df_prod.empty: df_prod['data'] = pd.to_datetime(df_prod['data']).dt.date
    if not df_fin.empty: df_fin['data'] = pd.to_datetime(df_fin['data']).dt.date

    with tab_macro:
        c1, c2 = st.columns(2)
        ini = c1.date_input("Início Análise", datetime.date.today() - timedelta(days=30))
        fim = c2.date_input("Fim Análise", datetime.date.today())
        
        df_prod_filt = df_prod.copy()
        if not df_prod.empty:
            df_prod_filt = df_prod[(df_prod['data'] >= ini) & (df_prod['data'] <= fim)]
        
        kpis = calcular_bi(df_prod_filt, df_fin, ini, fim)
        
        if kpis:
            usando_estimativa = False
            if kpis['preco_medio'] == 0:
                usando_estimativa = True
                kpis['receita'] = kpis['producao_total'] * PRECO_PADRAO_LEITE
                kpis['lucro'] = kpis['receita'] - kpis['custo_total']

            st.markdown(f"#### Resultados Consolidados ({ini.strftime('%d/%m')} a {fim.strftime('%d/%m')})")
            
            if usando_estimativa:
                st.warning(f"⚠️ Nenhuma receita de leite vinculada neste período. Usando R$ {PRECO_PADRAO_LEITE:.2f}/L.")

            k1, k2, k3, k4 = st.columns(4)
            
            preco_display = kpis['preco_medio'] if kpis['preco_medio'] > 0 else PRECO_PADRAO_LEITE
            cor_preco = "normal" if preco_display > kpis['custo_litro'] else "inverse"
            
            k1.metric("Preço Médio/L", f"R$ {preco_display:.2f}", delta="Estimado" if usando_estimativa else "Realizado", delta_color="off" if usando_estimativa else "normal")
            k2.metric("Custo por Litro", f"R$ {kpis['custo_litro']:.2f}", delta_color="inverse")
            k3.metric("Receita Total", f"R$ {kpis['receita']:,.2f}")
            k4.metric("Lucro Operacional", f"R$ {kpis['lucro']:,.2f}", delta_color="normal" if kpis['lucro'] > 0 else "inverse")
            
            st.divider()
            
            g1, g2 = st.columns(2)
            with g1:
                st.subheader("Produção Diária")
                if not df_prod_filt.empty:
                    diario = df_prod_filt.groupby("data")['leite'].sum().reset_index()
                    st.line_chart(diario, x="data", y="leite")
            with g2:
                st.subheader("Custos Totais")
                if not df_fin.empty:
                    mask_desp = (df_fin['cat'].isin(CATEGORIAS_DESPESA)) & (df_fin['data'] >= ini) & (df_fin['data'] <= fim)
                    df_pizza = df_fin[mask_desp].copy()
                    dados_pizza = df_pizza.groupby('cat')['valor'].sum().reset_index()
                    dados_pizza.loc[len(dados_pizza)] = ['Nutrição (Estimada)', kpis['custo_racao']]
                    fig = px.pie(dados_pizza, values='valor', names='cat', hole=0.5)
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Sem dados suficientes para gerar o dashboard macro.")

    with tab_micro:
        st.markdown("#### 🔎 Análise Detalhada por Vaca")
        cr1, cr2, cr3 = st.columns([2, 1, 1])
        lista_vacas = [a for a in st.session_state.db["animais"] if a['status'] in ['Lactação', 'Seca']]
        ops_vacas = {a['id']: a['nome'] for a in lista_vacas}
        vaca_id = cr1.selectbox("Selecione a Vaca:", list(ops_vacas.keys()), format_func=lambda x: f"{x} - {ops_vacas[x]}")
        dt_ini_v = cr2.date_input("De:", datetime.date.today() - timedelta(days=30), key="dti_v")
        dt_fim_v = cr3.date_input("Até:", datetime.date.today(), key="dtf_v")
        st.divider()
        
        if vaca_id and not df_prod.empty:
            mask_prod_vaca = (df_prod['id_animal'] == vaca_id) & (df_prod['data'] >= dt_ini_v) & (df_prod['data'] <= dt_fim_v)
            df_vaca = df_prod[mask_prod_vaca]
            
            gastos_diretos = 0.0
            df_fin_vaca = pd.DataFrame()
            if not df_fin.empty and 'animal' in df_fin.columns:
                mask_fin_vaca = (df_fin['animal'] == vaca_id) & (df_fin['data'] >= dt_ini_v) & (df_fin['data'] <= dt_fim_v) & (df_fin['cat'].isin(CATEGORIAS_DESPESA))
                df_fin_vaca = df_fin[mask_fin_vaca]
                gastos_diretos = df_fin_vaca['valor'].sum()

            if not df_vaca.empty:
                total_leite_v = df_vaca['leite'].sum()
                total_racao_v = df_vaca['racao'].sum()
                media_racao_dia = df_vaca['racao'].mean()
                
                preco_base = kpis['preco_medio'] if 'kpis' in locals() and kpis and kpis['preco_medio'] > 0 else PRECO_PADRAO_LEITE
                
                receita_estimada = total_leite_v * preco_base
                custo_racao_v = total_racao_v * 2.00
                custo_total_v = custo_racao_v + gastos_diretos
                margem_v = receita_estimada - custo_total_v
                
                c_kpi1, c_kpi2, c_kpi3, c_kpi4 = st.columns(4)
                c_kpi1.metric("Produção Total", f"{total_leite_v:.1f} L")
                c_kpi2.metric("Receita (Ref)", f"R$ {receita_estimada:.2f}")
                c_kpi3.metric("Custo Total", f"R$ {custo_total_v:.2f}")
                c_kpi4.metric("Margem", f"R$ {margem_v:.2f}", delta_color="normal" if margem_v > 0 else "inverse")
                
                col_zoo, col_fam = st.columns([2, 1])
                with col_zoo:
                    st.subheader("📈 Curva: Leite vs Ração")
                    df_graf = df_vaca[['data', 'leite', 'racao']].set_index('data')
                    st.line_chart(df_graf)
                with col_fam:
                    st.subheader("🧬 Filhos")
                    bezerros_dela = [b for b in st.session_state.db["animais"] if b.get('mae_id') == vaca_id]
                    if bezerros_dela:
                        for b in bezerros_dela:
                            st.info(f"🆔 {b['id']} - {b['nome']} ({b['status']})")
                    else:
                        st.warning("Sem registros.")
                        
                st.subheader(f"💲 Gastos Exclusivos")
                if not df_fin_vaca.empty:
                    st.dataframe(df_fin_vaca[['data', 'cat', 'desc', 'valor']], use_container_width=True)
                else:
                    st.info("Sem gastos específicos.")
            else:
                st.warning("Sem registros de ordenha neste período.")
        else:
            st.info("Selecione uma vaca.")

    with tab_tabela:
        st.markdown("#### 📑 Relatório Comparativo")
        c_t1, c_t2 = st.columns(2)
        dt_ini_t = c_t1.date_input("Início:", datetime.date.today() - timedelta(days=30), key="dti_t")
        dt_fim_t = c_t2.date_input("Fim:", datetime.date.today(), key="dtf_t")
        
        if st.button("Gerar Tabela"):
            if not df_prod.empty:
                mask_periodo = (df_prod['data'] >= dt_ini_t) & (df_prod['data'] <= dt_fim_t)
                df_p_filt = df_prod[mask_periodo]
                
                if not df_p_filt.empty:
                    resumo = df_p_filt.groupby(['id_animal', 'nome_animal']).agg(
                        Leite_Total=('leite', 'sum'),
                        Racao_Total=('racao', 'sum'),
                        Dias_Ordenha=('data', 'nunique')
                    ).reset_index()
                    
                    preco_ref = kpis['preco_medio'] if 'kpis' in locals() and kpis and kpis['preco_medio'] > 0 else PRECO_PADRAO_LEITE
                    
                    resumo['Receita_Est'] = resumo['Leite_Total'] * preco_ref
                    resumo['Custo_Racao'] = resumo['Racao_Total'] * 2.00
                    resumo['Margem_Bruta'] = resumo['Receita_Est'] - resumo['Custo_Racao']
                    resumo['Media_Leite_Dia'] = resumo['Leite_Total'] / resumo['Dias_Ordenha']
                    
                    st.dataframe(
                        resumo.style.format({
                            "Leite_Total": "{:.1f} L",
                            "Racao_Total": "{:.1f} kg",
                            "Receita_Est": "R$ {:.2f}",
                            "Custo_Racao": "R$ {:.2f}",
                            "Margem_Bruta": "R$ {:.2f}",
                            "Media_Leite_Dia": "{:.1f} L/dia"
                        }),
                        use_container_width=True
                    )
                else:
                    st.warning("Sem dados neste período.")
            else:
                st.warning("Banco vazio.")

# ==============================================================================
# MÓDULO 2: VETERINÁRIA
# ==============================================================================
elif menu == "🧬 Veterinária & Reprodução":
    st.title("Central Veterinária")
    col_alertas, col_parto = st.columns([2, 1])
    with col_alertas:
        st.subheader("Monitoramento")
        alertas = processar_alertas()
        if alertas:
            for item in alertas:
                with st.container(border=True):
                    c_txt, c_btn = st.columns([3, 1])
                    cor = "red" if item['nivel'] == "critico" else "orange"
                    c_txt.markdown(f":{cor}[**{item['msg']}**] - {item.get('detalhe', '')}")
                    
                    if item['acao'] == "inseminar":
                        if c_btn.button("Registrar", key=f"i{item['doc_id']}"):
                            atualizar_item("animais", item['doc_id'], {'dt_insem': str(datetime.date.today())})
                            st.rerun()
                    elif item['acao'] == "diagnostico":
                        c1, c2 = c_btn.columns(2)
                        if c1.button("Prenhe", key=f"p{item['doc_id']}"):
                            atualizar_item("animais", item['doc_id'], {'prenhez': True})
                            st.rerun()
                        if c2.button("Vazia", key=f"v{item['doc_id']}"):
                            atualizar_item("animais", item['doc_id'], {'prenhez': False, 'dt_insem': None})
                            st.rerun()
                    elif item['acao'] == "secar":
                        if c_btn.button("Secar", key=f"s{item['doc_id']}"):
                            atualizar_item("animais", item['doc_id'], {'status': "Seca", 'freq': 0})
                            st.rerun()
                    elif item['acao'] == "colostro":
                        if c_btn.button("Confirmar", key=f"c{item['doc_id']}"):
                            atualizar_item("animais", item['doc_id'], {'colostro': True})
                            st.rerun()
        else:
            st.success("Manejo 100% em dia!")
    
    with col_parto:
        st.info("👶 Registrar Parto")
        with st.form("parto"):
            candidatas = [f"{a['id']} - {a['nome']}" for a in st.session_state.db["animais"] if a['status'] != 'Bezerro']
            mae_sel = st.selectbox("Mãe:", candidatas)
            dt_nasc = st.date_input("Data:", datetime.date.today())
            b_id = st.text_input("ID Bezerro")
            b_nome = st.text_input("Nome")
            b_sexo = st.radio("Sexo", ["Fêmea", "Macho"], horizontal=True)
            nova_freq = st.number_input("Ordenhas/dia:", 1, 3, 2)
            
            if st.form_submit_button("Salvar Nascimento"):
                if mae_sel and b_id:
                    id_mae = mae_sel.split(" - ")[0]
                    # Encontra a mãe na lista para pegar o ID do documento
                    mae_obj = next((a for a in st.session_state.db["animais"] if a['id'] == id_mae), None)
                    
                    if mae_obj:
                        # Atualiza a mãe
                        atualizar_item("animais", mae_obj['doc_id'], {
                            "status": "Lactação", "freq": nova_freq, 
                            "dt_parto": str(dt_nasc), "prenhez": False, "dt_insem": None
                        })
                        # Cria o bezerro
                        adicionar_item("animais", {
                            "id": b_id, "nome": b_nome, "status": "Bezerro", 
                            "lote": "Berçário", "nasc": str(dt_nasc), 
                            "mae_id": id_mae, "sexo": b_sexo, "colostro": False
                        })
                        st.success("Nascimento registrado!")
                        time.sleep(1)
                        st.rerun()

# ==============================================================================
# MÓDULO 3: SANIDADE
# ==============================================================================
elif menu == "💉 Sanidade (Novo)":
    st.title("Controle Sanitário")
    c_form, c_hist = st.columns([1, 2])
    with c_form:
        st.info("Novo Registro")
        with st.form("sanidade"):
            tipo = st.selectbox("Tipo:", TIPOS_SANITARIOS)
            prod = st.text_input("Produto Usado")
            modo = st.radio("Aplicação:", ["Individual", "Rebanho Todo"])
            sel_animal = None
            if modo == "Individual":
                ops = {a['id']: a['nome'] for a in st.session_state.db["animais"]}
                sel_animal = st.selectbox("Animal:", list(ops.keys()), format_func=lambda x: f"{x} - {ops[x]}")
            custo = st.number_input("Custo Total (R$):", min_value=0.0)
            obs = st.text_area("Obs:")
            if st.form_submit_button("Salvar"):
                novo_reg = {"data": str(datetime.date.today()), "tipo": tipo, "prod": prod, "modo": modo, "animal": sel_animal, "custo": custo, "obs": obs}
                adicionar_item("sanitario", novo_reg)
                if custo > 0:
                    adicionar_item("financeiro", {
                        "data": str(datetime.date.today()), "cat": "Medicamento / Sanitário", 
                        "desc": f"{tipo} - {prod}", "valor": custo, 
                        "tipo": "Geral" if modo=="Rebanho Todo" else "Individual", "animal": sel_animal
                    })
                st.success("Salvo!")
                st.rerun()
    with c_hist:
        st.write("### Histórico")
        if st.session_state.db["sanitario"]:
            st.dataframe(pd.DataFrame(st.session_state.db["sanitario"]), use_container_width=True)

# ==============================================================================
# MÓDULO 4: BERÇÁRIO
# ==============================================================================
elif menu == "👶 Berçário":
    st.markdown("### 🍼 Gestão de Bezerros")
    tab_ver, tab_entrada, tab_saida = st.tabs(["👁️ Visualizar/Editar", "➕ Entrada Manual", "🚀 Saída/Evolução"])
    
    with tab_ver:
        bezerros = [a for a in st.session_state.db["animais"] if a['status'] == 'Bezerro']
        if bezerros:
            df_b = pd.DataFrame(bezerros)
            if 'nasc' in df_b.columns:
                df_b['nasc'] = pd.to_datetime(df_b['nasc'])
            
            st.info("Edite dados básicos diretamente na tabela:")
            df_edit = st.data_editor(
                df_b,
                column_config={
                    "doc_id": None,
                    "nasc": st.column_config.DateColumn("Nascimento", format="YYYY-MM-DD"),
                    "colostro": st.column_config.CheckboxColumn("Colostro OK?"),
                    "sexo": st.column_config.SelectboxColumn("Sexo", options=["Fêmea", "Macho"]),
                    "mae_id": "ID Mãe",
                    "id": st.column_config.TextColumn("Brinco", disabled=True)
                },
                use_container_width=True,
                key="bez_edit",
                hide_index=True
            )
            if st.button("💾 Salvar Alterações Tabela"):
                recs = df_edit.to_dict('records')
                # Formata datas antes de salvar no banco
                for r in recs:
                    if isinstance(r.get('nasc'), (pd.Timestamp, datetime.date)):
                        r['nasc'] = r['nasc'].strftime('%Y-%m-%d')
                
                salvar_lote_dataframe("animais", recs)
                st.success("Dados atualizados!")
        else:
            st.warning("Nenhum bezerro no berçário.")

    with tab_entrada:
        st.caption("Compra de bezerros externos.")
        with st.form("novo_bezerro"):
            c1, c2, c3 = st.columns(3)
            b_id = c1.text_input("Brinco/ID")
            b_nome = c2.text_input("Nome")
            b_nasc = c3.date_input("Nascimento")
            b_sexo = st.radio("Sexo", ["Fêmea", "Macho"], horizontal=True)
            b_valor = st.number_input("Valor de Compra (R$)", min_value=0.0)
            if st.form_submit_button("Cadastrar Compra"):
                if b_id and b_nome:
                    adicionar_item("animais", {
                        "id": b_id, "nome": b_nome, "status": "Bezerro", 
                        "lote": "Berçário", "nasc": str(b_nasc), "mae_id": None, 
                        "sexo": b_sexo, "colostro": False, "freq": 0
                    })
                    if b_valor > 0:
                        adicionar_item("financeiro", {
                            "data": str(datetime.date.today()), "cat": "Compra de Animais", 
                            "desc": f"Compra Bezerro {b_id}", "valor": b_valor, 
                            "tipo": "Individual", "animal": b_id
                        })
                    st.success("Bezerro adicionado!")
                    st.rerun()
                else:
                    st.error("ID e Nome obrigatórios.")

    with tab_saida:
        st.markdown("#### Definir Destino")
        if not bezerros:
            st.info("Sem animais.")
        else:
            opcoes_bez = {b['id']: f"{b['nome']} ({b['sexo']})" for b in bezerros}
            sel_b_id = st.selectbox("Selecione o Bezerro:", list(opcoes_bez.keys()), format_func=lambda x: f"{x} - {opcoes_bez[x]}")
            tipo_saida = st.radio("Tipo de Saída:", ["📈 Evolução (Vai para Pasto)", "💰 Venda (Sai da Fazenda)"], horizontal=True)
            
            # Busca o objeto completo do bezerro selecionado
            b_selecionado = next((b for b in bezerros if b['id'] == sel_b_id), None)

            if tipo_saida == "💰 Venda (Sai da Fazenda)":
                val_venda = st.number_input("Valor da Venda (R$):", min_value=0.0)
                if st.button("Confirmar Venda"):
                    adicionar_item("financeiro", {
                        "data": str(datetime.date.today()), "cat": "Venda de Animais", 
                        "desc": f"Venda Bezerro {sel_b_id}", "valor": val_venda, 
                        "tipo": "Receita", "animal": sel_b_id
                    })
                    deletar_item("animais", b_selecionado['doc_id'])
                    st.success("Venda realizada!")
                    st.rerun()
            else: 
                novo_lote = st.selectbox("Novo Lote:", ["Recria", "Geral", "Engorda"])
                novo_status = "Novilha" if b_selecionado['sexo'] == "Fêmea" else "Garrote"
                st.info(f"Animal virará **{novo_status}** no lote **{novo_lote}**.")
                if st.button("Processar Evolução"):
                    atualizar_item("animais", b_selecionado['doc_id'], {
                        'status': novo_status, 'lote': novo_lote
                    })
                    st.success("Evolução concluída!")
                    st.rerun()

# ==============================================================================
# MÓDULO 5: FINANCEIRO (COM EDIÇÃO DIRETA NA TABELA)
# ==============================================================================
elif menu == "💰 Financeiro 360":
    st.markdown("### 💸 Fluxo de Caixa & Saldo")
    saldo, rec_total, desp_total = calcular_saldo_atual()
    k1, k2, k3 = st.columns(3)
    k1.metric("Receitas Totais", f"R$ {rec_total:,.2f}", delta="Entradas")
    k2.metric("Despesas Totais", f"R$ {desp_total:,.2f}", delta="-Saídas", delta_color="inverse")
    k3.metric("SALDO EM CAIXA", f"R$ {saldo:,.2f}", delta_color="normal" if saldo >= 0 else "inverse")
    st.divider()
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.info("Novo Lançamento")
        tipo_lancamento = st.radio("Selecione o Tipo:", ["Despesa", "Receita"], horizontal=True)
        cats_disponiveis = CATEGORIAS_RECEITA if tipo_lancamento == "Receita" else CATEGORIAS_DESPESA
        
        with st.form("fin"):
            cat = st.selectbox("Categoria", cats_disponiveis)
            desc = st.text_input("Descrição (Opcional)")
            val = st.number_input("Valor (R$)", min_value=0.0, step=10.0)
            
            ref_ini, ref_fim = None, None
            if cat == "Venda de Leite":
                st.markdown("---")
                st.markdown("**:blue[📅 Referência do Pagamento]**")
                cr1, cr2 = st.columns(2)
                ref_ini = cr1.date_input("De:", datetime.date.today() - timedelta(days=30))
                ref_fim = cr2.date_input("Até:", datetime.date.today())
                st.markdown("---")

            if st.form_submit_button("💾 Lançar Movimentação"):
                novo_reg = {"data": str(datetime.date.today()), "cat": cat, "desc": desc, "valor": val, "tipo": "Geral", "animal": None}
                if cat == "Venda de Leite":
                    novo_reg["ref_ini"] = str(ref_ini)
                    novo_reg["ref_fim"] = str(ref_fim)
                adicionar_item("financeiro", novo_reg)
                st.success("Lançado!")
                time.sleep(1)
                st.rerun()
                
    with c2:
        st.write("### 📝 Extrato Detalhado (Editável)")
        if st.session_state.db["financeiro"]:
            df_f = pd.DataFrame(st.session_state.db["financeiro"])
            
            # Garante colunas
            if "ref_ini" not in df_f.columns: df_f["ref_ini"] = None
            if "ref_fim" not in df_f.columns: df_f["ref_fim"] = None
            
            # Converte datas
            for c in ['data', 'ref_ini', 'ref_fim']:
                df_f[c] = pd.to_datetime(df_f[c], errors='coerce')

            edited_df = st.data_editor(
                df_f.sort_values('data', ascending=False), 
                use_container_width=True,
                num_rows="dynamic",
                column_config={
                    "doc_id": None, # Oculta ID técnico
                    "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                    "data": st.column_config.DateColumn("Data Caixa", format="DD/MM/YYYY"),
                    "ref_ini": st.column_config.DateColumn("Ref. Início (Leite)", format="DD/MM/YYYY"),
                    "ref_fim": st.column_config.DateColumn("Ref. Fim (Leite)", format="DD/MM/YYYY"),
                    "cat": st.column_config.SelectboxColumn("Categoria", options=CATEGORIAS_FINANCEIRAS),
                },
                key="editor_financeiro"
            )

            if st.button("💾 Salvar Alterações no Extrato"):
                records = edited_df.to_dict('records')
                
                # Formata datas de volta para string
                for r in records:
                    def fmt_date(d):
                        if pd.isnull(d): return None
                        if isinstance(d, (pd.Timestamp, datetime.date, datetime.datetime)):
                            return d.strftime('%Y-%m-%d')
                        return str(d).split('T')[0] 

                    r['data'] = fmt_date(r['data'])
                    r['ref_ini'] = fmt_date(r['ref_ini'])
                    r['ref_fim'] = fmt_date(r['ref_fim'])

                salvar_lote_dataframe("financeiro", records)
                st.success("Extrato atualizado com sucesso!")
        else:
            st.warning("Caixa vazio.")

# ==============================================================================
# MÓDULO 6: ARMAZÉM (ATUALIZADO: LISTA COMPLETA + FINANCEIRO)
# ==============================================================================
elif menu == "📦 Armazém Avançado":
    st.markdown("### 📦 Gestão de Estoque Completo")
    
    tab_lista, tab_compra, tab_uso = st.tabs(["📋 Estoque Atual", "🛒 Registrar Compra", "📉 Registrar Uso"])
    
    # --- ABA 1: VISÃO GERAL DO ESTOQUE ---
    with tab_lista:
        if st.session_state.db["estoque"]:
            df_est = pd.DataFrame(st.session_state.db["estoque"])
            df_est['valor_total'] = df_est['qtd'] * df_est['custo_medio']
            
            # KPI de Valor Total em Estoque
            total_patrimonio = df_est['valor_total'].sum()
            st.metric("Valor Total em Estoque (Patrimônio)", f"R$ {total_patrimonio:,.2f}")
            
            st.dataframe(
                df_est, 
                use_container_width=True,
                column_config={
                    "doc_id": None,
                    "item": "Produto",
                    "qtd": st.column_config.NumberColumn("Qtd Atual", format="%.2f"),
                    "un": "Unidade",
                    "custo_medio": st.column_config.NumberColumn("Custo Médio (R$)", format="R$ %.2f"),
                    "valor_total": st.column_config.NumberColumn("Valor Total (R$)", format="R$ %.2f"),
                },
                hide_index=True
            )
        else:
            st.info("Nenhum produto cadastrado no estoque.")

    # --- ABA 2: REGISTRAR COMPRA (ENTRADA + FINANCEIRO) ---
    with tab_compra:
        st.caption("Lança a entrada no estoque e a despesa no financeiro automaticamente.")
        
        with st.form("compra_estoque"):
            col_a, col_b = st.columns(2)
            
            # Lista de sugestões (produtos já cadastrados)
            prods_existentes = [p['item'] for p in st.session_state.db["estoque"]]
            
            # Permite digitar um novo ou selecionar existente
            prod_nome = col_a.text_input("Nome do Produto (Ex: Sal Mineral, Ração):", 
                                         placeholder="Digite ou copie da lista ao lado" if not prods_existentes else f"Sugestões: {', '.join(prods_existentes[:3])}...")
            
            qtd_compra = col_a.number_input("Quantidade Comprada:", min_value=0.1, step=1.0)
            unidade = col_a.selectbox("Unidade:", ["kg", "sc (saco)", "L", "un", "dose"])
            
            valor_total_nota = col_b.number_input("Valor Total da Nota (R$):", min_value=0.0, step=10.0)
            categoria_fin = col_b.selectbox("Categoria Financeira:", ["Ração / Nutrição", "Medicamento / Sanitário", "Outros"])
            fornecedor = col_b.text_input("Fornecedor:")
            
            # Cálculo do custo unitário da compra atual
            custo_un_compra = valor_total_nota / qtd_compra if qtd_compra > 0 else 0
            if valor_total_nota > 0:
                col_b.caption(f"Custo Unitário desta compra: R$ {custo_un_compra:.2f} / {unidade}")
            
            if st.form_submit_button("✅ Confirmar Entrada"):
                if prod_nome and qtd_compra > 0 and valor_total_nota > 0:
                    # 1. Atualizar Estoque (Média Ponderada)
                    encontrado = False
                    for item in st.session_state.db["estoque"]:
                        if item["item"].lower() == prod_nome.lower():
                            # Cálculo Média Ponderada
                            valor_antigo_total = item["qtd"] * item["custo_medio"]
                            nova_qtd_total = item["qtd"] + qtd_compra
                            novo_valor_total = valor_antigo_total + valor_total_nota
                            novo_custo_medio = novo_valor_total / nova_qtd_total
                            
                            atualizar_item("estoque", item['doc_id'], {
                                "qtd": nova_qtd_total,
                                "custo_medio": novo_custo_medio,
                                "un": unidade
                            })
                            encontrado = True
                            break
                    
                    if not encontrado:
                        adicionar_item("estoque", {
                            "item": prod_nome,
                            "qtd": qtd_compra,
                            "un": unidade,
                            "custo_medio": custo_un_compra
                        })
                    
                    # 2. Lançar no Financeiro
                    adicionar_item("financeiro", {
                        "data": str(datetime.date.today()),
                        "cat": categoria_fin,
                        "desc": f"Compra {prod_nome} ({qtd_compra}{unidade}) - {fornecedor}",
                        "valor": valor_total_nota,
                        "tipo": "Geral",
                        "animal": None
                    })
                    
                    st.success(f"Estoque de {prod_nome} atualizado e despesa lançada!")
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.error("Preencha Nome, Quantidade e Valor Total.")

    # --- ABA 3: REGISTRAR USO (BAIXA) ---
    with tab_uso:
        st.caption("Registra o consumo interno (ex: ração dada hoje, remédio aplicado). Não gera custo financeiro novo (já foi pago na compra).")
        
        if st.session_state.db["estoque"]:
            opcoes_estoque = {p['item']: f"{p['item']} (Atual: {p['qtd']:.1f} {p['un']})" for p in st.session_state.db["estoque"]}
            
            c_uso1, c_uso2 = st.columns(2)
            item_uso = c_uso1.selectbox("Produto utilizado:", list(opcoes_estoque.keys()), format_func=lambda x: opcoes_estoque[x])
            qtd_uso = c_uso2.number_input("Quantidade usada:", min_value=0.0, step=0.5)
            
            if st.button("📉 Confirmar Baixa"):
                # Encontra o item
                item_obj = next((i for i in st.session_state.db["estoque"] if i["item"] == item_uso), None)
                
                if item_obj:
                    if item_obj["qtd"] >= qtd_uso:
                        nova_qtd = item_obj["qtd"] - qtd_uso
                        atualizar_item("estoque", item_obj['doc_id'], {'qtd': nova_qtd})
                        st.success(f"Baixa realizada! Restam {nova_qtd:.1f} {item_obj['un']}.")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Estoque insuficiente! Você tem apenas {item_obj['qtd']} {item_obj['un']}.")
        else:
            st.warning("Estoque vazio. Faça uma compra antes.")

# ==============================================================================
# MÓDULO 7: REBANHO GERAL (CORRIGIDO: COLUNAS FIXAS NA ESQUERDA)
# ==============================================================================
elif menu == "🐄 Rebanho Geral":
    st.markdown("### 🐄 Inventário e Gestão")

    # --- ÁREA DE CADASTRO MANUAL ---
    with st.expander("➕ CADASTRAR NOVO ANIMAL (Entrada Inicial/Inventário)", expanded=False):
        st.info("Use esta área para cadastrar animais que já estão na fazenda.")
        with st.form("form_cadastro_geral"):
            c_cad1, c_cad2, c_cad3 = st.columns(3)
            novo_id = c_cad1.text_input("Brinco / ID do Animal")
            novo_nome = c_cad2.text_input("Nome / Apelido")
            novo_sexo = c_cad3.radio("Sexo", ["Fêmea", "Macho"], horizontal=True)
            
            c_cad4, c_cad5, c_cad6 = st.columns(3)
            novo_status = c_cad4.selectbox("Status Atual", ["Lactação", "Seca", "Novilha", "Garrote", "Touro"])
            novo_lote = c_cad5.selectbox("Lote Inicial", ["A", "B", "C", "Maternidade", "Recria", "Engorda", "Geral"])
            novo_nasc = c_cad6.date_input("Data Nascimento (Aprox.)", value=None)
            
            st.markdown("---")
            st.caption("Dados Reprodutivos (Opcional - Apenas para Fêmeas)")
            c_rep1, c_rep2 = st.columns(2)
            novo_parto = c_rep1.date_input("Último Parto", value=None)
            novo_insem = c_rep2.date_input("Última Inseminação", value=None)
            nova_prenhez = st.checkbox("Animal está Prenhe?")
            
            if st.form_submit_button("💾 Salvar Animal"):
                if novo_id and novo_nome:
                    # Verifica duplicidade
                    ids_existentes = [a['id'] for a in st.session_state.db["animais"]]
                    if novo_id in ids_existentes:
                        st.error("Erro: Já existe um animal com este ID!")
                    else:
                        dados_animal = {
                            "id": novo_id, "nome": novo_nome, "status": novo_status,
                            "lote": novo_lote, "sexo": novo_sexo,
                            "nasc": str(novo_nasc) if novo_nasc else None,
                            "freq": 2 if novo_status == "Lactação" else 0,
                            "mae_id": None, "colostro": True,
                            "dt_parto": str(novo_parto) if novo_parto else None,
                            "dt_insem": str(novo_insem) if novo_insem else None,
                            "prenhez": nova_prenhez
                        }
                        adicionar_item("animais", dados_animal)
                        st.success(f"Sucesso! {novo_nome} cadastrado.")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.warning("Brinco e Nome são obrigatórios.")

    st.divider()
    
    # --- TABELA DE GESTÃO ---
    df_raw = pd.DataFrame(st.session_state.db["animais"])
    
    if df_raw.empty:
        st.warning("Nenhum animal cadastrado.")
    else:
        # KPIs de Lotes
        contagem_lotes = df_raw['lote'].value_counts().to_dict()
        if len(contagem_lotes) > 0:
            cols_kpi = st.columns(min(len(contagem_lotes), 6))
            for i, (lote, qtd) in enumerate(contagem_lotes.items()):
                if i < 6: cols_kpi[i].metric(f"Lote {lote}", f"{qtd}")
        
        st.divider()

        with st.container(border=True):
            st.markdown("#### 🔍 Filtros e Edição")
            c_filtro1, c_filtro2, c_filtro3 = st.columns(3)
            
            # Filtros
            opcoes_status = df_raw['status'].unique().tolist()
            filtro_status = c_filtro1.multiselect("Status:", options=opcoes_status)
            
            opcoes_lote = df_raw['lote'].unique().tolist()
            filtro_lote = c_filtro2.multiselect("Lote:", options=opcoes_lote)
            
            filtro_prenhez = c_filtro3.radio("Situação:", ["Todos", "Prenhes", "Vazias"], horizontal=True)
            
            # Seleção de Colunas
            colunas_padrao = ["id", "nome", "status", "lote", "nasc", "prenhez", "dt_parto"]
            cols_presentes = list(df_raw.columns)
            defaults_validos = [c for c in colunas_padrao if c in cols_presentes]
            
            cols_selecionadas = st.multiselect("Colunas Visíveis:", options=cols_presentes, default=defaults_validos)

        # Aplica Filtros
        df_view = df_raw.copy()
        if filtro_status: df_view = df_view[df_view['status'].isin(filtro_status)]
        if filtro_lote: df_view = df_view[df_view['lote'].isin(filtro_lote)]
        if filtro_prenhez == "Prenhes": df_view = df_view[df_view['prenhez'] == True]
        elif filtro_prenhez == "Vazias": df_view = df_view[df_view['prenhez'] == False]

        # --- LÓGICA DE ORDENAÇÃO VISUAL (FIXAR ESQUERDA) ---
        # Aqui garantimos que ID e Nome sejam SEMPRE os primeiros
        cols_visual = []
        prioridade = ["id", "nome", "status"]
        
        # 1. Adiciona as prioritárias primeiro (se estiverem selecionadas)
        for p in prioridade:
            if p in cols_selecionadas:
                cols_visual.append(p)
        
        # 2. Adiciona o resto depois
        for c in cols_selecionadas:
            if c not in prioridade:
                cols_visual.append(c)

        # Conversão de datas para o editor
        for col in ['dt_parto', 'dt_insem', 'nasc']:
            if col in df_view.columns: 
                df_view[col] = pd.to_datetime(df_view[col], errors='coerce')

        # Listagem de Mães para o Dropdown
        lista_maes = df_raw[df_raw['sexo'] == 'Fêmea']['id'].unique().tolist()
        lista_maes.insert(0, None)

        st.caption(f"Listando {len(df_view)} animais")
        
        # EDITOR BLINDADO
        df_editado = st.data_editor(
            df_view[cols_visual], # Usa a lista ordenada visualmente
            column_config={
                "doc_id": None,
                "id": st.column_config.TextColumn("Brinco (ID)", required=True, width="small"), # Brinco fixo pequeno
                "nome": st.column_config.TextColumn("Nome", required=True),
                "status": st.column_config.SelectboxColumn("Status", options=["Lactação", "Seca", "Bezerro", "Novilha", "Garrote", "Touro"]),
                "lote": st.column_config.SelectboxColumn("Lote", options=["A", "B", "C", "Maternidade", "Berçário", "Geral", "Recria", "Engorda"]),
                "sexo": st.column_config.SelectboxColumn("Sexo", options=["Fêmea", "Macho"]),
                "mae_id": st.column_config.SelectboxColumn("Mãe", options=lista_maes),
                "dt_parto": st.column_config.DateColumn("Último Parto", format="DD/MM/YYYY"),
                "dt_insem": st.column_config.DateColumn("Insem", format="DD/MM/YYYY"),
                "nasc": st.column_config.DateColumn("Nascimento", format="DD/MM/YYYY"),
                "prenhez": st.column_config.CheckboxColumn("Prenhe?"),
                "colostro": st.column_config.CheckboxColumn("Colostro?")
            },
            use_container_width=True, 
            num_rows="dynamic", 
            hide_index=True,
            key="editor_rebanho_fixo"
        )

        if st.button("💾 Salvar Alterações na Tabela"):
            recs = df_editado.to_dict('records')
            # Tratamento de datas antes de enviar pro Firebase
            for r in recs:
                for date_col in ['dt_parto', 'dt_insem', 'nasc']:
                    val = r.get(date_col)
                    if pd.isnull(val):
                        r[date_col] = None
                    elif isinstance(val, (pd.Timestamp, datetime.date, datetime.datetime)):
                        r[date_col] = val.strftime('%Y-%m-%d')
            
            salvar_lote_dataframe("animais", recs)
            st.success("Tabela atualizada!")

    st.divider()
    # --- VENDA ---
    with st.expander("Realizar Venda (Baixa no Estoque)"):
        # (Código de venda permanece igual ao anterior...)
        animais_venda = [a for a in st.session_state.db["animais"] if a['status'] != 'Bezerro']
        if animais_venda:
            ops_venda = {a['id']: f"{a['nome']} ({a['status']})" for a in animais_venda}
            c_v1, c_v2, c_v3 = st.columns(3)
            v_animal_id = c_v1.selectbox("Animal:", list(ops_venda.keys()), format_func=lambda x: f"{x} - {ops_venda[x]}")
            v_valor = c_v2.number_input("Valor (R$):", min_value=0.0, step=100.0)
            v_motivo = c_v3.text_input("Motivo", "Descarte")
            
            if st.button("CONFIRMAR VENDA", type="primary"):
                animal_obj = next((a for a in animais_venda if a['id'] == v_animal_id), None)
                if animal_obj:
                    adicionar_item("financeiro", {
                        "data": str(datetime.date.today()), "cat": "Venda de Animais", 
                        "desc": f"Venda {ops_venda[v_animal_id]} - {v_motivo}", "valor": v_valor, 
                        "tipo": "Receita", "animal": v_animal_id
                    })
                    deletar_item("animais", animal_obj['doc_id'])
                    st.success(f"Vendido!")
                    st.rerun()
# ==============================================================================
# MÓDULO 8: CALENDÁRIO & AGENDA
# ==============================================================================
elif menu == "📅 Calendário & Agenda":
    st.title("📅 Calendário de Manejo")
    
    def gerar_eventos_futuros(db_animais):
        eventos = []
        hoje = datetime.date.today()
        for animal in db_animais:
            dt_insem = datetime.datetime.strptime(animal['dt_insem'], "%Y-%m-%d").date() if animal.get('dt_insem') else None
            dt_parto = datetime.datetime.strptime(animal['dt_parto'], "%Y-%m-%d").date() if animal.get('dt_parto') else None
            
            if animal.get('prenhez') and dt_insem:
                data_parto = dt_insem + timedelta(days=GESTACAO)
                data_secagem = data_parto - timedelta(days=DIAS_SECAGEM)
                eventos.append({"data": data_parto, "tipo": "Parto", "animal": animal['nome'], "cor": "green", "icon": "👶"})
                eventos.append({"data": data_secagem, "tipo": "Secagem", "animal": animal['nome'], "cor": "orange", "icon": "🍂"})
            
            if dt_insem and not animal.get('prenhez'):
                data_toque = dt_insem + timedelta(days=DIAS_DIAGNOSTICO)
                if data_toque >= hoje - timedelta(days=5):
                    eventos.append({"data": data_toque, "tipo": "Toque/Diag.", "animal": animal['nome'], "cor": "blue", "icon": "🩺"})
            
            if dt_parto and not animal.get('prenhez') and not dt_insem:
                data_liberacao = dt_parto + timedelta(days=DIAS_PVE)
                if data_liberacao >= hoje - timedelta(days=30):
                    eventos.append({"data": data_liberacao, "tipo": "Liberada Insem.", "animal": animal['nome'], "cor": "red", "icon": "💉"})
        return eventos

    lista_eventos = gerar_eventos_futuros(st.session_state.db["animais"])
    df_eventos = pd.DataFrame(lista_eventos)
    
    c_nav1, c_nav2, c_nav3 = st.columns([1, 2, 1])
    if 'cal_ano' not in st.session_state: st.session_state.cal_ano = datetime.date.today().year
    if 'cal_mes' not in st.session_state: st.session_state.cal_mes = datetime.date.today().month

    with c_nav1:
        if st.button("◀ Mês Anterior"):
            st.session_state.cal_mes -= 1
            if st.session_state.cal_mes == 0:
                st.session_state.cal_mes = 12
                st.session_state.cal_ano -= 1
    with c_nav3:
        if st.button("Próximo Mês ▶"):
            st.session_state.cal_mes += 1
            if st.session_state.cal_mes == 13:
                st.session_state.cal_mes = 1
                st.session_state.cal_ano += 1
    with c_nav2:
        nome_mes = calendar.month_name[st.session_state.cal_mes]
        st.markdown(f"<h3 style='text-align: center;'>{nome_mes} {st.session_state.cal_ano}</h3>", unsafe_allow_html=True)

    st.divider()
    col_agenda, col_grid = st.columns([1, 3])
    
    with col_agenda:
        st.markdown("#### 🔔 Próximos 30 Dias")
        hoje = datetime.date.today()
        limite = hoje + timedelta(days=30)
        if not df_eventos.empty:
            mask_prox = (df_eventos['data'] >= hoje) & (df_eventos['data'] <= limite)
            df_prox = df_eventos[mask_prox].sort_values('data')
            if not df_prox.empty:
                for _, row in df_prox.iterrows():
                    delta_dias = (row['data'] - hoje).days
                    texto_data = "Hoje!" if delta_dias == 0 else f"em {delta_dias} dias"
                    st.success(f"**{row['data'].strftime('%d/%m')}** ({texto_data})\n\n{row['icon']} {row['tipo']}: **{row['animal']}**")
            else:
                st.caption("Nenhum evento crítico.")
        else:
            st.caption("Sem eventos.")

    with col_grid:
        cal = calendar.monthcalendar(st.session_state.cal_ano, st.session_state.cal_mes)
        dias_semana = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        cols = st.columns(7)
        for i, dia in enumerate(dias_semana):
            cols[i].markdown(f"**{dia}**")
        
        for semana in cal:
            cols = st.columns(7)
            for i, dia in enumerate(semana):
                with cols[i]:
                    if dia == 0:
                        st.write(" ")
                    else:
                        with st.container(border=True):
                            if dia == hoje.day and st.session_state.cal_mes == hoje.month and st.session_state.cal_ano == hoje.year:
                                st.markdown(f":red[**{dia}**]")
                            else:
                                st.markdown(f"**{dia}**")
                            
                            data_atual_loop = datetime.date(st.session_state.cal_ano, st.session_state.cal_mes, dia)
                            if not df_eventos.empty:
                                eventos_dia = df_eventos[df_eventos['data'] == data_atual_loop]
                                for _, ev in eventos_dia.iterrows():
                                    st.caption(f"{ev['icon']} {ev['animal']}")
                                    st.markdown(f"<span style='color:{ev['cor']}; font-size:0.8em;'>{ev['tipo']}</span>", unsafe_allow_html=True)

# ==============================================================================
# MÓDULO 9: CONFIGURAÇÕES (RESET)
# ==============================================================================
elif menu == "⚙️ Configurações":
    st.title("Configurações do Sistema")
    st.divider()
    
    st.error("### 🧨 Zona de Perigo")
    st.warning("Atenção: Esta ação é irreversível. Todos os animais, financeiro e estoque serão apagados.")
    
    if st.button("APAGAR TUDO (Reset de Fábrica)", type="primary"):

        limpar_banco_completo()



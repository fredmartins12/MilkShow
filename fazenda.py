import streamlit as st
import pandas as pd
import datetime
import time

# --- CONFIGURAÇÕES DA FAZENDA ---
DENSIDADE_LEITE = 1.032
BASE_PASTO_LITROS = 4.0
FATOR_CONVERSAO = 3.0
MAXIMO_POR_REFEICAO = 6.0

# --- BANCO DE DADOS MOCK (Simulando o Firebase) ---
if "db_animais" not in st.session_state:
    st.session_state["db_animais"] = [
        {"id": "105", "nome": "Mimosa", "status": "Lactação", "ult_leite_dia": 35.0, "racao_hoje": 0.0, "freq": 3},
        {"id": "202", "nome": "Estrela", "status": "Lactação", "ult_leite_dia": 18.0, "racao_hoje": 0.0, "freq": 2},
        {"id": "404", "nome": "Velha", "status": "Lactação", "ult_leite_dia": 8.0, "racao_hoje": 0.0, "freq": 1},
        {"id": "500", "nome": "Fujona", "status": "Lactação", "ult_leite_dia": 20.0, "racao_hoje": 0.0, "freq": 2},
    ]

if "db_ordenha" not in st.session_state:
    st.session_state["db_ordenha"] = []

# --- FUNÇÃO AUTOMÁTICA DE TURNO ---
def detectar_turno():
    hora = datetime.datetime.now().hour
    if hora < 11: return 1
    elif hora < 16: return 2
    else: return 3

# --- INTERFACE ---
st.set_page_config(page_title="Operação Fazenda", page_icon="🐄", layout="centered")

# CABEÇALHO
st.title("🐄 Registro de Ordenha")
turno_auto = detectar_turno()

# Barra de Status Rápida
c1, c2 = st.columns(2)
turno_selecionado = c1.selectbox("Turno Atual:", [1, 2, 3], index=(turno_auto-1))
data_hoje = c2.date_input("Data:", datetime.date.today())

st.divider()

# 1. SELEÇÃO DO ANIMAL
animais_ativos = [a for a in st.session_state["db_animais"] if a['status'] == 'Lactação']
opcoes = ["Selecione..."] + [f"{a['id']} - {a['nome']}" for a in animais_ativos]
escolha = st.selectbox("Animal no Tronco:", opcoes)

if escolha != "Selecione...":
    id_sel = escolha.split(" - ")[0]
    vaca = next(a for a in st.session_state["db_animais"] if a['id'] == id_sel)
    
    # --- CÉREBRO DA NUTRIÇÃO ---
    # 1. Meta do dia
    meta_total_dia = (vaca['ult_leite_dia'] - BASE_PASTO_LITROS) / FATOR_CONVERSAO
    if meta_total_dia < 0.5: meta_total_dia = 0.5
    
    # 2. Oportunidades Restantes (Dinâmico)
    # Ex: Se vaca é 2x e estamos no turno 1 -> Restam 2 oportunidades
    ops_restantes = vaca['freq'] - (turno_selecionado - 1)
    if ops_restantes < 1: ops_restantes = 1 # Proteção contra turno extra
    
    # 3. Saldo
    saldo = meta_total_dia - vaca['racao_hoje']
    if saldo < 0: saldo = 0
    
    # 4. Liberação Agora
    sugestao = saldo / ops_restantes
    
    # 5. Trava de Segurança
    alerta = False
    if sugestao > MAXIMO_POR_REFEICAO:
        sugestao = MAXIMO_POR_REFEICAO
        alerta = True

    # --- TELA DE AÇÃO ---
    st.info(f"**Perfil:** {vaca['freq']} ordenhas/dia | **Produção Ontem:** {vaca['ult_leite_dia']} L")
    
    col_racao, col_leite = st.columns(2)
    
    with col_racao:
        st.markdown(f"### 🥣 Ração: {sugestao:.2f} kg")
        if alerta:
            st.warning(f"⚠️ Teto máx ({MAXIMO_POR_REFEICAO}kg) ativado!")
        
        # Simulador da Rosca
        peso_racao_real = st.number_input("Peso Real Ração (Kg):", value=round(sugestao, 2), step=0.1)

    with col_leite:
        st.markdown("### 🥛 Leite")
        peso_balde = st.number_input("Peso Balde (Kg):", min_value=0.0, step=0.1)
        litros = peso_balde / DENSIDADE_LEITE
        st.caption(f"= {litros:.2f} Litros")

    # BOTÃO GRANDE DE SALVAR
    if st.button("✅ CONFIRMAR E SALVAR", type="primary", use_container_width=True):
        if peso_balde > 0:
            st.session_state["db_ordenha"].append({
                "data": str(data_hoje),
                "turno": turno_selecionado,
                "id": id_sel,
                "nome": vaca['nome'],
                "leite": litros,
                "racao": peso_racao_real
            })
            # Atualiza o 'comeu hoje' da vaca na memória
            vaca['racao_hoje'] += peso_racao_real
            
            st.success(f"Registro salvo para {vaca['nome']}!")
            time.sleep(1)
            st.rerun()

# Histórico Recente (Rodapé)
if st.session_state["db_ordenha"]:
    st.markdown("---")
    st.caption("Últimos registros desta sessão:")
    df = pd.DataFrame(st.session_state["db_ordenha"])
    st.dataframe(df.tail(3), hide_index=True)
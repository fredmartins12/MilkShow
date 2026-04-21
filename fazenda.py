"""
fazenda.py — App de Campo (Mobile-friendly)
Registro de ordenha por turno com sincronização ao Firebase.
"""
import streamlit as st
import pandas as pd
import datetime
import time

from utils import (
    init_firebase, carregar_dados, apply_theme,
    adicionar_item, atualizar_item,
    DENSIDADE_LEITE, MAXIMO_POR_REFEICAO, calcular_meta_racao,
)

st.set_page_config(
    page_title="MilkShow Campo",
    page_icon="🐄",
    layout="centered",
    initial_sidebar_state="collapsed",
)
apply_theme()

# ── PWA meta tags + pré-selecionar animal via URL param ─────────────
import streamlit.components.v1 as _comp
_comp.html("""
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#070e08">
<link rel="manifest" href="/app/static/manifest.json">
""", height=0)

# ── Firebase ─────────────────────────────────
try:
    init_firebase()
    carregar_dados()
    firebase_ok = True
except Exception:
    firebase_ok = False
    # Fallback: banco em memória para demonstração
    if "db" not in st.session_state:
        st.session_state.db = {
            "animais": [
                {"id":"105","nome":"Mimosa","status":"Lactação","ult_leite_dia":35.0,"racao_hoje":0.0,"freq":3,"doc_id":"mock_105"},
                {"id":"202","nome":"Estrela","status":"Lactação","ult_leite_dia":18.0,"racao_hoje":0.0,"freq":2,"doc_id":"mock_202"},
                {"id":"404","nome":"Velha",  "status":"Lactação","ult_leite_dia": 8.0,"racao_hoje":0.0,"freq":1,"doc_id":"mock_404"},
                {"id":"500","nome":"Fujona", "status":"Lactação","ult_leite_dia":20.0,"racao_hoje":0.0,"freq":2,"doc_id":"mock_500"},
            ],
            "producao": [],
        }

# ── Turno automático ──────────────────────────
def detectar_turno():
    h = datetime.datetime.now().hour
    if h < 11: return 1
    if h < 16: return 2
    return 3

TURNO_LABELS = {1: "🌞 Manhã", 2: "🌤️ Tarde", 3: "🌙 Noite"}

# ── Header ───────────────────────────────────
st.markdown(
    "<h2 style='text-align:center; color:#a5d6a7;'>🐄 Registro de Ordenha</h2>",
    unsafe_allow_html=True,
)

if not firebase_ok:
    st.warning("⚠️ Sem conexão Firebase — operando em modo local (dados NÃO serão salvos na nuvem).")

# ── Controles do cabeçalho ────────────────────
c1, c2 = st.columns(2)
turno_auto = detectar_turno()
turno_sel  = c1.selectbox(
    "Turno:", [1, 2, 3],
    index=turno_auto - 1,
    format_func=lambda x: TURNO_LABELS[x],
)
data_hoje = c2.date_input("Data:", datetime.date.today())
str_data  = str(data_hoje)

st.divider()

# ── Produção já registrada hoje ───────────────
df_prod_hoje = pd.DataFrame()
df_prod_all  = pd.DataFrame(st.session_state.db.get("producao", []))
if not df_prod_all.empty:
    df_prod_all['data'] = df_prod_all['data'].astype(str)
    df_prod_hoje = df_prod_all[df_prod_all['data'] == str_data]

# ── Seleção do animal ─────────────────────────
vacas_lact = [a for a in st.session_state.db.get("animais", []) if a.get('status') == 'Lactação']
if not vacas_lact:
    st.error("Nenhuma vaca em lactação cadastrada. Acesse o Rebanho Geral para cadastrar.")
    st.stop()

opcoes = ["Selecione..."] + [f"{a['id']} — {a['nome']}" for a in vacas_lact]
escolha = st.selectbox("Animal no Tronco:", opcoes)

if escolha == "Selecione...":
    # ── Mini resumo do dia ─────────────────────
    if not df_prod_hoje.empty:
        st.divider()
        st.markdown("#### Resumo do dia")
        total_leite_dia = df_prod_hoje['leite'].sum()
        total_racao_dia = df_prod_hoje['racao'].sum()
        vacas_feitas    = df_prod_hoje['id_animal'].nunique()
        k1, k2, k3 = st.columns(3)
        k1.metric("Vacas Ordenhadas", f"{vacas_feitas}/{len(vacas_lact)}")
        k2.metric("Leite Total",      f"{total_leite_dia:.1f} L")
        k3.metric("Ração Total",      f"{total_racao_dia:.1f} kg")
    st.stop()

# ── Dados da vaca selecionada ─────────────────
id_sel = escolha.split(" — ")[0]
vaca   = next(a for a in vacas_lact if a['id'] == id_sel)

# Produção de ontem (para calcular meta de ração)
prod_ontem = 15.0
if not df_prod_all.empty:
    ontem_str = str(data_hoje - datetime.timedelta(days=1))
    reg_ont   = df_prod_all[
        (df_prod_all['data'] == ontem_str) & (df_prod_all['id_animal'] == id_sel)
    ]
    if not reg_ont.empty:
        prod_ontem = float(reg_ont['leite'].sum())

# Ração consumida hoje por esta vaca
racao_hoje_vaca = 0.0
if not df_prod_hoje.empty:
    reg_hj = df_prod_hoje[df_prod_hoje['id_animal'] == id_sel]
    if not reg_hj.empty:
        racao_hoje_vaca = float(reg_hj['racao'].sum())

# ── Cálculo de nutrição ────────────────────────
meta_total_dia = calcular_meta_racao(prod_ontem)
# Conta quantas ordenhas já foram feitas hoje para ESTA vaca
turnos_feitos = 0
if not df_prod_hoje.empty:
    turnos_feitos = int((df_prod_hoje['id_animal'] == id_sel).sum())
ops_restantes = max(vaca.get('freq', 2) - turnos_feitos, 1)
saldo          = max(meta_total_dia - racao_hoje_vaca, 0)
sugestao       = saldo / ops_restantes
alerta_max     = False
if sugestao > MAXIMO_POR_REFEICAO:
    sugestao   = MAXIMO_POR_REFEICAO
    alerta_max = True

# ── Perfil da vaca ────────────────────────────
with st.container(border=True):
    st.info(
        f"**{vaca['nome']}** (#{vaca['id']}) · "
        f"{vaca.get('freq', 2)}x/dia · "
        f"Ontem: **{prod_ontem:.1f} L**"
    )

# ── Inputs de ação ───────────────────────────
col_r, col_l = st.columns(2)

with col_r:
    with st.container(border=True):
        st.markdown(f"### 🥣 Ração Sugerida")
        st.markdown(
            f"<h2 style='color:#a5d6a7; margin:0;'>{sugestao:.2f} kg</h2>",
            unsafe_allow_html=True,
        )
        if alerta_max:
            st.warning(f"⚠️ Teto máx. ({MAXIMO_POR_REFEICAO} kg)")
        st.caption(f"Meta dia: {meta_total_dia:.1f} kg · Consumido: {racao_hoje_vaca:.1f} kg")
        peso_racao = st.number_input(
            "Peso Real (kg):", value=round(sugestao, 2), step=0.1, min_value=0.0,
        )

with col_l:
    with st.container(border=True):
        st.markdown("### 🥛 Leite")
        peso_balde = st.number_input("Peso do Balde (kg):", min_value=0.0, step=0.1)
        litros     = peso_balde / DENSIDADE_LEITE
        st.markdown(
            f"<h3 style='color:#a5d6a7; margin:4px 0;'>= {litros:.2f} L</h3>",
            unsafe_allow_html=True,
        )

st.divider()

# ── Botão de salvar ───────────────────────────
if st.button("✅ CONFIRMAR E SALVAR", type="primary", use_container_width=True):
    if peso_balde > 0:
        registro = {
            "data":        str_data,
            "turno":       turno_sel,
            "id_animal":   id_sel,
            "nome_animal": vaca['nome'],
            "leite":       round(litros, 3),
            "racao":       round(peso_racao, 2),
        }
        if firebase_ok:
            adicionar_item("producao", registro)
        else:
            # Fallback local
            st.session_state.db["producao"].append(registro)

        st.success(f"✅ Salvo! {vaca['nome']} — {litros:.2f} L · {peso_racao:.2f} kg ração")
        time.sleep(1)
        st.rerun()
    else:
        st.error("Informe o peso do balde antes de salvar.")

# ── Histórico do dia ──────────────────────────
if not df_prod_hoje.empty:
    st.divider()
    st.caption("Últimos registros de hoje:")
    df_show = df_prod_hoje[['turno','nome_animal','leite','racao']].copy()
    df_show['turno'] = df_show['turno'].map(TURNO_LABELS)
    df_show.columns = ['Turno', 'Animal', 'Leite (L)', 'Ração (kg)']
    st.dataframe(
        df_show.tail(5).style.format({"Leite (L)": "{:.2f}", "Ração (kg)": "{:.2f}"}),
        hide_index=True,
        use_container_width=True,
    )

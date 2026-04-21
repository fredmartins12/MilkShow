"""
Controle de Ordenha — Monitoramento diário (dados do app de campo fazenda.py).
"""
import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta
import plotly.express as px

from utils import (
    init_firebase, carregar_dados, apply_theme, page_banner,
    calcular_meta_racao, exportar_excel,
)

st.set_page_config(page_title="MilkShow | Ordenha", layout="wide", page_icon="🥛")
apply_theme()
init_firebase()
carregar_dados()

st.sidebar.markdown(
    '<div class="sidebar-title">MilkShow</div>'
    '<div class="sidebar-sub">Controle de Ordenha</div>',
    unsafe_allow_html=True,
)
page_banner("", "Controle Diário de Ordenha", "Monitoramento em tempo real — integrado ao app de campo")

# ── Filtro de data ────────────────────────────
col_d1, col_d2 = st.columns([1, 3])
data_analise = col_d1.date_input("Data:", datetime.date.today())
str_data     = str(data_analise)

# ── Preparação dos dados ──────────────────────
vacas_lact = [v for v in st.session_state.db.get("animais", []) if v.get('status') == 'Lactação']
df_prod    = pd.DataFrame(st.session_state.db.get("producao", []))

df_hoje  = pd.DataFrame()
df_ontem = pd.DataFrame()
if not df_prod.empty:
    df_prod['data'] = df_prod['data'].astype(str)
    df_hoje  = df_prod[df_prod['data'] == str_data]
    df_ontem = df_prod[df_prod['data'] == str(data_analise - timedelta(days=1))]

total_leite     = float(df_hoje['leite'].sum())  if not df_hoje.empty else 0.0
total_racao     = float(df_hoje['racao'].sum())  if not df_hoje.empty else 0.0
vacas_ordenhadas = len(df_hoje['id_animal'].unique()) if not df_hoje.empty else 0
total_esperado  = len(vacas_lact)

# ── KPIs ─────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("Progresso",      f"{vacas_ordenhadas}/{total_esperado} vacas")
k2.metric("Leite Captado",  f"{total_leite:.1f} L")
k3.metric("Ração Ofertada", f"{total_racao:.1f} kg")
k4.metric("Eficiência",
          f"{int(vacas_ordenhadas/total_esperado*100)}%" if total_esperado > 0 else "—")

prog = vacas_ordenhadas / total_esperado if total_esperado > 0 else 0
st.progress(prog, text=f"Cobertura do Rebanho: {int(prog*100)}%")
st.divider()

# ── Gráfico de turno ─────────────────────────
if not df_hoje.empty and 'turno' in df_hoje.columns:
    por_turno = df_hoje.groupby('turno')['leite'].sum().reset_index()
    por_turno['Turno'] = por_turno['turno'].map({1: 'Manhã', 2: 'Tarde', 3: 'Noite'})
    fig = px.bar(por_turno, x='Turno', y='leite',
                 color_discrete_sequence=['#43a047'],
                 labels={'leite': 'Litros', 'Turno': ''})
    fig.update_layout(
        plot_bgcolor='rgba(255,255,255,0.03)', paper_bgcolor='rgba(255,255,255,0.03)',
        font_color='#94a3b8',
        xaxis=dict(gridcolor='rgba(255,255,255,0.06)'),
        yaxis=dict(gridcolor='rgba(255,255,255,0.06)'),
        margin=dict(l=0, r=0, t=10, b=0), height=180,
        showlegend=False,
    )
    col_g1, _ = st.columns([1, 2])
    with col_g1:
        st.subheader("Produção por Turno")
        st.plotly_chart(fig, use_container_width=True)
    st.divider()

# ── Cards por vaca ───────────────────────────
if not vacas_lact:
    st.info("Nenhuma vaca em lactação cadastrada.")
else:
    st.markdown("### Detalhamento Individual")
    for vaca in vacas_lact:
        vid     = vaca['id']
        freq_esp = int(vaca.get('freq', 2))

        dados_v = df_hoje[df_hoje['id_animal'] == vid] if not df_hoje.empty else pd.DataFrame()
        qtd_real = len(dados_v)
        leite_m  = float(dados_v[dados_v['turno'] == 1]['leite'].sum()) if not dados_v.empty else 0
        leite_t  = float(dados_v[dados_v['turno'] == 2]['leite'].sum()) if not dados_v.empty else 0
        leite_n  = float(dados_v[dados_v['turno'] == 3]['leite'].sum()) if not dados_v.empty else 0
        leite_tot = float(dados_v['leite'].sum()) if not dados_v.empty else 0
        racao_c  = float(dados_v['racao'].sum()) if not dados_v.empty else 0

        # Meta de ração
        prod_ant = 15.0
        if not df_ontem.empty:
            reg_ont = df_ontem[df_ontem['id_animal'] == vid]
            if not reg_ont.empty:
                prod_ant = float(reg_ont['leite'].sum())
        meta_r = calcular_meta_racao(prod_ant)
        pct_n  = min(racao_c / meta_r, 1.0) if meta_r > 0 else 0

        # Status
        if qtd_real == 0:
            icon_s, txt_s, cor_s = "", "Pendente",     "#ef4444"
        elif qtd_real < freq_esp:
            icon_s, txt_s, cor_s = "", "Em andamento", "#f59e0b"
        else:
            icon_s, txt_s, cor_s = "", "Finalizado",   "#10b981"

        with st.container(border=True):
            c_id, c_prod, c_nutri = st.columns([1.2, 2, 2])

            with c_id:
                st.markdown(f"**{vaca['nome']}**")
                st.caption(f"Brinco: {vid}")
                st.markdown(
                    f"<span style='color:{cor_s}; font-weight:600;'>"
                    f"{icon_s} {qtd_real}/{freq_esp} — {txt_s}</span>",
                    unsafe_allow_html=True,
                )

            with c_prod:
                t1, t2, t3 = st.columns(3)
                t1.metric("Manhã",  f"{leite_m:.1f} L" if leite_m else "—")
                t2.metric("Tarde",  f"{leite_t:.1f} L" if leite_t else "—")
                t3.metric("Noite",  f"{leite_n:.1f} L" if leite_n else "—")
                st.markdown(f"**Total: {leite_tot:.1f} L**")

            with c_nutri:
                cor_b = "#1b5e20" if pct_n >= 0.9 else ("#ff9800" if pct_n >= 0.5 else "#c62828")
                st.markdown(f"**Nutrição:** {racao_c:.1f} kg / {meta_r:.1f} kg meta")
                st.markdown(
                    f"<div style='background:#1c3022; border-radius:6px; height:12px; margin:4px 0;'>"
                    f"<div style='background:{cor_b}; width:{int(pct_n*100)}%; height:100%; "
                    f"border-radius:6px; transition:width 0.3s;'></div></div>"
                    f"<span style='font-size:0.78em; color:#81c784;'>{int(pct_n*100)}% da dieta</span>",
                    unsafe_allow_html=True,
                )

# ── Exportação ───────────────────────────────
if not df_hoje.empty:
    st.divider()
    xls = exportar_excel({
        "Ordenha": df_hoje.drop(columns=['doc_id'], errors='ignore')
    })
    st.download_button(
        f"Exportar Ordenha de {data_analise.strftime('%d/%m/%Y')} (Excel)",
        data=xls,
        file_name=f"ordenha_{str_data}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

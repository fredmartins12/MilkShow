"""
BI & Inteligência — KPIs, dashboards, curva de lactação e exportação.
"""
import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta
import numpy as np

from utils import (
    init_firebase, carregar_dados, apply_theme, page_banner,
    calcular_bi, get_config, get_custo_racao,
    PRECO_PADRAO_LEITE, CATEGORIAS_DESPESA,
    exportar_excel, exportar_pdf_simples, sidebar_mini_resumo,
)

st.set_page_config(page_title="MilkShow | BI", layout="wide", page_icon="📊")
apply_theme()
init_firebase()
carregar_dados()

st.sidebar.markdown(
    '<div class="sidebar-title">MilkShow</div>'
    '<div class="sidebar-sub">BI & Inteligência</div>',
    unsafe_allow_html=True,
)
sidebar_mini_resumo()
page_banner("", "Business Intelligence", "KPIs, dashboards e análises de performance")

# ── Data prep ────────────────────────────────
df_prod = pd.DataFrame(st.session_state.db["producao"])
df_fin  = pd.DataFrame(st.session_state.db["financeiro"])

if not df_prod.empty:
    df_prod['data'] = pd.to_datetime(df_prod['data'], errors='coerce').dt.date
if not df_fin.empty:
    df_fin['data'] = pd.to_datetime(df_fin['data'], errors='coerce').dt.date

tab_macro, tab_micro, tab_tabela, tab_rankings, tab_lactacao, tab_forecast, tab_heatmap = st.tabs([
    "Dashboard Geral",
    "Raio-X Individual",
    "Relatório Comparativo",
    "Rankings",
    "Curva de Lactação",
    "Previsão",
    "Heatmap",
])

# ══════════════════════════════════════════════
# TAB 1 — MACRO
# ══════════════════════════════════════════════
with tab_macro:
    c1, c2 = st.columns(2)
    ini = c1.date_input("Início da análise", datetime.date.today() - timedelta(days=30))
    fim = c2.date_input("Fim da análise",    datetime.date.today())

    df_prod_filt = df_prod.copy()
    if not df_prod.empty:
        df_prod_filt = df_prod[(df_prod['data'] >= ini) & (df_prod['data'] <= fim)]

    kpis = calcular_bi(df_prod_filt, df_fin, ini, fim)

    if kpis:
        usando_estimativa = kpis['preco_medio'] == 0
        preco_leite = float(get_config('preco_leite', PRECO_PADRAO_LEITE))

        if usando_estimativa:
            kpis['receita'] = kpis['producao_total'] * preco_leite
            kpis['lucro']   = kpis['receita'] - kpis['custo_total']

        if usando_estimativa:
            st.warning(
                f"Nenhuma Venda de Leite vinculada neste período. "
                f"Usando preço configurado de R$ {preco_leite:.2f}/L."
            )

        st.markdown(f"#### Resultados: {ini.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}")
        k1, k2, k3, k4, k5 = st.columns(5)
        preco_d = kpis['preco_medio'] if kpis['preco_medio'] > 0 else preco_leite
        k1.metric("Produção Total",    f"{kpis['producao_total']:.0f} L")
        k2.metric("Preço Médio/L",     f"R$ {preco_d:.2f}",
                  delta="Estimado" if usando_estimativa else "Realizado",
                  delta_color="off" if usando_estimativa else "normal")
        k3.metric("Custo por Litro",   f"R$ {kpis['custo_litro']:.2f}", delta_color="inverse")
        k4.metric("Receita Total",     f"R$ {kpis['receita']:,.2f}")
        k5.metric("Lucro Operacional", f"R$ {kpis['lucro']:,.2f}",
                  delta_color="normal" if kpis['lucro'] > 0 else "inverse")

        st.markdown(f"*Custo unitário da ração: R$ {kpis['custo_racao_kg']:.2f}/kg (do estoque)*")
        st.divider()

        g1, g2 = st.columns(2)
        with g1:
            st.subheader("Produção Diária")
            if not df_prod_filt.empty:
                diario = df_prod_filt.groupby("data")['leite'].sum().reset_index()
                fig = px.bar(diario, x="data", y="leite",
                             color_discrete_sequence=['#3b82f6'],
                             labels={'leite': 'Litros', 'data': ''})
                fig.update_layout(
                    plot_bgcolor='rgba(255,255,255,0.03)', paper_bgcolor='rgba(0,0,0,0)',
                    font_color='#94a3b8', showlegend=False,
                    xaxis=dict(gridcolor='rgba(255,255,255,0.06)'),
                    yaxis=dict(gridcolor='rgba(255,255,255,0.06)'),
                    margin=dict(l=0, r=0, t=0, b=0), height=260,
                )
                st.plotly_chart(fig, use_container_width=True)

        with g2:
            st.subheader("Composição de Custos")
            if not df_fin.empty:
                mask = (df_fin['cat'].isin(CATEGORIAS_DESPESA) &
                        (df_fin['data'] >= ini) & (df_fin['data'] <= fim))
                df_pizza = df_fin[mask].groupby('cat')['valor'].sum().reset_index()
                df_pizza.loc[len(df_pizza)] = ['Nutrição (Ração)', kpis['custo_racao']]
                # Paleta diversificada para distinguir fatias facilmente
                CORES_PIZZA = ['#e53935','#fb8c00','#fdd835','#43a047','#1e88e5','#8e24aa',
                                '#00acc1','#f06292','#26a69a','#ff7043']
                fig2 = px.pie(df_pizza, values='valor', names='cat', hole=0.5,
                              color_discrete_sequence=CORES_PIZZA)
                fig2.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                    font_color='#e0e0e0',
                    legend=dict(font=dict(color='#e0e0e0', size=11)),
                    margin=dict(l=0, r=0, t=0, b=0), height=280,
                )
                fig2.update_traces(
                    textfont_color='white',
                    textfont_size=12,
                    pull=[0.03]*len(df_pizza),
                    marker=dict(line=dict(color='#0a1810', width=2)),
                )
                st.plotly_chart(fig2, use_container_width=True)

        # ── Histórico Mensal de Custo/L ───────
        st.divider()
        st.subheader("Evolução Mensal — Custo/L vs Preço/L")
        st.caption("Acompanhe se sua margem está melhorando ou piorando mês a mês.")

        if not df_prod.empty:
            # Agrupa produção por mês
            df_hist = df_prod.copy()
            df_hist['mes'] = pd.to_datetime(df_hist['data'].astype(str)).dt.to_period('M')
            meses = sorted(df_hist['mes'].unique())[-12:]  # últimos 12 meses

            hist_rows = []
            custo_kg_h = get_custo_racao()
            preco_h    = float(get_config('preco_leite', PRECO_PADRAO_LEITE))

            for mes in meses:
                df_m = df_hist[df_hist['mes'] == mes]
                litros_m = float(df_m['leite'].sum())
                racao_m  = float(df_m['racao'].sum())
                if litros_m == 0:
                    continue

                # Financeiro do mês
                mes_str_ini = str(mes.start_time.date())
                mes_str_fim = str(mes.end_time.date())
                rec_m = des_m = 0.0
                if not df_fin.empty:
                    mask_m = (df_fin['data'] >= mes.start_time.date()) & (df_fin['data'] <= mes.end_time.date())
                    df_fm  = df_fin[mask_m]
                    rec_m  = float(df_fm[df_fm['cat'] == 'Venda de Leite']['valor'].sum())
                    des_m  = float(df_fm[df_fm['cat'].isin(CATEGORIAS_DESPESA)]['valor'].sum())

                custo_r = racao_m * custo_kg_h
                custo_t = custo_r + des_m
                preco_m = rec_m / litros_m if rec_m > 0 else preco_h
                custo_l = custo_t / litros_m
                lucro_l = preco_m - custo_l

                hist_rows.append({
                    'Mês':        str(mes),
                    'Litros':     litros_m,
                    'Preço/L':    preco_m,
                    'Custo/L':    custo_l,
                    'Lucro/L':    lucro_l,
                })

            if hist_rows:
                df_hg = pd.DataFrame(hist_rows)
                fig_h = go.Figure()
                fig_h.add_trace(go.Scatter(
                    x=df_hg['Mês'], y=df_hg['Preço/L'],
                    name='Preço/L', mode='lines+markers',
                    line=dict(color='#60a5fa', width=2.5),
                    marker=dict(size=6),
                ))
                fig_h.add_trace(go.Scatter(
                    x=df_hg['Mês'], y=df_hg['Custo/L'],
                    name='Custo/L', mode='lines+markers',
                    line=dict(color='#f87171', width=2.5),
                    marker=dict(size=6),
                    fill='tonexty',
                    fillcolor='rgba(248,113,113,0.12)',
                ))
                fig_h.add_trace(go.Bar(
                    x=df_hg['Mês'], y=df_hg['Lucro/L'],
                    name='Lucro/L',
                    marker_color=['#4ade80' if v >= 0 else '#f87171' for v in df_hg['Lucro/L']],
                    opacity=0.6, yaxis='y2',
                ))
                fig_h.update_layout(
                    plot_bgcolor='rgba(255,255,255,0.03)', paper_bgcolor='rgba(0,0,0,0)',
                    font_color='#94a3b8',
                    xaxis=dict(gridcolor='rgba(255,255,255,0.06)'),
                    yaxis=dict(title='R$/L', gridcolor='rgba(255,255,255,0.06)'),
                    yaxis2=dict(overlaying='y', side='right', title='Lucro/L (R$)',
                                gridcolor='rgba(0,0,0,0)'),
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
                    hovermode='x unified',
                    margin=dict(l=0, r=0, t=30, b=0), height=280,
                )
                st.plotly_chart(fig_h, use_container_width=True)
            else:
                st.info("Sem dados suficientes para histórico mensal.")

        # ── Exportação ────────────────────────
        st.divider()
        st.subheader("⬇️ Exportar")
        exp1, exp2 = st.columns(2)
        with exp1:
            if not df_prod_filt.empty:
                xls = exportar_excel({
                    "Producao": df_prod_filt.drop(columns=['doc_id'], errors='ignore'),
                    "Financeiro": df_fin.drop(columns=['doc_id'], errors='ignore') if not df_fin.empty else pd.DataFrame(),
                })
                st.download_button(
                    "Baixar Excel (Produção + Financeiro)",
                    data=xls,
                    file_name=f"milkshow_{ini}_{fim}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
        with exp2:
            if not df_prod_filt.empty:
                resumo_exp = df_prod_filt.groupby("data")['leite'].sum().reset_index()
                resumo_exp.columns = ['Data', 'Litros']
                pdf_bytes = exportar_pdf_simples(
                    f"Produção {ini.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}",
                    resumo_exp
                )
                if pdf_bytes:
                    st.download_button(
                        "Baixar PDF (Resumo de Produção)",
                        data=pdf_bytes,
                        file_name=f"producao_{ini}_{fim}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )
    else:
        st.warning("Sem dados suficientes para o dashboard. Registre produções primeiro.")

# ══════════════════════════════════════════════
# TAB 2 — MICRO
# ══════════════════════════════════════════════
with tab_micro:
    st.markdown("#### Análise Individual por Vaca")
    lista_vacas = [a for a in st.session_state.db["animais"] if a.get('status') in ['Lactação', 'Seca']]

    if not lista_vacas:
        st.info("Nenhuma vaca em lactação ou seca cadastrada.")
    else:
        ops = {a['id']: a['nome'] for a in lista_vacas}
        cr1, cr2, cr3 = st.columns([2, 1, 1])
        vaca_id  = cr1.selectbox("Vaca:", list(ops.keys()), format_func=lambda x: f"{x} — {ops[x]}")
        dt_ini_v = cr2.date_input("De:", datetime.date.today() - timedelta(days=30), key="dti_v")
        dt_fim_v = cr3.date_input("Até:", datetime.date.today(), key="dtf_v")

        if vaca_id and not df_prod.empty:
            mask_v = ((df_prod['id_animal'] == vaca_id) &
                      (df_prod['data'] >= dt_ini_v) &
                      (df_prod['data'] <= dt_fim_v))
            df_vaca = df_prod[mask_v]

            gastos_diretos = 0.0
            if not df_fin.empty and 'animal' in df_fin.columns:
                mask_f = ((df_fin['animal'] == vaca_id) &
                          (df_fin['data'] >= dt_ini_v) &
                          (df_fin['data'] <= dt_fim_v) &
                          (df_fin['cat'].isin(CATEGORIAS_DESPESA)))
                gastos_diretos = float(df_fin[mask_f]['valor'].sum())

            if not df_vaca.empty:
                custo_kg    = get_custo_racao()
                total_leite = float(df_vaca['leite'].sum())
                total_racao = float(df_vaca['racao'].sum())
                preco_base  = float(get_config('preco_leite', PRECO_PADRAO_LEITE))

                # Usa preço real das vendas no período, se disponível
                if not df_fin.empty:
                    vendas_p = df_fin[(df_fin['cat'] == 'Venda de Leite') &
                                      (df_fin['data'] >= dt_ini_v) &
                                      (df_fin['data'] <= dt_fim_v)]
                    litros_todos = df_prod[(df_prod['data'] >= dt_ini_v) &
                                          (df_prod['data'] <= dt_fim_v)]['leite'].sum()
                    if litros_todos > 0 and vendas_p['valor'].sum() > 0:
                        preco_base = float(vendas_p['valor'].sum()) / float(litros_todos)

                receita_est = total_leite * preco_base
                custo_racao = total_racao * custo_kg
                custo_total = custo_racao + gastos_diretos
                margem      = receita_est - custo_total
                custo_litro_v = custo_total / total_leite if total_leite > 0 else 0
                lucro_litro_v = preco_base - custo_litro_v

                m1, m2, m3, m4, m5, m6 = st.columns(6)
                m1.metric("Produção Total",  f"{total_leite:.1f} L")
                m2.metric("Preço/L",         f"R$ {preco_base:.2f}")
                m3.metric("Receita Est.",    f"R$ {receita_est:,.2f}")
                m4.metric("Custo Total",     f"R$ {custo_total:,.2f}")
                m5.metric("Custo/L",         f"R$ {custo_litro_v:.2f}",
                           delta=f"{'acima' if custo_litro_v > preco_base else 'abaixo'} do preço",
                           delta_color="inverse" if custo_litro_v > preco_base else "normal")
                m6.metric("Lucro/L",         f"R$ {lucro_litro_v:.2f}",
                           delta_color="normal" if lucro_litro_v >= 0 else "inverse")

                if custo_litro_v > preco_base:
                    st.error(
                        f"**Prejuízo por litro!** Custo de produção R$ {custo_litro_v:.2f}/L "
                        f"está acima do preço de venda R$ {preco_base:.2f}/L. "
                        f"Prejuízo de **R$ {abs(lucro_litro_v):.2f}** por litro produzido."
                    )
                elif lucro_litro_v < preco_base * 0.15:
                    st.warning(
                        f"Margem apertada: {lucro_litro_v/preco_base*100:.1f}% sobre o preço. "
                        f"Revise custos de ração ou alimentação."
                    )

                col_zoo, col_bez = st.columns([2, 1])
                with col_zoo:
                    st.subheader("Leite vs Ração")
                    df_graf = df_vaca[['data','leite','racao']].sort_values('data')
                    fig = go.Figure()
                    # Área de ração (fundo, eixo direito)
                    fig.add_trace(go.Scatter(
                        x=df_graf['data'], y=df_graf['racao'],
                        name='Ração (kg)', mode='lines',
                        yaxis='y2',
                        line=dict(color='#22c55e', width=1.5),
                        fill='tozeroy',
                        fillcolor='rgba(34,197,94,0.18)',
                    ))
                    # Área de leite (frente, eixo esquerdo)
                    fig.add_trace(go.Scatter(
                        x=df_graf['data'], y=df_graf['leite'],
                        name='Leite (L)', mode='lines+markers',
                        line=dict(color='#60a5fa', width=2.5),
                        fill='tozeroy',
                        fillcolor='rgba(96,165,250,0.22)',
                        marker=dict(size=5, color='#60a5fa',
                                    line=dict(color='#fff', width=1)),
                    ))
                    fig.update_layout(
                        plot_bgcolor='rgba(255,255,255,0.03)',
                        paper_bgcolor='rgba(255,255,255,0.03)',
                        font_color='#94a3b8',
                        xaxis=dict(gridcolor='rgba(255,255,255,0.06)',
                                   showspikes=True, spikecolor='#475569',
                                   spikethickness=1),
                        yaxis=dict(gridcolor='rgba(255,255,255,0.06)',
                                   title='Litros', title_font_color='#60a5fa',
                                   tickfont_color='#60a5fa'),
                        yaxis2=dict(overlaying='y', side='right',
                                    title='kg Ração', title_font_color='#22c55e',
                                    tickfont_color='#22c55e',
                                    gridcolor='rgba(255,255,255,0)'),
                        legend=dict(font=dict(color='#94a3b8'),
                                    orientation='h', yanchor='bottom',
                                    y=1.02, xanchor='right', x=1),
                        hovermode='x unified',
                        margin=dict(l=0, r=0, t=30, b=0), height=260,
                    )
                    st.plotly_chart(fig, use_container_width=True)

                with col_bez:
                    st.subheader("Filhos")
                    bezerros = [b for b in st.session_state.db["animais"]
                                if b.get('mae_id') == vaca_id]
                    if bezerros:
                        for b in bezerros:
                            st.info(f"{b['id']} — {b['nome']} ({b.get('status','')})")
                    else:
                        st.caption("Sem registros de filhos.")

                # Download individual
                xls_v = exportar_excel({
                    "Producao": df_vaca.drop(columns=['doc_id'], errors='ignore')
                })
                st.download_button(
                    "Exportar dados desta vaca (Excel)",
                    data=xls_v,
                    file_name=f"vaca_{vaca_id}_{dt_ini_v}_{dt_fim_v}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            else:
                st.warning("Sem registros de ordenha neste período.")

# ══════════════════════════════════════════════
# TAB 3 — COMPARATIVO
# ══════════════════════════════════════════════
with tab_tabela:
    st.markdown("#### Relatório Comparativo por Animal")
    c_t1, c_t2 = st.columns(2)
    dt_ini_t = c_t1.date_input("Início:", datetime.date.today() - timedelta(days=30), key="dti_t")
    dt_fim_t = c_t2.date_input("Fim:",    datetime.date.today(), key="dtf_t")

    if st.button("Gerar Relatório", type="primary"):
        if not df_prod.empty:
            mask_p = (df_prod['data'] >= dt_ini_t) & (df_prod['data'] <= dt_fim_t)
            df_p   = df_prod[mask_p]
            if not df_p.empty:
                custo_kg  = get_custo_racao()
                preco_ref = float(get_config('preco_leite', PRECO_PADRAO_LEITE))

                resumo = df_p.groupby(['id_animal', 'nome_animal']).agg(
                    Leite_Total   = ('leite',  'sum'),
                    Racao_Total   = ('racao',  'sum'),
                    Dias_Ordenha  = ('data',   'nunique'),
                ).reset_index()
                resumo['Receita_Est']    = resumo['Leite_Total'] * preco_ref
                resumo['Custo_Racao']    = resumo['Racao_Total'] * custo_kg
                resumo['Margem_Bruta']   = resumo['Receita_Est'] - resumo['Custo_Racao']
                resumo['Media_L_Dia']    = resumo['Leite_Total'] / resumo['Dias_Ordenha']

                st.dataframe(
                    resumo.style.format({
                        "Leite_Total":  "{:.1f} L",
                        "Racao_Total":  "{:.1f} kg",
                        "Receita_Est":  "R$ {:.2f}",
                        "Custo_Racao":  "R$ {:.2f}",
                        "Margem_Bruta": "R$ {:.2f}",
                        "Media_L_Dia":  "{:.1f} L/dia",
                    }),
                    use_container_width=True,
                    hide_index=True,
                )

                xls_r = exportar_excel({"Comparativo": resumo})
                st.download_button(
                    "Exportar Relatório (Excel)",
                    data=xls_r,
                    file_name=f"comparativo_{dt_ini_t}_{dt_fim_t}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            else:
                st.warning("Sem dados neste período.")
        else:
            st.warning("Banco de produção vazio.")

# ══════════════════════════════════════════════
# TAB 4 — RANKINGS & ANÁLISES
# ══════════════════════════════════════════════
with tab_rankings:
    st.markdown("#### Rankings & Análises Comparativas")

    r_c1, r_c2, r_c3 = st.columns(3)
    dt_ini_r = r_c1.date_input("Início:", datetime.date.today() - timedelta(days=30), key="dti_r")
    dt_fim_r = r_c2.date_input("Fim:",    datetime.date.today(), key="dtf_r")
    metrica  = r_c3.selectbox("Ordenar por:", [
        "Lucro/L (Mais Lucrativas)",
        "Custo/L (Mais Baratas)",
        "Margem de Lucro (R$)",
        "Produção Total (L)",
        "Eficiência (L/kg ração)",
        "Média Diária (L/dia)",
        "Custo Ração (R$)",
        "Idade (Mais Velhas)",
        "Idade (Mais Novas)",
    ], key="rank_metrica")

    animais_db = st.session_state.db.get("animais", [])

    if df_prod.empty:
        st.info("Sem dados de produção para gerar rankings.")
    else:
        mask_r = (df_prod['data'] >= dt_ini_r) & (df_prod['data'] <= dt_fim_r)
        df_r   = df_prod[mask_r]

        if df_r.empty:
            st.warning("Sem registros neste período.")
        else:
            custo_kg_r  = get_custo_racao()
            preco_ref_r = float(get_config('preco_leite', PRECO_PADRAO_LEITE))

            # Preço real das vendas no período (se houver)
            if not df_fin.empty:
                vendas_r = df_fin[(df_fin['cat'] == 'Venda de Leite') &
                                  (df_fin['data'] >= dt_ini_r) &
                                  (df_fin['data'] <= dt_fim_r)]
                total_l_r = float(df_r['leite'].sum())
                if total_l_r > 0 and vendas_r['valor'].sum() > 0:
                    preco_ref_r = float(vendas_r['valor'].sum()) / total_l_r

            resumo_r = df_r.groupby(['id_animal', 'nome_animal']).agg(
                Leite_Total  = ('leite', 'sum'),
                Racao_Total  = ('racao', 'sum'),
                Dias         = ('data',  'nunique'),
            ).reset_index()
            resumo_r['Receita']     = resumo_r['Leite_Total'] * preco_ref_r
            resumo_r['Custo_Racao'] = resumo_r['Racao_Total'] * custo_kg_r
            resumo_r['Eficiencia']  = resumo_r.apply(
                lambda row: row['Leite_Total'] / row['Racao_Total']
                if row['Racao_Total'] > 0 else 0.0, axis=1
            )
            resumo_r['Media_Dia'] = resumo_r['Leite_Total'] / resumo_r['Dias']

            # ── Custos diretos de veterinário/sanidade por animal ──
            resumo_r['Custo_Vet'] = 0.0
            if not df_fin.empty and 'animal' in df_fin.columns:
                nome_map = resumo_r.set_index('id_animal')['nome_animal'].to_dict()
                for vid, vnome in nome_map.items():
                    mask_vet = (
                        (df_fin['animal'].fillna('').str.lower() == vnome.lower()) &
                        (df_fin['data'] >= dt_ini_r) & (df_fin['data'] <= dt_fim_r) &
                        (df_fin['cat'].isin(CATEGORIAS_DESPESA))
                    )
                    resumo_r.loc[resumo_r['id_animal'] == vid, 'Custo_Vet'] = (
                        float(df_fin[mask_vet]['valor'].sum())
                    )

            # ── Rateio proporcional dos custos fixos (sem animal específico) ──
            custos_fixos_r = 0.0
            if not df_fin.empty:
                mask_fix = (
                    df_fin['cat'].isin(CATEGORIAS_DESPESA) &
                    (df_fin['data'] >= dt_ini_r) & (df_fin['data'] <= dt_fim_r) &
                    (df_fin['animal'].isna() | (df_fin['animal'].fillna('') == ''))
                )
                custos_fixos_r = float(df_fin[mask_fix]['valor'].sum())

            total_prod_r = resumo_r['Leite_Total'].sum()
            resumo_r['Custo_Fixo_Rat'] = resumo_r['Leite_Total'].apply(
                lambda l: (l / total_prod_r * custos_fixos_r) if total_prod_r > 0 else 0.0
            )

            resumo_r['Custo_Total']  = (resumo_r['Custo_Racao'] +
                                        resumo_r['Custo_Vet'] +
                                        resumo_r['Custo_Fixo_Rat'])
            resumo_r['Margem']       = resumo_r['Receita'] - resumo_r['Custo_Total']
            resumo_r['Custo_L']      = resumo_r.apply(
                lambda row: row['Custo_Total'] / row['Leite_Total']
                if row['Leite_Total'] > 0 else 0.0, axis=1
            )
            resumo_r['Lucro_L']      = preco_ref_r - resumo_r['Custo_L']

            # Enriquecer com idade do animal
            hoje_r = datetime.date.today()
            def _calc_idade(id_animal):
                a = next((x for x in animais_db if x.get('id') == id_animal), None)
                if not a or not a.get('nasc'):
                    return None
                try:
                    nasc = datetime.datetime.strptime(str(a['nasc'])[:10], "%Y-%m-%d").date()
                    return (hoje_r - nasc).days / 365.25
                except (ValueError, TypeError):
                    return None

            resumo_r['Idade_Anos'] = resumo_r['id_animal'].apply(_calc_idade)

            # Ordenação conforme seleção
            col_sort, asc_sort = {
                "Lucro/L (Mais Lucrativas)":    ("Lucro_L",     False),
                "Custo/L (Mais Baratas)":        ("Custo_L",     True),
                "Margem de Lucro (R$)":          ("Margem",      False),
                "Produção Total (L)":            ("Leite_Total", False),
                "Eficiência (L/kg ração)":       ("Eficiencia",  False),
                "Média Diária (L/dia)":          ("Media_Dia",   False),
                "Custo Ração (R$)":              ("Custo_Racao", True),
                "Idade (Mais Velhas)":           ("Idade_Anos",  False),
                "Idade (Mais Novas)":            ("Idade_Anos",  True),
            }[metrica]

            if col_sort == "Idade_Anos":
                df_sorted = resumo_r.dropna(subset=["Idade_Anos"]).sort_values(col_sort, ascending=asc_sort)
            else:
                df_sorted = resumo_r.sort_values(col_sort, ascending=asc_sort)

            # ── Cards Top 3 / Bottom 3 ──────────
            col_top, col_bot = st.columns(2)

            def _card_animal(rank, row, cor_borda, icone):
                nome  = row.get('nome_animal', row.get('id_animal', '?'))
                id_a  = row.get('id_animal', '')
                idade = f"{row['Idade_Anos']:.1f} anos" if pd.notna(row.get('Idade_Anos')) else "Idade n/d"
                lucro_l = row.get('Lucro_L', 0)
                cor_lucro = '#4ade80' if lucro_l >= 0 else '#f87171'
                lucro_txt = (f"<b style='color:{cor_lucro};'>R$ {lucro_l:+.2f}/L</b>")
                st.markdown(
                    f"<div style='border-left:4px solid {cor_borda}; background:#0d1f12; "
                    f"border-radius:10px; padding:12px 16px; margin-bottom:10px;'>"
                    f"<span style='font-size:1.2em; font-weight:700; color:{cor_borda};'>"
                    f"{icone} #{rank} — {nome}</span>"
                    f"<span style='color:#aaa; font-size:0.8em; margin-left:8px;'>({id_a})</span><br>"
                    f"<span style='color:#ccc; font-size:0.85em;'>"
                    f"{row['Leite_Total']:.0f} L &nbsp;|&nbsp; "
                    f"Custo R$ {row.get('Custo_L',0):.2f}/L &nbsp;|&nbsp; "
                    f"Lucro {lucro_txt} &nbsp;|&nbsp; "
                    f"{row['Eficiencia']:.2f} L/kg &nbsp;|&nbsp; {idade}"
                    f"</span></div>",
                    unsafe_allow_html=True,
                )

            with col_top:
                st.markdown("##### Top Performers")
                for i, (_, row) in enumerate(df_sorted.head(3).iterrows()):
                    cores = ['#ffd700', '#c0c0c0', '#cd7f32']
                    icons = ['1.','2.','3.']
                    _card_animal(i+1, row, cores[i], icons[i])

            with col_bot:
                st.markdown("##### Atenção Necessária")
                bottom = df_sorted.tail(3).iloc[::-1]
                for i, (_, row) in enumerate(bottom.iterrows()):
                    _card_animal(len(df_sorted)-i, row, '#ef4444', '')

            # ── Gráfico de barras ranking ───────
            st.divider()
            label_map = {
                "Lucro/L (Mais Lucrativas)":    ("Lucro_L",     "Lucro por Litro (R$)"),
                "Custo/L (Mais Baratas)":        ("Custo_L",     "Custo por Litro (R$)"),
                "Margem de Lucro (R$)":          ("Margem",      "Margem de Lucro (R$)"),
                "Produção Total (L)":            ("Leite_Total", "Produção Total (L)"),
                "Eficiência (L/kg ração)":       ("Eficiencia",  "Eficiência (L/kg ração)"),
                "Média Diária (L/dia)":          ("Media_Dia",   "Média Diária (L/dia)"),
                "Custo Ração (R$)":              ("Custo_Racao", "Custo de Ração (R$)"),
                "Idade (Mais Velhas)":           ("Idade_Anos",  "Idade (anos)"),
                "Idade (Mais Novas)":            ("Idade_Anos",  "Idade (anos)"),
            }
            ycol, ylabel = label_map[metrica]

            df_bar = df_sorted.dropna(subset=[ycol]).copy()

            # Cores: verde=lucro positivo, vermelho=prejuízo, dourado/prata/bronze para top
            def _cor_barra(i, row):
                if ycol == 'Lucro_L':
                    return '#4ade80' if row['Lucro_L'] >= 0 else '#f87171'
                if ycol == 'Custo_L':
                    return '#f87171' if row['Custo_L'] > preco_ref_r else '#4ade80'
                return ('#ffd700' if i == 0 else '#c0c0c0' if i == 1
                        else '#cd7f32' if i == 2
                        else '#ef5350' if i == len(df_bar)-1 else '#43a047')

            df_bar['cor'] = [_cor_barra(i, row) for i, (_, row) in enumerate(df_bar.iterrows())]

            fig_rank = go.Figure(go.Bar(
                x=df_bar['nome_animal'],
                y=df_bar[ycol],
                marker_color=df_bar['cor'],
                text=[f"R${v:.2f}" if ycol in ('Lucro_L','Custo_L') else f"{v:.1f}"
                      for v in df_bar[ycol]],
                textposition='outside',
                textfont=dict(color='#e0e0e0', size=11),
            ))
            # Linha de referência do preço de venda para Custo/L e Lucro/L
            if ycol in ('Lucro_L', 'Custo_L'):
                ref_val = 0.0 if ycol == 'Lucro_L' else preco_ref_r
                fig_rank.add_hline(
                    y=ref_val,
                    line_dash='dash', line_color='#f59e0b', line_width=1.5,
                    annotation_text=f"Preço venda R${preco_ref_r:.2f}/L" if ycol == 'Custo_L' else "Break-even",
                    annotation_font_color='#f59e0b',
                )
            fig_rank.update_layout(
                plot_bgcolor='rgba(255,255,255,0.03)', paper_bgcolor='rgba(255,255,255,0.03)',
                font_color='#94a3b8',
                xaxis=dict(gridcolor='rgba(255,255,255,0.06)', tickangle=-30),
                yaxis=dict(gridcolor='rgba(255,255,255,0.06)', title=ylabel),
                margin=dict(l=0, r=0, t=20, b=60),
                height=340,
                showlegend=False,
            )
            st.plotly_chart(fig_rank, use_container_width=True)

            # ── Gráfico scatter: produção vs custo/L ───
            st.divider()
            st.markdown("##### Custo de Produção vs Volume — visão geral de rentabilidade")
            fig_scatter = go.Figure()
            for _, row in df_sorted.iterrows():
                cor = '#4ade80' if row['Lucro_L'] >= 0 else '#f87171'
                fig_scatter.add_trace(go.Scatter(
                    x=[row['Leite_Total']],
                    y=[row['Custo_L']],
                    mode='markers+text',
                    marker=dict(size=max(row['Leite_Total'] / df_sorted['Leite_Total'].max() * 40, 10),
                                color=cor, opacity=0.85,
                                line=dict(color='#fff', width=1)),
                    text=[row['nome_animal']],
                    textposition='top center',
                    textfont=dict(color='#e0e0e0', size=11),
                    name=row['nome_animal'],
                    hovertemplate=(
                        f"<b>{row['nome_animal']}</b><br>"
                        f"Produção: {row['Leite_Total']:.0f} L<br>"
                        f"Custo/L: R$ {row['Custo_L']:.2f}<br>"
                        f"Lucro/L: R$ {row['Lucro_L']:.2f}<br>"
                        f"Margem: R$ {row['Margem']:.2f}<extra></extra>"
                    ),
                ))
            fig_scatter.add_hline(
                y=preco_ref_r, line_dash='dash', line_color='#f59e0b', line_width=1.5,
                annotation_text=f"Preço venda R${preco_ref_r:.2f}/L",
                annotation_font_color='#f59e0b',
            )
            fig_scatter.update_layout(
                plot_bgcolor='rgba(255,255,255,0.03)', paper_bgcolor='rgba(255,255,255,0.03)',
                font_color='#94a3b8',
                xaxis=dict(title='Litros Produzidos', gridcolor='rgba(255,255,255,0.06)'),
                yaxis=dict(title='Custo por Litro (R$)', gridcolor='rgba(255,255,255,0.06)'),
                showlegend=False,
                height=360,
                margin=dict(l=0, r=0, t=10, b=0),
            )
            st.caption("Animais *acima* da linha amarela estão em prejuízo. Bolhas maiores = mais litros produzidos.")
            st.plotly_chart(fig_scatter, use_container_width=True)

            # ── Tabela completa ─────────────────
            st.divider()
            st.markdown("##### Tabela Completa de Rentabilidade")
            tbl = df_sorted[['id_animal','nome_animal','Leite_Total','Media_Dia',
                               'Racao_Total','Eficiencia','Receita','Custo_Racao',
                               'Custo_Vet','Custo_Fixo_Rat','Custo_Total',
                               'Custo_L','Lucro_L','Margem','Dias','Idade_Anos']].copy()
            tbl.columns = ['ID','Nome','Prod. (L)','Média/Dia',
                            'Ração (kg)','Efic.(L/kg)','Receita','C.Ração',
                            'C.Vet.','C.Rateado','C.Total',
                            'Custo/L','Lucro/L','Margem','Dias','Idade']

            def _highlight_rent(row):
                if row['Lucro/L'] < 0:
                    return ['background-color:#3b1010; color:#f87171'] * len(row)
                if row['Lucro/L'] == tbl['Lucro/L'].max():
                    return ['background-color:#0d2e0d; color:#4ade80'] * len(row)
                return [''] * len(row)

            fmt = {
                "Prod. (L)":   "{:.1f}",   "Média/Dia":  "{:.1f}",
                "Ração (kg)":  "{:.1f}",   "Efic.(L/kg)":"{:.2f}",
                "Receita":     "R${:.2f}", "C.Ração":    "R${:.2f}",
                "C.Vet.":      "R${:.2f}", "C.Rateado":  "R${:.2f}",
                "C.Total":     "R${:.2f}", "Custo/L":    "R${:.2f}",
                "Lucro/L":     "R${:.2f}", "Margem":     "R${:.2f}",
                "Idade":       lambda x: f"{x:.1f}" if pd.notna(x) else "—",
            }
            st.dataframe(
                tbl.style.apply(_highlight_rent, axis=1).format(fmt),
                use_container_width=True, hide_index=True,
            )

            xls_rank = exportar_excel({"Rentabilidade": tbl.reset_index(drop=True)})
            st.download_button(
                "Exportar Rankings (Excel)",
                data=xls_rank,
                file_name=f"rankings_{dt_ini_r}_{dt_fim_r}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

# ══════════════════════════════════════════════
# TAB 5 — CURVA DE LACTAÇÃO (305 DIAS)
# ══════════════════════════════════════════════
with tab_lactacao:
    st.markdown("#### Curva de Lactação — Benchmark 305 Dias")
    st.caption(
        "Compara a produção real de cada vaca com a curva padrão de Wood (benchmark zootécnico). "
        "A curva de referência é calculada para o pico de produção declarado."
    )

    lista_lact = [a for a in st.session_state.db["animais"] if a.get('status') == 'Lactação']
    if not lista_lact:
        st.info("Nenhuma vaca em lactação.")
    else:
        ops_l = {a['id']: a['nome'] for a in lista_lact}
        sel_v = st.selectbox("Selecione a vaca:", list(ops_l.keys()),
                              format_func=lambda x: f"{x} — {ops_l[x]}", key="curva_v")

        animal_obj = next((a for a in lista_lact if a['id'] == sel_v), None)
        dt_parto = None
        if animal_obj and animal_obj.get('dt_parto'):
            try:
                dt_parto = datetime.datetime.strptime(str(animal_obj['dt_parto'])[:10], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                st.warning("Data de parto inválida para este animal.")
        if dt_parto and not df_prod.empty:
            mask_lc  = df_prod['id_animal'] == sel_v
            df_lc    = df_prod[mask_lc].copy().sort_values('data')
            df_lc['dim'] = (pd.to_datetime(df_lc['data']) -
                             pd.Timestamp(dt_parto)).dt.days + 1

            # Produção real acumulada por DIM
            real = df_lc.groupby('dim')['leite'].sum().reset_index()
            real = real[real['dim'].between(1, 305)]

            # Curva de Wood: y = a * dim^b * exp(-c * dim)
            # Parâmetros típicos para vacas holandesas de alta produção
            pico_est = st.number_input("Pico de produção esperado (L/dia):",
                                        min_value=10.0, max_value=60.0,
                                        value=float(df_lc['leite'].max() or 25.0),
                                        step=1.0, key="pico_lc")
            a_w, b_w, c_w = 0.2 * pico_est, 0.15, 0.003
            dims   = np.arange(1, 306)
            wood   = a_w * (dims ** b_w) * np.exp(-c_w * dims)

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=dims, y=wood, name='Curva Wood (Referência)',
                line=dict(color='#60a5fa', dash='dash', width=2), mode='lines',
            ))
            if not real.empty:
                fig.add_trace(go.Scatter(
                    x=real['dim'], y=real['leite'], name='Produção Real',
                    line=dict(color='#f87171', width=2.5), mode='lines+markers',
                    marker=dict(size=5, color='#f87171'),
                ))
            fig.update_layout(
                plot_bgcolor='rgba(255,255,255,0.03)', paper_bgcolor='rgba(0,0,0,0)',
                font_color='#94a3b8',
                xaxis=dict(gridcolor='rgba(255,255,255,0.06)', title='Dias em Lactação (DIM)'),
                yaxis=dict(gridcolor='rgba(255,255,255,0.06)', title='Litros/dia'),
                legend=dict(font=dict(color='#94a3b8')),
                margin=dict(l=0, r=0, t=10, b=0), height=340,
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "A curva Wood é um modelo matemático padrão da zootecnia (Wood, 1967). "
                "Vacas acima da curva têm desempenho acima do esperado."
            )
        if not dt_parto:
            st.info("Selecione uma vaca com data de parto e registros de produção.")

# ══════════════════════════════════════════════
# TAB 5 — PREVISÃO DE PRODUÇÃO
# ══════════════════════════════════════════════
with tab_forecast:
    st.markdown("#### Previsão de Produção — Próximos 7 Dias")
    st.caption("Regressão polinomial sobre os últimos 30 dias de produção diária.")

    if df_prod.empty:
        st.info("Sem dados de produção para gerar previsão.")
    else:
        df_fc = df_prod.copy()
        df_fc['data'] = pd.to_datetime(df_fc['data'], errors='coerce').dt.date
        hoje_dt = datetime.date.today()
        ini_fc  = hoje_dt - timedelta(days=30)
        diario  = (df_fc[df_fc['data'] >= ini_fc]
                   .groupby('data')['leite'].sum()
                   .reset_index()
                   .sort_values('data'))

        if len(diario) < 5:
            st.warning("Mínimo de 5 dias de dados necessário para previsão.")
        else:
            # Regressão polinomial grau 2
            x = np.arange(len(diario))
            y = diario['leite'].values
            coef = np.polyfit(x, y, deg=2)
            poly = np.poly1d(coef)

            # Projetar 7 dias futuros
            dias_futuros = 7
            x_fut = np.arange(len(x), len(x) + dias_futuros)
            datas_fut = [hoje_dt + timedelta(days=i+1) for i in range(dias_futuros)]
            y_fut = np.maximum(poly(x_fut), 0)  # não deixa negativo

            # Linha de tendência sobre histórico
            y_trend = poly(x)

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=diario['data'], y=diario['leite'],
                name='Real', marker_color='#1d4ed8', opacity=0.7,
            ))
            fig.add_trace(go.Scatter(
                x=diario['data'], y=y_trend,
                name='Tendência', mode='lines',
                line=dict(color='#60a5fa', width=2, dash='dot'),
            ))
            fig.add_trace(go.Scatter(
                x=datas_fut, y=y_fut,
                name='Previsão 7d', mode='lines+markers',
                line=dict(color='#f59e0b', width=2.5),
                marker=dict(size=8, color='#f59e0b', symbol='diamond'),
            ))
            fig.update_layout(
                plot_bgcolor='rgba(255,255,255,0.03)', paper_bgcolor='rgba(255,255,255,0.03)',
                font_color='#94a3b8',
                xaxis=dict(gridcolor='rgba(255,255,255,0.06)'),
                yaxis=dict(gridcolor='rgba(255,255,255,0.06)', title='Litros'),
                legend=dict(font=dict(color='#94a3b8')),
                margin=dict(l=0, r=0, t=10, b=0), height=320,
            )
            st.plotly_chart(fig, use_container_width=True)

            # Tabela de previsão
            df_prev = pd.DataFrame({
                'Data':          [d.strftime('%d/%m/%Y') for d in datas_fut],
                'Previsão (L)':  [round(float(v), 1) for v in y_fut],
            })
            st.dataframe(df_prev, hide_index=True, use_container_width=True)
            st.caption(
                "Modelo: regressão polinomial grau 2 (numpy.polyfit). "
                "Previsões são estimativas baseadas na tendência recente — não substituem o julgamento do gestor."
            )

# ══════════════════════════════════════════════
# TAB 6 — HEATMAP DE PRODUÇÃO
# ══════════════════════════════════════════════
with tab_heatmap:
    st.markdown("#### Heatmap de Produção Anual")
    st.caption("Cada célula representa um dia — intensidade de cor pela produção em litros.")

    if df_prod.empty:
        st.info("Sem dados de produção para gerar heatmap.")
    else:
        df_hm = df_prod.copy()
        df_hm['data'] = pd.to_datetime(df_hm['data'], errors='coerce')
        df_hm = df_hm.dropna(subset=['data'])

        ano_sel = st.selectbox(
            "Ano:", sorted(df_hm['data'].dt.year.unique(), reverse=True), key='hm_ano'
        )
        df_ano = df_hm[df_hm['data'].dt.year == ano_sel]
        diario_hm = df_ano.groupby('data')['leite'].sum().reset_index()

        # Build week × weekday matrix (ISO calendar)
        diario_hm['semana']   = diario_hm['data'].dt.isocalendar().week.astype(int)
        diario_hm['dia_sem']  = diario_hm['data'].dt.weekday  # 0=Mon…6=Sun
        diario_hm['dia_str']  = diario_hm['data'].dt.strftime('%d/%m/%Y')

        pivot = diario_hm.pivot_table(
            index='dia_sem', columns='semana', values='leite', aggfunc='sum'
        ).reindex(index=range(7))

        dias_label = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
        z = pivot.values.tolist()

        # Hover text
        texto = [['' for _ in range(pivot.shape[1])] for _ in range(7)]
        for _, row in diario_hm.iterrows():
            d = int(row['dia_sem'])
            w = int(row['semana']) - int(pivot.columns.min())
            if 0 <= w < pivot.shape[1]:
                texto[d][w] = f"{row['dia_str']}<br>{row['leite']:.1f} L"

        fig_hm = go.Figure(go.Heatmap(
            z=z,
            text=texto,
            hovertemplate='%{text}<extra></extra>',
            colorscale=[
                [0.0,  '#0a0d14'],
                [0.15, '#1e3a5f'],
                [0.4,  '#1d4ed8'],
                [0.7,  '#3b82f6'],
                [1.0,  '#93c5fd'],
            ],
            showscale=True,
            colorbar=dict(
                title=dict(text='Litros', font=dict(color='#94a3b8')),
                tickfont=dict(color='#94a3b8'),
            ),
            xgap=2, ygap=2,
        ))
        fig_hm.update_layout(
            plot_bgcolor='rgba(255,255,255,0.02)', paper_bgcolor='rgba(0,0,0,0)',
            font_color='#94a3b8',
            yaxis=dict(
                tickmode='array', tickvals=list(range(7)),
                ticktext=dias_label, gridcolor='rgba(0,0,0,0)',
                tickfont=dict(color='#94a3b8'),
            ),
            xaxis=dict(
                title='Semana do ano',
                tickfont=dict(color='#94a3b8'),
                gridcolor='rgba(0,0,0,0)',
            ),
            margin=dict(l=50, r=20, t=20, b=40),
            height=260,
        )
        st.plotly_chart(fig_hm, use_container_width=True)

        # Estatísticas anuais
        if not diario_hm.empty:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total no Ano",   f"{diario_hm['leite'].sum():.0f} L")
            c2.metric("Média Diária",   f"{diario_hm['leite'].mean():.1f} L")
            c3.metric("Melhor Dia",     f"{diario_hm['leite'].max():.1f} L")
            c4.metric("Dias Registrados", len(diario_hm))

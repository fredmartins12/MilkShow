"""
Financeiro 360 — Fluxo de caixa, lançamentos e extrato editável.
"""
import streamlit as st
import pandas as pd
import datetime
import time
import plotly.express as px
from datetime import timedelta

from utils import (
    init_firebase, carregar_dados, apply_theme, page_banner,
    adicionar_item, salvar_lote, calcular_saldo, fmt_date,
    CATEGORIAS_RECEITA, CATEGORIAS_DESPESA, CATEGORIAS_FINANCEIRAS,
    CATEGORIAS_COM_ESTOQUE,
    registrar_compra_produto, registrar_compra_animal,
    exportar_excel, sidebar_mini_resumo,
)

st.set_page_config(page_title="MilkShow | Financeiro", layout="wide", page_icon="💰")
apply_theme()
init_firebase()
carregar_dados()

st.sidebar.markdown(
    '<div class="sidebar-title">MilkShow</div>'
    '<div class="sidebar-sub">Financeiro 360</div>',
    unsafe_allow_html=True,
)
sidebar_mini_resumo()
page_banner("", "Financeiro 360", "Fluxo de caixa, receitas, despesas e extrato completo")

# ── KPIs ─────────────────────────────────────
saldo, rec_total, desp_total = calcular_saldo()
k1, k2, k3 = st.columns(3)
k1.metric("Receitas Totais",  f"R$ {rec_total:,.2f}",  delta="Entradas")
k2.metric("Despesas Totais",  f"R$ {desp_total:,.2f}", delta="Saídas", delta_color="inverse")
k3.metric("Saldo em Caixa",   f"R$ {saldo:,.2f}",
          delta_color="normal" if saldo >= 0 else "inverse")

st.divider()

# ── Layout ───────────────────────────────────
c_form, c_extrato = st.columns([1, 2])

with c_form:
    with st.container(border=True):
        st.subheader("Novo Lançamento")
        tipo_lanc = st.radio("Tipo:", ["Despesa", "Receita"], horizontal=True)
        cats = CATEGORIAS_RECEITA if tipo_lanc == "Receita" else CATEGORIAS_DESPESA

        with st.form("fin"):
            cat  = st.selectbox("Categoria:", cats)
            desc = st.text_input("Descrição (opcional):")
            val  = st.number_input("Valor (R$):", min_value=0.0, step=10.0)

            # ── Venda de Leite: período de referência ──
            ref_ini, ref_fim = None, None
            if cat == "Venda de Leite":
                st.markdown("---")
                st.caption("Período de referência do leite vendido")
                cr1, cr2 = st.columns(2)
                ref_ini = cr1.date_input("De:", datetime.date.today() - timedelta(days=30))
                ref_fim = cr2.date_input("Até:", datetime.date.today())

            # ── Ração / Nutrição ou Medicamento → integra Armazém ──
            adic_estoque = False
            est_prod, est_qtd, est_un, est_forn = '', 0.0, 'kg', ''
            if cat in CATEGORIAS_COM_ESTOQUE:
                st.markdown("---")
                st.caption("Este lançamento envolve um produto físico?")
                adic_estoque = st.checkbox("Adicionar automaticamente ao Armazém", value=True)
                if adic_estoque:
                    prods_exist = [p['item'] for p in st.session_state.db.get('estoque', [])]
                    hint = ', '.join(prods_exist[:3]) if prods_exist else 'Ex: Ração Concentrada'
                    ea1, ea2 = st.columns(2)
                    est_prod = ea1.text_input("Produto:", placeholder=hint, key='fin_est_prod')
                    est_qtd  = ea1.number_input("Quantidade:", min_value=0.0, step=1.0, key='fin_est_qtd')
                    est_un   = ea2.selectbox("Unidade:", ["kg","sc","L","un","dose","fardo"], key='fin_est_un')
                    est_forn = ea2.text_input("Fornecedor (opcional):", key='fin_est_forn')

            # ── Compra de Animais → integra Rebanho ──
            cad_animal = False
            ani_id, ani_nome, ani_status, ani_lote, ani_sexo, ani_nasc = '', '', 'Novilha', 'Geral', 'Fêmea', None
            if cat == "Compra de Animais":
                st.markdown("---")
                st.caption("Cadastrar animal adquirido no Rebanho?")
                cad_animal = st.checkbox("Criar ficha do animal automaticamente", value=True)
                if cad_animal:
                    an1, an2 = st.columns(2)
                    ani_id     = an1.text_input("Brinco / ID:", key='fin_ani_id')
                    ani_nome   = an1.text_input("Nome:", key='fin_ani_nome')
                    ani_status = an2.selectbox("Status:", ["Novilha","Lactação","Seca","Garrote","Touro"], key='fin_ani_status')
                    ani_lote   = an2.selectbox("Lote:", ["Geral","A","B","C","Recria","Engorda"], key='fin_ani_lote')
                    ani_sexo   = an2.radio("Sexo:", ["Fêmea","Macho"], horizontal=True, key='fin_ani_sexo')
                    ani_nasc   = an1.date_input("Nascimento (aprox.):", value=None, key='fin_ani_nasc')

            if st.form_submit_button("Lançar", type="primary"):
                if val > 0:
                    # ── caso: produto físico com estoque ──
                    if adic_estoque and cat in CATEGORIAS_COM_ESTOQUE:
                        if est_prod and est_qtd > 0:
                            registrar_compra_produto(
                                prod_nome=est_prod, qtd=est_qtd, unidade=est_un,
                                valor_total=val, cat_fin=cat,
                                fornecedor=est_forn, desc_extra=desc,
                            )
                            st.success(f"Lançado! **{est_prod}** adicionado ao Armazém.")
                        else:
                            st.error("Informe o nome e a quantidade do produto.")
                            st.stop()

                    # ── caso: compra de animal ──
                    elif cad_animal and cat == "Compra de Animais":
                        if ani_id and ani_nome:
                            ids_exist = [a['id'] for a in st.session_state.db.get('animais', [])]
                            if ani_id in ids_exist:
                                st.error(f"Brinco #{ani_id} já cadastrado!")
                                st.stop()
                            registrar_compra_animal(
                                animal_id=ani_id, nome=ani_nome, status=ani_status,
                                valor=val, lote=ani_lote, sexo=ani_sexo,
                                nasc=str(ani_nasc) if ani_nasc else '',
                            )
                            st.success(f"Lançado! **{ani_nome}** cadastrado no Rebanho.")
                        else:
                            st.error("Informe o Brinco e o Nome do animal.")
                            st.stop()

                    # ── caso: lançamento simples ──
                    else:
                        reg = {
                            "data":   str(datetime.date.today()),
                            "cat":    cat,
                            "desc":   desc,
                            "valor":  val,
                            "tipo":   "Geral",
                            "animal": None,
                        }
                        if cat == "Venda de Leite":
                            reg["ref_ini"] = str(ref_ini)
                            reg["ref_fim"] = str(ref_fim)
                        adicionar_item("financeiro", reg)
                        st.success("Lançado!")

                    time.sleep(0.8)
                    st.rerun()
                else:
                    st.error("Informe um valor maior que zero.")

    # ── Gráfico receita vs despesa ─────────────
    st.divider()
    df_f_full = pd.DataFrame(st.session_state.db["financeiro"])
    if not df_f_full.empty:
        df_f_full['data'] = pd.to_datetime(df_f_full['data'], errors='coerce')
        df_f_full['Tipo'] = df_f_full['cat'].apply(
            lambda c: "Receita" if c in CATEGORIAS_RECEITA else "Despesa"
        )
        mensal = df_f_full.copy()
        mensal['mes'] = mensal['data'].dt.to_period('M').astype(str)
        mensal = mensal.groupby(['mes', 'Tipo'])['valor'].sum().reset_index()
        fig = px.bar(mensal, x='mes', y='valor', color='Tipo',
                     barmode='group',
                     color_discrete_map={'Receita': '#43a047', 'Despesa': '#c62828'},
                     labels={'valor': 'R$', 'mes': ''})
        fig.update_layout(
            plot_bgcolor='rgba(255,255,255,0.03)', paper_bgcolor='rgba(255,255,255,0.03)',
            font_color='#94a3b8', legend=dict(font=dict(color='#94a3b8')),
            xaxis=dict(gridcolor='rgba(255,255,255,0.06)'),
            yaxis=dict(gridcolor='rgba(255,255,255,0.06)'),
            margin=dict(l=0, r=0, t=10, b=0), height=220,
        )
        st.subheader("Receita vs Despesa por Mês")
        st.plotly_chart(fig, use_container_width=True)

with c_extrato:
    st.subheader("Extrato Editável")
    df_f = pd.DataFrame(st.session_state.db["financeiro"])
    if not df_f.empty:
        for col in ['data', 'ref_ini', 'ref_fim']:
            if col not in df_f.columns:
                df_f[col] = None
            df_f[col] = pd.to_datetime(df_f[col], errors='coerce')

        edited = st.data_editor(
            df_f.sort_values('data', ascending=False),
            use_container_width=True,
            num_rows="dynamic",
            hide_index=True,
            column_config={
                "doc_id":  None,
                "valor":   st.column_config.NumberColumn("Valor",      format="R$ %.2f"),
                "data":    st.column_config.DateColumn("Data Caixa",   format="DD/MM/YYYY"),
                "ref_ini": st.column_config.DateColumn("Ref. Início",  format="DD/MM/YYYY"),
                "ref_fim": st.column_config.DateColumn("Ref. Fim",     format="DD/MM/YYYY"),
                "cat":     st.column_config.SelectboxColumn("Categoria", options=CATEGORIAS_FINANCEIRAS),
                "desc":    "Descrição",
                "tipo":    None,
                "animal":  None,
            },
            key="editor_financeiro",
        )

        col_s, col_x = st.columns(2)
        with col_s:
            if st.button("Salvar Alterações no Extrato", type="primary", use_container_width=True):
                recs = edited.to_dict('records')
                for r in recs:
                    r['data']    = fmt_date(r.get('data'))
                    r['ref_ini'] = fmt_date(r.get('ref_ini'))
                    r['ref_fim'] = fmt_date(r.get('ref_fim'))
                salvar_lote("financeiro", recs)

        with col_x:
            xls = exportar_excel({
                "Extrato": df_f.drop(columns=['doc_id'], errors='ignore')
            })
            st.download_button(
                "Exportar Extrato (Excel)",
                data=xls,
                file_name="financeiro.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
    else:
        st.warning("Caixa vazio.")

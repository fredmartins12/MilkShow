"""
Sanidade — Histórico sanitário, vacinações, medicamentos.
"""
import streamlit as st
import pandas as pd
import datetime

from utils import (
    init_firebase, carregar_dados, apply_theme, page_banner,
    TIPOS_SANITARIOS, exportar_excel,
    registrar_procedimento_sanitario, sidebar_mini_resumo,
)

st.set_page_config(page_title="MilkShow | Sanidade", layout="wide", page_icon="💉")
apply_theme()
init_firebase()
carregar_dados()

st.sidebar.markdown(
    '<div class="sidebar-title">MilkShow</div>'
    '<div class="sidebar-sub">Sanidade</div>',
    unsafe_allow_html=True,
)
sidebar_mini_resumo()
page_banner("", "Controle Sanitário", "Vacinações, medicamentos e histórico do rebanho")

c_form, c_hist = st.columns([1, 2])

with c_form:
    with st.container(border=True):
        st.subheader("Novo Registro")
        with st.form("sanidade"):
            tipo    = st.selectbox("Tipo:", TIPOS_SANITARIOS)
            modo    = st.radio("Aplicação:", ["Individual", "Rebanho Todo"], horizontal=True)
            sel_ani = None
            if modo == "Individual":
                ops = {a['id']: a['nome'] for a in st.session_state.db["animais"]}
                if ops:
                    sel_ani = st.selectbox(
                        "Animal:", list(ops.keys()),
                        format_func=lambda x: f"{x} — {ops[x]}"
                    )
                else:
                    st.warning("Nenhum animal cadastrado.")

            st.markdown("---")
            # ── Integração com Armazém ──────────────
            estoque_items = [p['item'] for p in st.session_state.db.get('estoque', [])]
            usar_estoque  = st.checkbox("Usar produto do Armazém", value=bool(estoque_items))

            prod     = ''
            qtd_uso  = 0.0
            if usar_estoque and estoque_items:
                prod_sel  = st.selectbox("Produto do Estoque:", estoque_items, key='san_prod_est')
                item_obj  = next((i for i in st.session_state.db['estoque'] if i['item'] == prod_sel), None)
                disp      = f"{item_obj['qtd']:.1f} {item_obj.get('un','')}" if item_obj else ''
                qtd_uso   = st.number_input(
                    f"Quantidade usada (disponível: {disp}):",
                    min_value=0.0,
                    max_value=float(item_obj['qtd']) if item_obj else 0.0,
                    step=0.1, key='san_qtd_uso',
                )
                prod = prod_sel
            else:
                prod = st.text_input("Produto Usado:")

            custo = st.number_input("Custo Total (R$):", min_value=0.0, step=10.0)
            obs   = st.text_area("Observações:")

            if st.form_submit_button("Salvar", type="primary"):
                if prod:
                    avisos = registrar_procedimento_sanitario(
                        tipo=tipo,
                        prod=prod,
                        modo=modo,
                        animal=sel_ani,
                        custo=custo,
                        obs=obs,
                        baixar_do_estoque=(usar_estoque and qtd_uso > 0),
                        qtd_estoque=qtd_uso,
                    )
                    for av in avisos:
                        st.warning(av)
                    st.success("Registro salvo!" + (" Estoque atualizado." if usar_estoque and qtd_uso > 0 else ""))
                    st.rerun()
                else:
                    st.error("Informe o nome do produto.")

with c_hist:
    st.subheader("Histórico Sanitário")
    data_san = st.session_state.db.get("sanitario", [])
    if data_san:
        df_s = pd.DataFrame(data_san)
        df_s['data'] = pd.to_datetime(df_s['data'], errors='coerce')

        # Filtros
        fc1, fc2 = st.columns(2)
        filtro_tipo = fc1.multiselect("Filtrar por tipo:", TIPOS_SANITARIOS)
        filtro_modo = fc2.radio("Modo:", ["Todos", "Individual", "Rebanho Todo"], horizontal=True)

        df_view = df_s.copy()
        if filtro_tipo:
            df_view = df_view[df_view['tipo'].isin(filtro_tipo)]
        if filtro_modo != "Todos":
            df_view = df_view[df_view['modo'] == filtro_modo]

        st.dataframe(
            df_view.sort_values('data', ascending=False)
                   .drop(columns=['doc_id'], errors='ignore'),
            use_container_width=True,
            hide_index=True,
            column_config={
                "data":   st.column_config.DateColumn("Data",       format="DD/MM/YYYY"),
                "custo":  st.column_config.NumberColumn("Custo",    format="R$ %.2f"),
                "tipo":   "Tipo",
                "prod":   "Produto",
                "modo":   "Aplicação",
                "animal": "Animal",
                "obs":    "Observações",
            },
        )

        xls = exportar_excel({
            "Sanitario": df_view.drop(columns=['doc_id'], errors='ignore')
        })
        st.download_button(
            "Exportar Histórico (Excel)",
            data=xls,
            file_name="sanitario.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.info("Nenhum registro sanitário ainda.")

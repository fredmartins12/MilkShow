"""
Armazém Avançado — Estoque com média ponderada e baixas.
"""
import streamlit as st
import pandas as pd
import datetime
import time

from utils import (
    init_firebase, carregar_dados, apply_theme, page_banner,
    exportar_excel, sidebar_mini_resumo,
    registrar_compra_produto, registrar_procedimento_sanitario,
    atualizar_item,
    TIPOS_SANITARIOS,
)

st.set_page_config(page_title="MilkShow | Armazém", layout="wide", page_icon="📦")
apply_theme()
init_firebase()
carregar_dados()

st.sidebar.markdown(
    '<div class="sidebar-title">MilkShow</div>'
    '<div class="sidebar-sub">Armazém Avançado</div>',
    unsafe_allow_html=True,
)
sidebar_mini_resumo()
page_banner("", "Armazém Avançado", "Estoque com preço médio ponderado e baixas automáticas")

tab_lista, tab_compra, tab_uso = st.tabs([
    "Estoque Atual",
    "Registrar Compra",
    "Registrar Uso",
])

# ══════════════════════════════════════════════
# TAB 1 — ESTOQUE ATUAL
# ══════════════════════════════════════════════
with tab_lista:
    estoque = st.session_state.db.get("estoque", [])
    if estoque:
        df_e = pd.DataFrame(estoque)
        df_e['valor_total'] = df_e['qtd'] * df_e['custo_medio']
        total_patrim = df_e['valor_total'].sum()

        k1, k2, k3 = st.columns(3)
        k1.metric("Itens em Estoque",      len(df_e))
        k2.metric("Valor Total (Patrimônio)", f"R$ {total_patrim:,.2f}")
        k3.metric("Itens com Estoque Baixo",
                  int((df_e['qtd'] < 10).sum()),
                  delta_color="inverse")

        # Alertas de estoque baixo
        baixos = df_e[df_e['qtd'] < 10]
        if not baixos.empty:
            st.warning(
                "Produtos com estoque baixo (< 10 unidades): "
                + ", ".join(baixos['item'].tolist())
            )

        st.dataframe(
            df_e.sort_values('item'),
            use_container_width=True,
            hide_index=True,
            column_config={
                "doc_id":       None,
                "item":         "Produto",
                "qtd":          st.column_config.NumberColumn("Qtd Atual",    format="%.2f"),
                "un":           "Unidade",
                "custo_medio":  st.column_config.NumberColumn("Custo Médio",  format="R$ %.2f"),
                "valor_total":  st.column_config.NumberColumn("Valor Total",  format="R$ %.2f"),
            },
        )

        xls = exportar_excel({
            "Estoque": df_e.drop(columns=['doc_id'], errors='ignore')
        })
        st.download_button(
            "Exportar Estoque (Excel)",
            data=xls,
            file_name="estoque.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.info("Nenhum produto cadastrado. Registre uma compra para começar.")

# ══════════════════════════════════════════════
# TAB 2 — COMPRA
# ══════════════════════════════════════════════
with tab_compra:
    with st.container(border=True):
        st.caption(
            "Lança a entrada no estoque (média ponderada) e a despesa no financeiro automaticamente."
        )
        with st.form("compra_estoque"):
            col_a, col_b = st.columns(2)
            prods_exist  = [p['item'] for p in st.session_state.db.get("estoque", [])]
            hint = f"Sugestões: {', '.join(prods_exist[:3])}..." if prods_exist else "Ex: Ração, Sal Mineral..."

            prod_nome  = col_a.text_input("Produto:", placeholder=hint)
            qtd_compra = col_a.number_input("Quantidade Comprada:", min_value=0.1, step=1.0)
            unidade    = col_a.selectbox("Unidade:", ["kg", "sc (saco)", "L", "un", "dose", "fardo"])
            val_nota   = col_b.number_input("Valor Total da Nota (R$):", min_value=0.0, step=10.0)
            cat_fin    = col_b.selectbox("Categoria Financeira:", ["Ração / Nutrição", "Medicamento / Sanitário", "Infraestrutura", "Outros"])
            fornecedor = col_b.text_input("Fornecedor (opcional):")

            if qtd_compra > 0 and val_nota > 0:
                col_b.caption(f"Custo unitário: **R$ {val_nota/qtd_compra:.2f}/{unidade}**")

            # ── Se for medicamento, oferecer registrar na Sanidade ──
            reg_sanidade = False
            san_tipo, san_modo, san_animal = TIPOS_SANITARIOS[0], 'Rebanho Todo', None
            if cat_fin == "Medicamento / Sanitário":
                st.markdown("---")
                st.caption("Registrar no histórico sanitário?")
                reg_sanidade = st.checkbox("Criar registro sanitário automático", value=True)
                if reg_sanidade:
                    sm1, sm2 = st.columns(2)
                    san_tipo  = sm1.selectbox("Tipo:", TIPOS_SANITARIOS, key='arm_san_tipo')
                    san_modo  = sm2.radio("Aplicação:", ["Rebanho Todo", "Individual"], horizontal=True, key='arm_san_modo')
                    if san_modo == "Individual":
                        ops_a = {a['id']: a['nome'] for a in st.session_state.db.get('animais', [])}
                        if ops_a:
                            san_animal = st.selectbox(
                                "Animal:", list(ops_a.keys()),
                                format_func=lambda x: f"{x} — {ops_a[x]}", key='arm_san_ani'
                            )

            if st.form_submit_button("Confirmar Entrada", type="primary"):
                if prod_nome and qtd_compra > 0 and val_nota > 0:
                    registrar_compra_produto(
                        prod_nome=prod_nome, qtd=qtd_compra, unidade=unidade,
                        valor_total=val_nota, cat_fin=cat_fin, fornecedor=fornecedor,
                    )
                    if reg_sanidade:
                        registrar_procedimento_sanitario(
                            tipo=san_tipo, prod=prod_nome, modo=san_modo,
                            animal=san_animal, custo=0.0,
                            obs=f"Compra registrada — {qtd_compra} {unidade}",
                            baixar_do_estoque=False,
                        )
                    st.success(f"**{prod_nome}** entrada no estoque e lançado no financeiro!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Preencha Produto, Quantidade e Valor.")

# ══════════════════════════════════════════════
# TAB 3 — USO / BAIXA
# ══════════════════════════════════════════════
with tab_uso:
    estoque = st.session_state.db.get("estoque", [])
    if not estoque:
        st.warning("Estoque vazio. Faça uma compra primeiro.")
    else:
        with st.container(border=True):
            st.caption("Registra consumo interno. Não gera novo lançamento financeiro (já pago na compra).")
            ops_e    = {p['item']: f"{p['item']} (Atual: {p['qtd']:.1f} {p['un']})" for p in estoque}
            c_u1, c_u2 = st.columns(2)
            item_uso = c_u1.selectbox("Produto:", list(ops_e.keys()), format_func=lambda x: ops_e[x])
            item_obj = next((i for i in estoque if i["item"] == item_uso), None)

            max_qtd = float(item_obj['qtd']) if item_obj else 0.0
            qtd_uso = c_u2.number_input(
                f"Quantidade usada (máx {max_qtd:.1f}):",
                min_value=0.0, max_value=max_qtd, step=0.5,
            )

            if st.button("Confirmar Baixa", type="primary", use_container_width=True):
                if item_obj and qtd_uso > 0:
                    nova_qtd = item_obj["qtd"] - qtd_uso
                    atualizar_item("estoque", item_obj['doc_id'], {'qtd': nova_qtd})
                    st.success(f"Baixa realizada! Restam **{nova_qtd:.1f} {item_obj['un']}**.")
                    time.sleep(1)
                    st.rerun()

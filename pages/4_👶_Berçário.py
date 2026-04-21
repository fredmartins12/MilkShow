"""
Berçário — Gestão de bezerros, colostragem, desmame e saída.
"""
import streamlit as st
import pandas as pd
import datetime
import time

from utils import (
    init_firebase, carregar_dados, apply_theme, page_banner,
    adicionar_item, atualizar_item, deletar_item, salvar_lote, fmt_date,
)

st.set_page_config(page_title="MilkShow | Berçário", layout="wide", page_icon="👶")
apply_theme()
init_firebase()
carregar_dados()

st.sidebar.markdown(
    '<div class="sidebar-title">MilkShow</div>'
    '<div class="sidebar-sub">Berçário</div>',
    unsafe_allow_html=True,
)
page_banner("", "Berçário", "Gestão completa de bezerros, colostragem e desmame")

bezerros = [a for a in st.session_state.db["animais"] if a.get('status') == 'Bezerro']

# ── KPIs ─────────────────────────────────────
total_b = len(bezerros)
colostro_ok  = sum(1 for b in bezerros if b.get('colostro'))
femeas       = sum(1 for b in bezerros if b.get('sexo') == 'Fêmea')
machos       = sum(1 for b in bezerros if b.get('sexo') == 'Macho')

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total no Berçário", total_b)
k2.metric("Colostragem OK",    colostro_ok)
k3.metric("Fêmeas",            femeas)
k4.metric("Machos",            machos)

st.divider()

tab_ver, tab_entrada, tab_saida = st.tabs([
    "Visualizar / Editar",
    "Entrada Manual",
    "Saída / Evolução",
])

# ══════════════════════════════════════════════
# TAB 1 — VISUALIZAR
# ══════════════════════════════════════════════
with tab_ver:
    if bezerros:
        df_b = pd.DataFrame(bezerros)
        if 'nasc' in df_b.columns:
            df_b['nasc'] = pd.to_datetime(df_b['nasc'], errors='coerce')

        hoje = datetime.date.today()
        df_b['Idade (dias)'] = df_b['nasc'].apply(
            lambda x: (hoje - x.date()).days if pd.notnull(x) else None
        )

        st.info("Edite diretamente na tabela e clique em Salvar.")
        df_edit = st.data_editor(
            df_b,
            column_config={
                "doc_id":       None,
                "nasc":         st.column_config.DateColumn("Nascimento", format="DD/MM/YYYY"),
                "colostro":     st.column_config.CheckboxColumn("Colostro OK?"),
                "sexo":         st.column_config.SelectboxColumn("Sexo", options=["Fêmea", "Macho"]),
                "mae_id":       "ID Mãe",
                "id":           st.column_config.TextColumn("Brinco", disabled=True),
                "Idade (dias)": st.column_config.NumberColumn("Idade", disabled=True),
            },
            use_container_width=True,
            hide_index=True,
            key="bez_edit",
        )
        if st.button("Salvar Alterações", type="primary"):
            recs = df_edit.to_dict('records')
            for r in recs:
                r['nasc'] = fmt_date(r.get('nasc'))
                r.pop('Idade (dias)', None)
            salvar_lote("animais", recs)
    else:
        st.warning("Nenhum bezerro no berçário.")

# ══════════════════════════════════════════════
# TAB 2 — ENTRADA MANUAL
# ══════════════════════════════════════════════
with tab_entrada:
    with st.container(border=True):
        st.caption("Compra de bezerros externos ou cadastro avulso.")
        with st.form("novo_bezerro"):
            c1, c2, c3 = st.columns(3)
            b_id   = c1.text_input("Brinco / ID")
            b_nome = c2.text_input("Nome")
            b_nasc = c3.date_input("Nascimento", datetime.date.today())
            b_sexo  = st.radio("Sexo:", ["Fêmea", "Macho"], horizontal=True)
            b_valor = st.number_input("Valor de Compra (R$):", min_value=0.0, step=50.0)

            if st.form_submit_button("Cadastrar", type="primary"):
                if b_id and b_nome:
                    ids_exist = [a['id'] for a in st.session_state.db["animais"]]
                    if b_id in ids_exist:
                        st.error("Já existe um animal com este ID.")
                    else:
                        adicionar_item("animais", {
                            "id": b_id, "nome": b_nome, "status": "Bezerro",
                            "lote": "Berçário", "nasc": str(b_nasc),
                            "mae_id": None, "sexo": b_sexo,
                            "colostro": False, "freq": 0,
                        })
                        if b_valor > 0:
                            adicionar_item("financeiro", {
                                "data":   str(datetime.date.today()),
                                "cat":    "Compra de Animais",
                                "desc":   f"Compra Bezerro {b_id} — {b_nome}",
                                "valor":  b_valor,
                                "tipo":   "Individual",
                                "animal": b_id,
                            })
                        st.success(f"{b_nome} cadastrado!")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.error("ID e Nome são obrigatórios.")

# ══════════════════════════════════════════════
# TAB 3 — SAÍDA
# ══════════════════════════════════════════════
with tab_saida:
    if not bezerros:
        st.info("Sem bezerros no berçário.")
    else:
        ops_b = {b['id']: f"{b['nome']} ({b.get('sexo','')})" for b in bezerros}
        sel_b = st.selectbox(
            "Selecione o Bezerro:",
            list(ops_b.keys()),
            format_func=lambda x: f"{x} — {ops_b[x]}",
        )
        b_obj = next((b for b in bezerros if b['id'] == sel_b), None)

        tipo_saida = st.radio(
            "Tipo de Saída:",
            ["Evolução (Vai para Pasto)", "Venda (Sai da Fazenda)"],
            horizontal=True,
        )

        if tipo_saida == "Venda (Sai da Fazenda)":
            val_venda = st.number_input("Valor da Venda (R$):", min_value=0.0, step=50.0)
            if st.button("Confirmar Venda", type="primary"):
                if b_obj:
                    adicionar_item("financeiro", {
                        "data":   str(datetime.date.today()),
                        "cat":    "Venda de Animais",
                        "desc":   f"Venda Bezerro {sel_b} — {ops_b[sel_b]}",
                        "valor":  val_venda,
                        "tipo":   "Receita",
                        "animal": sel_b,
                    })
                    deletar_item("animais", b_obj['doc_id'])
                    st.success("Venda registrada!")
                    time.sleep(1)
                    st.rerun()
        else:
            novo_lote   = st.selectbox("Novo Lote:", ["Recria", "Geral", "Engorda"])
            novo_status = "Novilha" if b_obj and b_obj.get('sexo') == "Fêmea" else "Garrote"
            st.info(f"Animal virará **{novo_status}** no lote **{novo_lote}**.")
            if st.button("Processar Evolução", type="primary"):
                if b_obj:
                    atualizar_item("animais", b_obj['doc_id'], {
                        'status': novo_status, 'lote': novo_lote,
                    })
                    st.success(f"{b_obj['nome']} evoluído para {novo_status}!")
                    time.sleep(1)
                    st.rerun()

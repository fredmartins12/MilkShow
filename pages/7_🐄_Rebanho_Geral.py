"""
Rebanho Geral — Inventário completo, filtros, edição e venda de animais.
"""
import streamlit as st
import pandas as pd
import datetime
import time

from utils import (
    init_firebase, carregar_dados, apply_theme, page_banner,
    adicionar_item, atualizar_item, deletar_item, salvar_lote, fmt_date,
    exportar_excel, sidebar_mini_resumo,
)
import io as _io

st.set_page_config(page_title="MilkShow | Rebanho", layout="wide", page_icon="🐄")
apply_theme()
init_firebase()
carregar_dados()

st.sidebar.markdown(
    '<div class="sidebar-title">MilkShow</div>'
    '<div class="sidebar-sub">Rebanho Geral</div>',
    unsafe_allow_html=True,
)
sidebar_mini_resumo()
page_banner("", "Rebanho Geral", "Inventário completo, filtros avançados e gestão do rebanho")

# ── KPIs ─────────────────────────────────────
animais  = st.session_state.db.get("animais", [])
df_raw   = pd.DataFrame(animais)

if not df_raw.empty:
    status_count = df_raw['status'].value_counts()
    cols_k = st.columns(min(len(status_count), 6))
    for i, (s, q) in enumerate(status_count.items()):
        if i < 6:
            cols_k[i].metric(s, q)
    st.divider()

# ── Cadastro ─────────────────────────────────
with st.expander("Cadastrar Novo Animal", expanded=False):
    with st.form("form_cadastro_geral"):
        c1, c2, c3 = st.columns(3)
        novo_id     = c1.text_input("Brinco / ID")
        novo_nome   = c2.text_input("Nome / Apelido")
        novo_sexo   = c3.radio("Sexo:", ["Fêmea", "Macho"], horizontal=True)

        c4, c5, c6 = st.columns(3)
        novo_status = c4.selectbox("Status Atual:", ["Lactação", "Seca", "Novilha", "Garrote", "Touro"])
        novo_lote   = c5.selectbox("Lote:",  ["A", "B", "C", "Maternidade", "Recria", "Engorda", "Geral"])
        novo_nasc   = c6.date_input("Data de Nascimento (aprox.):", value=None)

        st.markdown("---")
        st.caption("Dados Reprodutivos — apenas para fêmeas")
        r1, r2 = st.columns(2)
        novo_parto = r1.date_input("Último Parto:", value=None)
        novo_insem = r2.date_input("Última Inseminação:", value=None)
        nova_prenz = st.checkbox("Animal está Prenhe?")

        if st.form_submit_button("Salvar Animal", type="primary"):
            if novo_id and novo_nome:
                ids_exist = [a['id'] for a in animais]
                if novo_id in ids_exist:
                    st.error("Já existe um animal com este ID!")
                else:
                    adicionar_item("animais", {
                        "id": novo_id, "nome": novo_nome,
                        "status": novo_status, "lote": novo_lote, "sexo": novo_sexo,
                        "nasc":     str(novo_nasc)  if novo_nasc  else None,
                        "dt_parto": str(novo_parto) if novo_parto else None,
                        "dt_insem": str(novo_insem) if novo_insem else None,
                        "freq":     2 if novo_status == "Lactação" else 0,
                        "mae_id":   None, "colostro": True, "prenhez": nova_prenz,
                    })
                    st.success(f"{novo_nome} cadastrado!")
                    time.sleep(1)
                    st.rerun()
            else:
                st.warning("Brinco e Nome são obrigatórios.")

# ── Tabela filtrada ───────────────────────────
if df_raw.empty:
    st.warning("Nenhum animal cadastrado.")
else:
    with st.container(border=True):
        st.markdown("#### Filtros")
        fc1, fc2, fc3 = st.columns(3)
        f_status  = fc1.multiselect("Status:", df_raw['status'].unique().tolist())
        f_lote    = fc2.multiselect("Lote:",   df_raw['lote'].unique().tolist() if 'lote' in df_raw.columns else [])
        f_prenhez = fc3.radio("Situação:", ["Todos", "Prenhes", "Vazias"], horizontal=True)

        colunas_pad = ["id", "nome", "status", "lote", "nasc", "prenhez", "dt_parto"]
        defaults_ok = [c for c in colunas_pad if c in df_raw.columns]
        cols_sel    = st.multiselect("Colunas visíveis:", df_raw.columns.tolist(), default=defaults_ok)

    df_view = df_raw.copy()
    if f_status:   df_view = df_view[df_view['status'].isin(f_status)]
    if f_lote:     df_view = df_view[df_view['lote'].isin(f_lote)]
    if 'prenhez' in df_view.columns:
        if f_prenhez == "Prenhes":
            df_view = df_view[df_view['prenhez'] == True]
        elif f_prenhez == "Vazias":
            df_view = df_view[df_view['prenhez'] != True]

    # Ordenar colunas com prioridade visual
    prio = [c for c in ["id","nome","status"] if c in (cols_sel or df_view.columns)]
    resto = [c for c in (cols_sel or df_view.columns) if c not in prio]
    cols_final = prio + resto

    for col in ['dt_parto', 'dt_insem', 'nasc']:
        if col in df_view.columns:
            df_view[col] = pd.to_datetime(df_view[col], errors='coerce')

    lista_maes = [None] + df_raw[df_raw.get('sexo', pd.Series()) == 'Fêmea']['id'].unique().tolist() if 'sexo' in df_raw.columns else [None]

    st.caption(f"Listando {len(df_view)} animais")
    df_edit = st.data_editor(
        df_view[cols_final] if cols_final else df_view,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        key="editor_rebanho",
        column_config={
            "doc_id":   None,
            "id":       st.column_config.TextColumn("Brinco", required=True, width="small"),
            "nome":     st.column_config.TextColumn("Nome",   required=True),
            "status":   st.column_config.SelectboxColumn("Status",
                            options=["Lactação","Seca","Bezerro","Novilha","Garrote","Touro"]),
            "lote":     st.column_config.SelectboxColumn("Lote",
                            options=["A","B","C","Maternidade","Berçário","Geral","Recria","Engorda"]),
            "sexo":     st.column_config.SelectboxColumn("Sexo", options=["Fêmea","Macho"]),
            "mae_id":   st.column_config.SelectboxColumn("Mãe", options=lista_maes),
            "dt_parto": st.column_config.DateColumn("Último Parto",    format="DD/MM/YYYY"),
            "dt_insem": st.column_config.DateColumn("Inseminação",      format="DD/MM/YYYY"),
            "nasc":     st.column_config.DateColumn("Nascimento",       format="DD/MM/YYYY"),
            "prenhez":  st.column_config.CheckboxColumn("Prenhe?"),
            "colostro": st.column_config.CheckboxColumn("Colostro?"),
        },
    )

    col_s, col_x = st.columns(2)
    with col_s:
        if st.button("Salvar Alterações", type="primary", use_container_width=True):
            recs = df_edit.to_dict('records')
            for r in recs:
                for dc in ['dt_parto', 'dt_insem', 'nasc']:
                    r[dc] = fmt_date(r.get(dc))
            salvar_lote("animais", recs)
    with col_x:
        xls = exportar_excel({
            "Rebanho": df_view.drop(columns=['doc_id'], errors='ignore')
        })
        st.download_button(
            "Exportar Rebanho (Excel)",
            data=xls, file_name="rebanho.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

# ── QR Code por Animal ───────────────────────
st.divider()
with st.expander("Gerar QR Code para App de Campo"):
    st.caption(
        "Escaneie o QR com o celular para abrir o app de campo direto no animal selecionado."
    )
    try:
        import qrcode
        from PIL import Image

        anim_qr = [a for a in animais if a.get('status') == 'Lactação']
        if not anim_qr:
            st.info("Nenhuma vaca em lactação.")
        else:
            opcoes_qr = {a['id']: f"{a['id']} — {a['nome']}" for a in anim_qr}
            qr_sel = st.selectbox("Animal:", list(opcoes_qr.keys()),
                                  format_func=lambda x: opcoes_qr[x], key='qr_sel')

            # URL base — usa Network URL se disponível
            base_url = st.text_input(
                "URL base do app de campo (ex: http://192.168.18.22:8503):",
                value="http://192.168.18.22:8503",
                key='qr_base_url',
            )
            url_qr = f"{base_url.rstrip('/')}/?animal={qr_sel}"

            qr_img = qrcode.make(url_qr)
            buf = _io.BytesIO()
            qr_img.save(buf, format='PNG')
            buf.seek(0)

            q1, q2 = st.columns([1, 2])
            with q1:
                st.image(buf, width=180, caption=f"Animal: {opcoes_qr[qr_sel]}")
            with q2:
                st.markdown(f"**URL gerada:**")
                st.code(url_qr)
                st.download_button(
                    "Baixar QR Code (PNG)",
                    data=buf.getvalue(),
                    file_name=f"qr_{qr_sel}.png",
                    mime="image/png",
                )
    except ImportError:
        st.warning("Instale: pip install qrcode[pil]")

# ── Venda de animal ──────────────────────────
st.divider()
with st.expander("Realizar Venda de Animal"):
    anim_venda = [a for a in animais if a.get('status') != 'Bezerro']
    if anim_venda:
        ops_v  = {a['id']: f"{a['nome']} ({a.get('status','')})" for a in anim_venda}
        cv1, cv2, cv3 = st.columns(3)
        v_id    = cv1.selectbox("Animal:", list(ops_v.keys()), format_func=lambda x: f"{x} — {ops_v[x]}")
        v_valor = cv2.number_input("Valor (R$):", min_value=0.0, step=100.0)
        v_mot   = cv3.text_input("Motivo:", "Descarte")

        if st.button("Confirmar Venda", type="primary"):
            obj = next((a for a in anim_venda if a['id'] == v_id), None)
            if obj:
                adicionar_item("financeiro", {
                    "data":   str(datetime.date.today()),
                    "cat":    "Venda de Animais",
                    "desc":   f"Venda {ops_v[v_id]} — {v_mot}",
                    "valor":  v_valor,
                    "tipo":   "Receita",
                    "animal": v_id,
                })
                deletar_item("animais", obj['doc_id'])
                st.success("Venda registrada!")
                time.sleep(1)
                st.rerun()
    else:
        st.info("Nenhum animal disponível para venda.")

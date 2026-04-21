"""
Veterinária & Reprodução — Alertas, robô veterinário, registros de parto.
"""
import streamlit as st
import datetime
import time

from utils import (
    init_firebase, carregar_dados, apply_theme, page_banner,
    processar_alertas, atualizar_item, adicionar_item,
    enviar_email_alertas, enviar_whatsapp_alertas,
    GESTACAO, DIAS_SECAGEM,
)
from datetime import timedelta

st.set_page_config(page_title="MilkShow | Veterinária", layout="wide", page_icon="🧬")
apply_theme()
init_firebase()
carregar_dados()

st.sidebar.markdown(
    '<div class="sidebar-title">MilkShow</div>'
    '<div class="sidebar-sub">Veterinária & Reprodução</div>',
    unsafe_allow_html=True,
)
page_banner("", "Veterinária & Reprodução", "Robô veterinário, alertas e gestão reprodutiva")

alertas = processar_alertas()
criticos = [a for a in alertas if a['nivel'] == 'critico']
atencao  = [a for a in alertas if a['nivel'] == 'atencao']

# ── Envio de alertas ─────────────────────────
col_alerta, col_parto = st.columns([2, 1])

with col_alerta:
    # Barra de ações
    st.subheader("Central de Alertas")
    if alertas:
        ac1, ac2, ac3 = st.columns(3)
        with ac1:
            if st.button("Enviar por E-mail", use_container_width=True):
                ok, msg = enviar_email_alertas(alertas)
                st.success(msg) if ok else st.error(msg)
        with ac2:
            if st.button("Enviar WhatsApp", use_container_width=True):
                ok, msg = enviar_whatsapp_alertas(alertas)
                st.success(msg) if ok else st.error(msg)
        with ac3:
            st.metric("Total de Alertas", len(alertas),
                      delta=f"{len(criticos)} críticos",
                      delta_color="inverse" if criticos else "off")

        st.divider()

    if not alertas:
        st.success("Manejo 100% em dia. Nenhum alerta pendente.")
    else:
        # Críticos primeiro
        for item in criticos + atencao:
            with st.container(border=True):
                c_txt, c_btn = st.columns([3, 1])
                cor  = "red" if item['nivel'] == "critico" else "orange"
                icon = ""
                c_txt.markdown(f"<span style='color:{cor};font-weight:700;'>{item['msg']}</span>", unsafe_allow_html=True)
                c_txt.caption(item.get('detalhe', ''))

                doc = item['doc_id']
                acao = item['acao']

                if acao == "inseminar":
                    if c_btn.button("Registrar Inseminação", key=f"i{doc}", use_container_width=True):
                        atualizar_item("animais", doc, {'dt_insem': str(datetime.date.today())})
                        st.rerun()

                elif acao == "diagnostico":
                    b1, b2 = c_btn.columns(2)
                    if b1.button("Prenhe", key=f"p{doc}"):
                        atualizar_item("animais", doc, {'prenhez': True})
                        st.rerun()
                    if b2.button("Vazia", key=f"v{doc}"):
                        atualizar_item("animais", doc, {'prenhez': False, 'dt_insem': None})
                        st.rerun()

                elif acao == "secar":
                    if c_btn.button("Secar Vaca", key=f"s{doc}", use_container_width=True):
                        atualizar_item("animais", doc, {'status': "Seca", 'freq': 0})
                        st.rerun()

                elif acao == "colostro":
                    if c_btn.button("Confirmar", key=f"c{doc}", use_container_width=True):
                        atualizar_item("animais", doc, {'colostro': True})
                        st.rerun()

                elif acao == "desmamar":
                    if c_btn.button("Desmamar", key=f"d{doc}", use_container_width=True):
                        atualizar_item("animais", doc, {'status': 'Novilha'})
                        st.rerun()

with col_parto:
    with st.container(border=True):
        st.subheader("Registrar Parto")
        with st.form("parto"):
            candidatas = [
                f"{a['id']} — {a['nome']}"
                for a in st.session_state.db["animais"]
                if a.get('status') not in ['Bezerro']
            ]
            if not candidatas:
                st.warning("Nenhum animal disponível.")
            else:
                mae_sel    = st.selectbox("Mãe:", candidatas)
                dt_nasc    = st.date_input("Data do Nascimento:", datetime.date.today())
                b_id       = st.text_input("Brinco/ID do Bezerro")
                b_nome     = st.text_input("Nome do Bezerro")
                b_sexo     = st.radio("Sexo:", ["Fêmea", "Macho"], horizontal=True)
                nova_freq  = st.number_input("Ordenhas/dia (mãe):", 1, 3, 2)

                if st.form_submit_button("Salvar Nascimento", type="primary"):
                    if mae_sel and b_id and b_nome:
                        id_mae   = mae_sel.split(" — ")[0]
                        mae_obj  = next(
                            (a for a in st.session_state.db["animais"] if a['id'] == id_mae), None
                        )
                        if mae_obj:
                            atualizar_item("animais", mae_obj['doc_id'], {
                                "status": "Lactação", "freq": nova_freq,
                                "dt_parto": str(dt_nasc),
                                "prenhez": False, "dt_insem": None,
                            })
                            adicionar_item("animais", {
                                "id": b_id, "nome": b_nome,
                                "status": "Bezerro", "lote": "Berçário",
                                "nasc": str(dt_nasc), "mae_id": id_mae,
                                "sexo": b_sexo, "colostro": False, "freq": 0,
                            })
                            st.success("Nascimento registrado!")
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.error("Preencha ID e Nome do bezerro.")

# ── Calendário reprodutivo ───────────────────
st.divider()
st.subheader("Previsões Reprodutivas")

animais_repro = [
    a for a in st.session_state.db["animais"]
    if a.get('status') in ['Lactação', 'Seca'] and a.get('prenhez')
       and a.get('dt_insem')
]
if animais_repro:
    import pandas as pd
    rows = []
    hoje = datetime.date.today()
    for a in animais_repro:
        try:
            dt_ins = datetime.datetime.strptime(str(a['dt_insem'])[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        prev_parto   = dt_ins + timedelta(days=GESTACAO)
        prev_secagem = prev_parto - timedelta(days=DIAS_SECAGEM)
        dias_parto   = (prev_parto - hoje).days
        rows.append({
            "Brinco": a['id'],
            "Nome":   a['nome'],
            "Inseminação":    str(dt_ins),
            "Prev. Secagem":  str(prev_secagem),
            "Prev. Parto":    str(prev_parto),
            "Dias p/ Parto":  dias_parto,
        })
    df_r = pd.DataFrame(rows).sort_values("Dias p/ Parto")
    st.dataframe(df_r, use_container_width=True, hide_index=True)
else:
    st.info("Nenhum animal prenhe com data de inseminação registrada.")

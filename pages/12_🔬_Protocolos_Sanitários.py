"""
Protocolos Sanitários — Cadastro e acompanhamento de protocolos recorrentes.
(Ex: vacina aftosa a cada 6 meses, vermifugação trimestral, etc.)
"""
import streamlit as st
import datetime
import pandas as pd
from datetime import timedelta
from firebase_admin import firestore

from utils import (
    init_firebase, carregar_dados, apply_theme, page_banner,
)

st.set_page_config(page_title="MilkShow | Protocolos", layout="wide", page_icon="🔬")
apply_theme()
init_firebase()
carregar_dados()

st.sidebar.markdown(
    '<div class="sidebar-title">MilkShow</div>'
    '<div class="sidebar-sub">Protocolos Sanitários</div>',
    unsafe_allow_html=True,
)
page_banner("", "Protocolos Sanitários", "Vacinas, vermifugações e tratamentos recorrentes")

db  = firestore.client()
hoje = datetime.date.today()

# Detecta fazenda_id
fazenda_id = st.session_state.db.get("_fazenda_id", "default")
def _coll(nome):
    if fazenda_id == "default":
        return db.collection(nome)
    return db.collection("fazendas").document(fazenda_id).collection(nome)

# ─────────────────────────────────────────────
# Carregar protocolos
# ─────────────────────────────────────────────
def _carregar_protocolos():
    docs = list(_coll("protocolos_sanitarios").stream())
    return [{"doc_id": d.id, **d.to_dict()} for d in docs]

protos = _carregar_protocolos()
animais = st.session_state.db.get("animais", [])
nomes_animais = sorted([a.get("nome","?") for a in animais if a.get("status") not in ("Vendido",)])

tab_lista, tab_novo, tab_historico = st.tabs(["Protocolos Ativos", "Novo Protocolo", "Histórico de Execuções"])

# ══════════════════════════════════════════════
# TAB 1 — LISTA
# ══════════════════════════════════════════════
with tab_lista:
    ativos   = [p for p in protos if p.get("ativo", True)]
    inativos = [p for p in protos if not p.get("ativo", True)]

    if not ativos:
        st.info("Nenhum protocolo ativo. Cadastre um na aba 'Novo Protocolo'.")
    else:
        for p in sorted(ativos, key=lambda x: x.get("proxima_data", "9999")):
            prox_str = p.get("proxima_data", "")
            try:
                prox = datetime.datetime.strptime(prox_str[:10], "%Y-%m-%d").date()
                dias  = (prox - hoje).days
                if dias < 0:
                    cor = "#f87171"; tag = f"VENCIDO há {abs(dias)}d"
                elif dias == 0:
                    cor = "#fb923c"; tag = "HOJE"
                elif dias <= 7:
                    cor = "#fbbf24"; tag = f"em {dias}d"
                else:
                    cor = "#4ade80"; tag = f"em {dias}d"
            except Exception:
                cor = "#94a3b8"; tag = "data inválida"; prox = None

            alvo = p.get("alvo", "Rebanho todo")
            freq = p.get("frequencia_dias", "?")

            with st.container():
                c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
                c1.markdown(
                    f"**{p.get('nome','?')}**  "
                    f"<span style='background:rgba(255,255,255,0.06);border-radius:5px;"
                    f"padding:1px 7px;font-size:0.75em;color:#94a3b8;'>{p.get('tipo','')}</span>",
                    unsafe_allow_html=True,
                )
                c2.markdown(
                    f"<span style='color:{cor};font-weight:600;'>Próxima: {prox_str[:10]} ({tag})</span>",
                    unsafe_allow_html=True,
                )
                c3.caption(f"A cada {freq} dias | {alvo}")

                with c4:
                    if st.button("Executar", key=f"exec_{p['doc_id']}"):
                        # Registra execução no histórico
                        _coll("protocolos_execucoes").add({
                            "protocolo_id":   p["doc_id"],
                            "protocolo_nome": p.get("nome","?"),
                            "data":           str(hoje),
                            "obs":            "",
                        })
                        # Lança no sanitário
                        _coll("sanitario").add({
                            "data":   str(hoje),
                            "tipo":   p.get("tipo","Outros"),
                            "prod":   p.get("nome","?"),
                            "modo":   "Rebanho Todo" if "rebanho" in alvo.lower() else "Individual",
                            "animal": alvo if "rebanho" not in alvo.lower() else None,
                            "custo":  float(p.get("custo_estimado", 0)),
                            "obs":    f"Protocolo automático",
                        })
                        # Atualiza próxima data
                        nova_prox = hoje + timedelta(days=int(p.get("frequencia_dias", 30)))
                        _coll("protocolos_sanitarios").document(p["doc_id"]).update({
                            "proxima_data":  str(nova_prox),
                            "ultima_data":   str(hoje),
                        })
                        st.success(f"Protocolo executado! Próxima: {nova_prox}")
                        st.rerun()

                st.divider()

    if inativos:
        with st.expander(f"Inativos ({len(inativos)})"):
            for p in inativos:
                col1, col2 = st.columns([4, 1])
                col1.markdown(f"~~{p.get('nome','?')}~~ — {p.get('tipo','')}")
                if col2.button("Reativar", key=f"reat_{p['doc_id']}"):
                    _coll("protocolos_sanitarios").document(p["doc_id"]).update({"ativo": True})
                    st.rerun()

# ══════════════════════════════════════════════
# TAB 2 — NOVO PROTOCOLO
# ══════════════════════════════════════════════
with tab_novo:
    st.markdown("#### Cadastrar Protocolo Recorrente")
    with st.form("form_protocolo"):
        n1, n2 = st.columns(2)
        nome_proto = n1.text_input("Nome do protocolo:", placeholder="Ex: Vacina Aftosa")
        tipo_proto = n2.selectbox("Tipo:", [
            "Vacina", "Vermífugo", "Antibiótico", "Hormônio", "Casqueamento",
            "Exame", "Outros"
        ])

        p1, p2, p3 = st.columns(3)
        freq_dias = p1.number_input("Repetir a cada (dias):", min_value=1, value=180, step=1)
        prox_data = p2.date_input("Primeira aplicação:", value=hoje)
        custo_est = p3.number_input("Custo estimado (R$):", min_value=0.0, value=0.0, step=10.0)

        alvo_tipo = st.radio("Aplicar em:", ["Rebanho todo", "Animal específico", "Grupo/Lote"], horizontal=True)
        alvo_val  = ""
        if alvo_tipo == "Animal específico":
            alvo_val = st.selectbox("Animal:", nomes_animais) if nomes_animais else st.text_input("Nome do animal:")
        elif alvo_tipo == "Grupo/Lote":
            alvo_val = st.text_input("Lote/Grupo:", placeholder="Ex: Lactação, Bezerros")
        else:
            alvo_val = "Rebanho todo"

        obs_proto = st.text_area("Observações:", height=80)

        if st.form_submit_button("Cadastrar Protocolo", type="primary"):
            if not nome_proto.strip():
                st.error("Informe o nome do protocolo.")
            else:
                _coll("protocolos_sanitarios").add({
                    "nome":            nome_proto.strip(),
                    "tipo":            tipo_proto,
                    "frequencia_dias": int(freq_dias),
                    "proxima_data":    str(prox_data),
                    "ultima_data":     None,
                    "alvo":            alvo_val,
                    "custo_estimado":  float(custo_est),
                    "obs":             obs_proto,
                    "ativo":           True,
                    "criado_em":       str(hoje),
                })
                st.success(f"Protocolo '{nome_proto}' cadastrado! Próxima aplicação: {prox_data}")
                st.rerun()

# ══════════════════════════════════════════════
# TAB 3 — HISTÓRICO DE EXECUÇÕES
# ══════════════════════════════════════════════
with tab_historico:
    st.markdown("#### Histórico de Execuções")
    try:
        exec_docs = list(_coll("protocolos_execucoes")
                         .order_by("data", direction=firestore.Query.DESCENDING)
                         .limit(50).stream())
        if exec_docs:
            rows = [d.to_dict() for d in exec_docs]
            df_exec = pd.DataFrame(rows)
            st.dataframe(
                df_exec[['data','protocolo_nome','obs']].rename(columns={
                    'data':'Data','protocolo_nome':'Protocolo','obs':'Obs'
                }),
                use_container_width=True, hide_index=True,
            )
        else:
            st.info("Nenhuma execução registrada ainda.")
    except Exception as e:
        st.caption(f"Erro ao carregar histórico: {e}")

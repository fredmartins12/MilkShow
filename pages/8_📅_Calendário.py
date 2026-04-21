"""
Calendário & Agenda — Eventos reprodutivos e de manejo visualizados no calendário.
"""
import streamlit as st
import pandas as pd
import datetime
import calendar
from datetime import timedelta

from utils import (
    init_firebase, carregar_dados, apply_theme, page_banner,
    GESTACAO, DIAS_SECAGEM, DIAS_DIAGNOSTICO, DIAS_PVE, DIAS_DESMAME,
)

st.set_page_config(page_title="MilkShow | Calendário", layout="wide", page_icon="📅")
apply_theme()
init_firebase()
carregar_dados()

st.sidebar.markdown(
    '<div class="sidebar-title">MilkShow</div>'
    '<div class="sidebar-sub">Calendário & Agenda</div>',
    unsafe_allow_html=True,
)
page_banner("", "Calendário de Manejo", "Eventos reprodutivos e de manejo integrados automaticamente")


def _parse_date(s):
    """Parse a YYYY-MM-DD string safely; returns None on failure."""
    if not s or str(s) in ('None', 'nan', 'NaT', ''):
        return None
    try:
        return datetime.datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def gerar_eventos(db_animais):
    eventos = []
    hoje = datetime.date.today()
    for a in db_animais:
        dt_ins  = _parse_date(a.get('dt_insem'))
        dt_part = _parse_date(a.get('dt_parto'))
        dt_nasc = _parse_date(a.get('nasc'))

        if a.get('prenhez') and dt_ins:
            prev_parto   = dt_ins + timedelta(days=GESTACAO)
            prev_secagem = prev_parto - timedelta(days=DIAS_SECAGEM)
            eventos.append({"data": prev_parto,   "tipo": "Parto",   "animal": a['nome'], "cor": "#3b82f6", "icon": "P"})
            eventos.append({"data": prev_secagem, "tipo": "Secagem", "animal": a['nome'], "cor": "#f59e0b", "icon": "S"})

        if dt_ins and not a.get('prenhez'):
            data_diag = dt_ins + timedelta(days=DIAS_DIAGNOSTICO)
            if data_diag >= hoje - timedelta(days=5):
                eventos.append({"data": data_diag, "tipo": "Diagnóstico", "animal": a['nome'], "cor": "#60a5fa", "icon": "D"})

        if dt_part and not a.get('prenhez') and not dt_ins:
            data_lib = dt_part + timedelta(days=DIAS_PVE)
            if data_lib >= hoje - timedelta(days=30):
                eventos.append({"data": data_lib, "tipo": "Liberar Insem.", "animal": a['nome'], "cor": "#f87171", "icon": "I"})

        if a.get('status') == 'Bezerro' and dt_nasc:
            data_desmame = dt_nasc + timedelta(days=DIAS_DESMAME)
            if data_desmame >= hoje - timedelta(days=7):
                eventos.append({"data": data_desmame, "tipo": "Desmame", "animal": a['nome'], "cor": "#a78bfa", "icon": "W"})

    return eventos


eventos = gerar_eventos(st.session_state.db.get("animais", []))
df_ev   = pd.DataFrame(eventos) if eventos else pd.DataFrame()

# ── Navegação ────────────────────────────────
if 'cal_ano' not in st.session_state: st.session_state.cal_ano = datetime.date.today().year
if 'cal_mes' not in st.session_state: st.session_state.cal_mes = datetime.date.today().month

c_prev, c_title, c_next = st.columns([1, 3, 1])
with c_prev:
    if st.button("◀ Mês Anterior", use_container_width=True):
        st.session_state.cal_mes -= 1
        if st.session_state.cal_mes == 0:
            st.session_state.cal_mes = 12
            st.session_state.cal_ano -= 1
with c_next:
    if st.button("Próximo Mês ▶", use_container_width=True):
        st.session_state.cal_mes += 1
        if st.session_state.cal_mes == 13:
            st.session_state.cal_mes = 1
            st.session_state.cal_ano += 1
with c_title:
    nomes_pt = ["","Janeiro","Fevereiro","Março","Abril","Maio","Junho",
                "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
    st.markdown(
        f"<h2 style='text-align:center; color:#a5d6a7;'>"
        f"{nomes_pt[st.session_state.cal_mes]} {st.session_state.cal_ano}</h2>",
        unsafe_allow_html=True,
    )

st.divider()

col_agenda, col_grid = st.columns([1, 3])

# ── Agenda próximos 30 dias ──────────────────
with col_agenda:
    with st.container(border=True):
        st.markdown("#### Próximos 30 Dias")
        hoje = datetime.date.today()
        limite = hoje + timedelta(days=30)
        if not df_ev.empty:
            mask = (df_ev['data'] >= hoje) & (df_ev['data'] <= limite)
            prox = df_ev[mask].sort_values('data')
            if not prox.empty:
                for _, row in prox.iterrows():
                    delta = (row['data'] - hoje).days
                    txt   = "Hoje!" if delta == 0 else f"em {delta} dia(s)"
                    st.markdown(
                        f"<div style='background:rgba(255,255,255,0.03); border-left:3px solid {row['cor']}; "
                        f"border-radius:8px; padding:8px 12px; margin-bottom:8px;'>"
                        f"<b>{row['data'].strftime('%d/%m')}</b> ({txt})<br>"
                        f"{row['icon']} <b>{row['tipo']}</b> — {row['animal']}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("Nenhum evento nos próximos 30 dias.")
        else:
            st.caption("Sem eventos automáticos gerados.")

    # Legenda
    st.markdown("---")
    st.caption("**Legenda:**")
    for ev_tipo, cor, icon in [
        ("Parto",          "#3b82f6", "P"),
        ("Secagem",        "#f59e0b", "S"),
        ("Diagnóstico",    "#60a5fa", "D"),
        ("Liberar Insem.", "#f87171", "I"),
        ("Desmame",        "#a78bfa", "W"),
    ]:
        st.markdown(
            f"<span style='color:{cor}; font-weight:600;'>{icon} {ev_tipo}</span>",
            unsafe_allow_html=True,
        )

# ── Grid do calendário ───────────────────────
with col_grid:
    dias_semana = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    cab = st.columns(7)
    for i, d in enumerate(dias_semana):
        cab[i].markdown(f"<div style='text-align:center; color:#66bb6a; font-weight:700;'>{d}</div>",
                        unsafe_allow_html=True)

    cal_mes = calendar.monthcalendar(st.session_state.cal_ano, st.session_state.cal_mes)
    for semana in cal_mes:
        cols = st.columns(7)
        for i, dia in enumerate(semana):
            with cols[i]:
                if dia == 0:
                    st.markdown("<div style='height:60px;'></div>", unsafe_allow_html=True)
                    continue
                data_cell = datetime.date(st.session_state.cal_ano, st.session_state.cal_mes, dia)
                is_hoje   = (data_cell == hoje)

                # Cor do número do dia
                cor_dia = "#ef5350" if is_hoje else "#c8e6c9"
                bg_dia  = "background:#1b3a20;" if is_hoje else ""

                eventos_dia = []
                if not df_ev.empty:
                    eventos_dia = df_ev[df_ev['data'] == data_cell].to_dict('records')

                # Monta HTML do dia
                html = (
                    f"<div style='border:1px solid #2a4d32; border-radius:8px; "
                    f"padding:4px 6px; min-height:60px; {bg_dia}'>"
                    f"<span style='color:{cor_dia}; font-weight:700; font-size:0.95em;'>{dia}</span>"
                )
                for ev in eventos_dia[:3]:
                    html += (
                        f"<br><span style='color:{ev['cor']}; font-size:0.65em; "
                        f"font-weight:600;'>{ev['icon']} {ev['animal'][:8]}</span>"
                    )
                if len(eventos_dia) > 3:
                    html += f"<br><span style='color:#66bb6a; font-size:0.6em;'>+{len(eventos_dia)-3}</span>"
                html += "</div>"
                st.markdown(html, unsafe_allow_html=True)

"""
gestor.py — MilkShow Home Dashboard
Entry point. Shows overview KPIs, production chart and critical alerts.
"""
import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta

from utils import (
    init_firebase, carregar_dados, apply_theme, page_banner,
    processar_alertas, calcular_saldo, get_config, PRECO_PADRAO_LEITE,
    adicionar_item, atualizar_item,
    calcular_score_rebanho, sidebar_mini_resumo, injetar_atalhos_teclado,
    auto_refresh_contador, gerar_relatorio_pdf_completo, requer_autenticacao,
    score_gauge_html,
)

# ── Page config ──────────────────────────────
st.set_page_config(
    page_title="MilkShow | Home",
    layout="wide",
    page_icon="🐄",
    initial_sidebar_state="expanded",
)
apply_theme()

# ── Firebase bootstrap ───────────────────────
try:
    init_firebase()
except Exception as e:
    st.error(f"Erro Firebase: {e}")
    st.stop()

carregar_dados()

if not requer_autenticacao():
    st.stop()

# ── Sidebar branding ─────────────────────────
st.sidebar.markdown(
    '<div class="sidebar-title">MilkShow</div>'
    '<div class="sidebar-sub">Gestão Leiteira</div>',
    unsafe_allow_html=True,
)
if st.sidebar.button("Atualizar Dados", use_container_width=True, help="Atalho: tecla R"):
    carregar_dados(force=True)
    st.rerun()

auto_refresh_contador()
injetar_atalhos_teclado()

# ── Page header ──────────────────────────────
page_banner("", "Painel Principal", "Visão consolidada da fazenda em tempo real")
sidebar_mini_resumo()

# ── Alertas críticos ─────────────────────────
alertas = processar_alertas()
criticos = [a for a in alertas if a['nivel'] == 'critico']
atencao  = [a for a in alertas if a['nivel'] == 'atencao']

if criticos:
    st.error(
        f"{len(criticos)} alerta(s) crítico(s) — aguardando ação. "
        "acesse **Veterinária & Reprodução** no menu lateral."
    )
if atencao:
    st.warning(f"{len(atencao)} alerta(s) de atenção pendentes.")

# ── Dados base ────────────────────────────────
score      = calcular_score_rebanho()
animais    = st.session_state.db['animais']
lactacao   = sum(1 for a in animais if a.get('status') == 'Lactação')
secas      = sum(1 for a in animais if a.get('status') == 'Seca')
bezerros   = sum(1 for a in animais if a.get('status') == 'Bezerro')
total_ani  = len(animais)

df_prod   = pd.DataFrame(st.session_state.db['producao'])
hoje_str  = str(datetime.date.today())
ontem_str = str(datetime.date.today() - timedelta(days=1))
prod_hoje = prod_ontem = 0.0
if not df_prod.empty:
    df_prod['data'] = df_prod['data'].astype(str)
    prod_hoje  = float(df_prod[df_prod['data'] == hoje_str]['leite'].sum())
    prod_ontem = float(df_prod[df_prod['data'] == ontem_str]['leite'].sum())

saldo, rec, desp = calcular_saldo()
preco_leite = float(get_config('preco_leite', PRECO_PADRAO_LEITE))
delta_prod  = prod_hoje - prod_ontem
nome_fazenda = str(get_config('nome_fazenda', 'Minha Fazenda'))

# ══════════════════════════════════════════════
# HERO ROW — farm name + score gauge
# ══════════════════════════════════════════════
hero_left, hero_right = st.columns([3, 1], gap="large")

with hero_left:
    st.markdown(
        f"""<div style="
            background:rgba(255,255,255,0.04);
            border:1px solid rgba(255,255,255,0.1);border-radius:14px;
            padding:28px 32px;height:100%;min-height:200px;
            display:flex;flex-direction:column;justify-content:center;">
          <div style="font-size:0.66em;color:#475569;text-transform:uppercase;
              letter-spacing:2px;font-weight:600;margin-bottom:8px;">
            {datetime.date.today().strftime('%d de %B de %Y')}
          </div>
          <div style="font-size:1.9em;font-weight:700;letter-spacing:-0.8px;line-height:1.15;
              color:#f1f5f9;margin-bottom:18px;">{nome_fazenda}</div>
          <div style="display:flex;gap:16px;flex-wrap:wrap;">
            <div style="background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.08);
                border-radius:10px;padding:10px 16px;min-width:84px;">
              <div style="font-size:1.55em;font-weight:700;color:#f1f5f9;line-height:1;">{total_ani}</div>
              <div style="font-size:0.64em;color:#64748b;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;margin-top:2px;">Animais</div>
            </div>
            <div style="background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.08);
                border-radius:10px;padding:10px 16px;min-width:84px;">
              <div style="font-size:1.55em;font-weight:700;color:#f1f5f9;line-height:1;">{lactacao}</div>
              <div style="font-size:0.64em;color:#64748b;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;margin-top:2px;">Em Lactação</div>
            </div>
            <div style="background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.08);
                border-radius:10px;padding:10px 16px;min-width:84px;">
              <div style="font-size:1.55em;font-weight:700;color:#34d399;line-height:1;">{prod_hoje:.0f}<span style="font-size:0.45em;color:#64748b;"> L</span></div>
              <div style="font-size:0.64em;color:#64748b;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;margin-top:2px;">Prod. Hoje</div>
            </div>
            <div style="background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,{'0.1' if saldo >= 0 else '0.12'});
                border-radius:10px;padding:10px 16px;min-width:100px;">
              <div style="font-size:1.3em;font-weight:700;color:{'#34d399' if saldo >= 0 else '#f87171'};line-height:1;">R$&nbsp;{saldo:,.0f}</div>
              <div style="font-size:0.64em;color:#64748b;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;margin-top:2px;">Saldo</div>
            </div>
          </div>
        </div>""",
        unsafe_allow_html=True,
    )

with hero_right:
    st.markdown(
        score_gauge_html(score['score'], score['cor'], score['label'], score['icone']),
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════
# KPI ROW
# ══════════════════════════════════════════════
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Produção Hoje",       f"{prod_hoje:.0f} L",  delta=f"{delta_prod:+.0f} L vs ontem")
k2.metric("Receita Est. Hoje",   f"R$ {prod_hoje * preco_leite:,.0f}")
k3.metric("Receitas Acumuladas", f"R$ {rec:,.0f}")
k4.metric("Despesas Acumuladas", f"R$ {desp:,.0f}", delta_color="inverse")
k5.metric("Vacas Secas / Bez.",  f"{secas} / {bezerros}")

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════
# CHARTS
# ══════════════════════════════════════════════
col_g1, col_g2 = st.columns([3, 2], gap="medium")

with col_g1:
    st.markdown(
        '<div style="font-size:0.92em;font-weight:600;color:#94a3b8;margin-bottom:10px;'
        'text-transform:uppercase;letter-spacing:0.8px;">Produção — Últimos 30 Dias</div>',
        unsafe_allow_html=True,
    )
    if not df_prod.empty:
        df_prod['data'] = pd.to_datetime(df_prod['data'], errors='coerce')
        ini_30 = pd.Timestamp(datetime.date.today() - timedelta(days=30))
        df_30  = df_prod[df_prod['data'] >= ini_30]
        if not df_30.empty:
            diario = df_30.groupby('data')['leite'].sum().reset_index()
            media  = diario['leite'].mean()
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=diario['data'], y=diario['leite'],
                mode='lines+markers',
                line=dict(color='#3b82f6', width=2.5),
                marker=dict(color='#93c5fd', size=5),
                fill='tozeroy',
                fillcolor='rgba(59,130,246,0.08)',
                name='Produção',
            ))
            fig.add_hline(y=media, line_dash='dot', line_color='#475569', line_width=1.5,
                          annotation_text=f"  Média: {media:.0f} L",
                          annotation_font_color='#64748b', annotation_font_size=11)
            fig.update_layout(
                plot_bgcolor='rgba(255,255,255,0.03)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='#94a3b8', showlegend=False,
                xaxis=dict(gridcolor='rgba(255,255,255,0.05)', tickfont=dict(color='#64748b', size=10),
                           showline=False, zeroline=False),
                yaxis=dict(gridcolor='rgba(255,255,255,0.05)', tickfont=dict(color='#64748b', size=10),
                           title='', showline=False, zeroline=False),
                margin=dict(l=8, r=8, t=8, b=8),
                height=300,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados nos últimos 30 dias.")
    else:
        st.info("Sem dados de produção cadastrados.")

with col_g2:
    st.markdown(
        '<div style="font-size:0.92em;font-weight:600;color:#94a3b8;margin-bottom:10px;'
        'text-transform:uppercase;letter-spacing:0.8px;">Composição do Rebanho</div>',
        unsafe_allow_html=True,
    )
    if animais:
        df_a = pd.DataFrame(animais)
        if 'status' in df_a.columns:
            contagem = df_a['status'].value_counts().reset_index()
            contagem.columns = ['Status', 'Qtd']
            fig2 = px.pie(
                contagem, values='Qtd', names='Status', hole=0.60,
                color_discrete_sequence=['#3b82f6','#6366f1','#10b981','#f59e0b','#ef4444','#8b5cf6'],
            )
            fig2.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                font_color='#94a3b8', showlegend=True,
                legend=dict(font=dict(color='#94a3b8', size=11), bgcolor='rgba(0,0,0,0)'),
                margin=dict(l=0, r=0, t=8, b=8),
                height=300,
            )
            fig2.update_traces(
                textfont_color='white', textfont_size=11,
                marker=dict(line=dict(color='#0a0d14', width=2)),
            )
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Sem animais cadastrados.")

# ══════════════════════════════════════════════
# ALERTAS + FOOTER
# ══════════════════════════════════════════════
st.divider()
al_col, pdf_col = st.columns([3, 1], gap="large")

with al_col:
    st.markdown(
        '<div style="font-size:0.92em;font-weight:600;color:#94a3b8;margin-bottom:12px;'
        'text-transform:uppercase;letter-spacing:0.8px;">Eventos e Alertas</div>',
        unsafe_allow_html=True,
    )
    if alertas:
        for item in alertas[:8]:
            bg  = "rgba(239,68,68,0.08)"  if item['nivel'] == 'critico' else "rgba(245,158,11,0.08)"
            brd = "rgba(239,68,68,0.25)"  if item['nivel'] == 'critico' else "rgba(245,158,11,0.25)"
            cor = "#f87171" if item['nivel'] == 'critico' else "#fcd34d"
            st.markdown(
                f'<div style="background:{bg};border:1px solid {brd};border-radius:8px;'
                f'padding:10px 14px;margin-bottom:5px;font-size:0.87em;">'
                f'<strong style="color:{cor};">{item["msg"]}</strong>'
                f'<span style="color:#64748b;margin-left:8px;">— {item.get("detalhe","")}</span></div>',
                unsafe_allow_html=True,
            )
        if len(alertas) > 8:
            st.caption(f"+ {len(alertas)-8} alertas adicionais em Veterinária.")
    else:
        st.success("Nenhum evento crítico pendente. Rebanho em dia!")

with pdf_col:
    st.markdown(
        '<div style="font-size:0.92em;font-weight:600;color:#94a3b8;margin-bottom:12px;'
        'text-transform:uppercase;letter-spacing:0.8px;">Relatório</div>',
        unsafe_allow_html=True,
    )
    pdf_bytes = gerar_relatorio_pdf_completo()
    if pdf_bytes:
        st.download_button(
            "Baixar PDF Completo",
            data=pdf_bytes,
            file_name=f"relatorio_{datetime.date.today()}.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary",
        )
    usuario = st.session_state.get('usuario_email', '')
    st.caption(
        f"MilkShow v2.0 · {datetime.date.today().strftime('%d/%m/%Y')}"
        + (f"\n{usuario}" if usuario else "")
    )

"""
Painel Mobile — Resumo otimizado para celular.
"""
import streamlit as st
import datetime
import pandas as pd
from datetime import timedelta

from utils import (
    init_firebase, carregar_dados, apply_theme,
    get_config, get_custo_racao,
    PRECO_PADRAO_LEITE, processar_alertas,
)

st.set_page_config(page_title="MilkShow | Mobile", layout="centered", page_icon="📱")
apply_theme()
init_firebase()
carregar_dados()

# CSS compacto para mobile
st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 1.6rem !important; }
[data-testid="stMetricLabel"] { font-size: 0.75rem !important; }
.bloco { background: rgba(255,255,255,0.04); border-radius: 12px;
         padding: 14px 16px; margin-bottom: 10px; }
.titulo-bloco { color: #94a3b8; font-size: 0.72em; text-transform: uppercase;
                letter-spacing: 0.08em; margin-bottom: 6px; }
.val-grande { font-size: 1.9em; font-weight: 700; color: #f1f5f9; line-height: 1.1; }
.val-sub { font-size: 0.82em; color: #64748b; margin-top: 2px; }
.tag-ok    { background: rgba(74,222,128,0.15); color: #4ade80; border-radius: 6px;
             padding: 2px 8px; font-size: 0.75em; font-weight: 600; }
.tag-alerta { background: rgba(251,191,36,0.15); color: #fbbf24; border-radius: 6px;
              padding: 2px 8px; font-size: 0.75em; font-weight: 600; }
.tag-critico { background: rgba(248,113,113,0.15); color: #f87171; border-radius: 6px;
               padding: 2px 8px; font-size: 0.75em; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

hoje      = datetime.date.today()
hoje_iso  = str(hoje)
ini_mes   = hoje.replace(day=1)
ini_7d    = hoje - timedelta(days=7)

df_prod = pd.DataFrame(st.session_state.db.get("producao", []))
df_fin  = pd.DataFrame(st.session_state.db.get("financeiro", []))
animais = st.session_state.db.get("animais", [])

if not df_prod.empty:
    df_prod['data'] = pd.to_datetime(df_prod['data'], errors='coerce').dt.date
if not df_fin.empty:
    df_fin['data'] = pd.to_datetime(df_fin['data'], errors='coerce').dt.date

# ── Saudação ─────────────────────────────────
hora = datetime.datetime.now().hour
saud = "Bom dia" if hora < 12 else "Boa tarde" if hora < 18 else "Boa noite"
nome_fazenda = get_config('nome_fazenda', 'Fazenda')
st.markdown(f"### {saud}! 👋")
st.markdown(f"**{nome_fazenda}** — {hoje.strftime('%d/%m/%Y, %A')}")
st.divider()

# ── KPIs do dia ──────────────────────────────
st.markdown("#### Hoje")
prod_hoje = df_prod[df_prod['data'] == hoje] if not df_prod.empty else pd.DataFrame()
litros_hoje = float(prod_hoje['leite'].sum()) if not prod_hoje.empty else 0.0
vacas_lact  = [a for a in animais if a.get('status') == 'Lactação']
ordenhadas  = len(prod_hoje['id_animal'].unique()) if not prod_hoje.empty else 0

c1, c2, c3 = st.columns(3)
c1.metric("Litros", f"{litros_hoje:.0f} L")
c2.metric("Ordenhadas", f"{ordenhadas}/{len(vacas_lact)}")
preco_ref = float(get_config('preco_leite', PRECO_PADRAO_LEITE))
c3.metric("Receita est.", f"R${litros_hoje * preco_ref:.0f}")

# ── Produção semana ───────────────────────────
st.markdown("#### Semana")
prod_7d = df_prod[df_prod['data'] >= ini_7d] if not df_prod.empty else pd.DataFrame()
litros_7d = float(prod_7d['leite'].sum()) if not prod_7d.empty else 0.0
media_7d  = litros_7d / 7

col_a, col_b = st.columns(2)
col_a.metric("Total 7 dias", f"{litros_7d:.0f} L")
col_b.metric("Média/dia", f"{media_7d:.0f} L")

# ── Financeiro do mês ────────────────────────
st.markdown("#### Mês Atual")
if not df_fin.empty:
    fin_mes = df_fin[df_fin['data'] >= ini_mes]
    rec_mes = float(fin_mes[fin_mes['cat'].str.contains('Venda', na=False)]['valor'].sum())
    des_mes = float(fin_mes[~fin_mes['cat'].str.contains('Venda', na=False)]['valor'].sum())
    saldo   = rec_mes - des_mes

    fa, fb, fc = st.columns(3)
    fa.metric("Receitas", f"R${rec_mes:.0f}")
    fb.metric("Despesas", f"R${des_mes:.0f}")
    fc.metric("Saldo", f"R${saldo:.0f}", delta_color="normal" if saldo >= 0 else "inverse")

    # Custo/L mês
    prod_mes  = df_prod[df_prod['data'] >= ini_mes] if not df_prod.empty else pd.DataFrame()
    litros_m  = float(prod_mes['leite'].sum()) if not prod_mes.empty else 0
    racao_m   = float(prod_mes['racao'].sum()) if not prod_mes.empty else 0
    custo_kg  = get_custo_racao()
    custo_tot = racao_m * custo_kg + des_mes
    custo_l   = custo_tot / litros_m if litros_m > 0 else 0
    lucro_l   = preco_ref - custo_l

    fd, fe = st.columns(2)
    fd.metric("Custo/L", f"R${custo_l:.2f}", delta_color="inverse")
    fe.metric("Lucro/L", f"R${lucro_l:.2f}", delta_color="normal" if lucro_l >= 0 else "inverse")

# ── Alertas ───────────────────────────────────
st.divider()
st.markdown("#### Alertas")
alertas = processar_alertas()
criticos   = [a for a in alertas if a.get('nivel') == 'critico']
atencoes   = [a for a in alertas if a.get('nivel') == 'atencao']

if not alertas:
    st.markdown("<span class='tag-ok'>Tudo em ordem!</span>", unsafe_allow_html=True)
else:
    for a in criticos:
        st.markdown(
            f"<div class='bloco'>"
            f"<span class='tag-critico'>URGENTE</span><br>"
            f"<b style='color:#f1f5f9'>{a['msg']}</b><br>"
            f"<span class='val-sub'>{a.get('detalhe','')}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    for a in atencoes:
        st.markdown(
            f"<div class='bloco'>"
            f"<span class='tag-alerta'>ATENÇÃO</span><br>"
            f"<b style='color:#f1f5f9'>{a['msg']}</b><br>"
            f"<span class='val-sub'>{a.get('detalhe','')}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

# ── Top vacas do dia ──────────────────────────
st.divider()
st.markdown("#### Top Vacas — Hoje")
if not prod_hoje.empty and 'nome_animal' in prod_hoje.columns:
    top = (prod_hoje.groupby('nome_animal')['leite'].sum()
           .sort_values(ascending=False).head(5).reset_index())
    for _, row in top.iterrows():
        pct = row['leite'] / top['leite'].max() if top['leite'].max() > 0 else 0
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:6px;'>"
            f"<span style='width:90px;color:#e2e8f0;font-weight:600'>{row['nome_animal']}</span>"
            f"<div style='flex:1;background:rgba(255,255,255,0.06);border-radius:6px;height:14px;'>"
            f"<div style='width:{pct*100:.0f}%;background:#3b82f6;border-radius:6px;height:14px;'></div>"
            f"</div>"
            f"<span style='width:55px;text-align:right;color:#93c5fd;font-size:0.9em'>{row['leite']:.0f} L</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
else:
    st.caption("Nenhuma ordenha registrada hoje ainda.")

# ── Atualizar ─────────────────────────────────
st.divider()
if st.button("Atualizar dados", use_container_width=True):
    carregar_dados()
    st.rerun()

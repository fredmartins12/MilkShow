"""
Configurações — Parâmetros do sistema, alertas, integrações e reset seguro.
"""
import streamlit as st
import datetime
import time
import re
import os
import subprocess
import firebase_admin
from firebase_admin import firestore

from utils import (
    init_firebase, carregar_dados, apply_theme, page_banner,
    get_config, set_config, limpar_banco_completo,
    PRECO_PADRAO_LEITE,
    enviar_email_alertas,
    processar_alertas,
)

st.set_page_config(page_title="MilkShow | Configurações", layout="wide", page_icon="⚙️")
apply_theme()
init_firebase()
carregar_dados()

st.sidebar.markdown(
    '<div class="sidebar-title">MilkShow</div>'
    '<div class="sidebar-sub">Configurações</div>',
    unsafe_allow_html=True,
)
page_banner("", "Configurações do Sistema", "Parâmetros, integrações, alertas e administração")

tab_geral, tab_email, tab_bot, tab_preco, tab_perigo = st.tabs([
    "Geral",
    "E-mail / Alertas",
    "Bot IA (WhatsApp)",
    "Preços por Período",
    "Zona de Perigo",
])

# ══════════════════════════════════════════════
# TAB GERAL
# ══════════════════════════════════════════════
with tab_geral:
    st.subheader("Parâmetros da Fazenda")
    with st.form("cfg_geral"):
        nome_fazenda = st.text_input(
            "Nome da Fazenda:",
            value=get_config('nome_fazenda', 'Minha Fazenda'),
        )
        preco_leite = st.number_input(
            "Preço padrão do leite (R$/L):",
            min_value=0.50, max_value=10.0, step=0.05,
            value=float(get_config('preco_leite', PRECO_PADRAO_LEITE)),
        )
        if st.form_submit_button("Salvar", type="primary"):
            set_config('nome_fazenda', nome_fazenda)
            set_config('preco_leite',  preco_leite)
            st.success("Configurações salvas!")

# ══════════════════════════════════════════════
# TAB EMAIL
# ══════════════════════════════════════════════
with tab_email:
    st.subheader("Configurar E-mail para Alertas")
    st.info(
        "Configure um servidor SMTP para receber alertas veterinários por e-mail. "
        "Gmail: smtp.gmail.com / porta 587. Use uma senha de app, não a senha normal."
    )
    with st.form("cfg_email"):
        smtp_host = st.text_input("Servidor SMTP:",    value=get_config('smtp_host', 'smtp.gmail.com'))
        smtp_port = st.number_input("Porta:",          value=int(get_config('smtp_port', 587)), step=1)
        smtp_user = st.text_input("E-mail remetente:", value=get_config('smtp_user', ''))
        smtp_pass = st.text_input("Senha de App:",     value=get_config('smtp_pass', ''), type="password")
        email_d   = st.text_input("E-mail destino:",   value=get_config('email_dest', ''))

        if st.form_submit_button("Salvar Configurações de E-mail", type="primary"):
            set_config('smtp_host',  smtp_host)
            set_config('smtp_port',  smtp_port)
            set_config('smtp_user',  smtp_user)
            set_config('smtp_pass',  smtp_pass)
            set_config('email_dest', email_d)
            st.success("Configurações salvas!")

    if st.button("Testar Envio de E-mail"):
        alertas = processar_alertas()
        if not alertas:
            alertas = [{"nivel": "atencao", "msg": "Teste de e-mail", "detalhe": "Configuração funcionando!"}]
        ok, msg = enviar_email_alertas(alertas)
        st.success(msg) if ok else st.error(msg)


# ══════════════════════════════════════════════
# HELPERS do Bot IA
# ══════════════════════════════════════════════
def _normalizar_tel(numero: str) -> str:
    """Remove tudo que não é dígito e garante prefixo 55."""
    digits = re.sub(r'\D', '', numero.strip())
    if digits.startswith('55') and len(digits) >= 12:
        return digits
    return '55' + digits


def _registrar_telefone(tel_limpo: str, fazenda_id: str = 'default'):
    """Salva o mapeamento telefone → fazenda no Firestore global."""
    try:
        db = firestore.client()
        db.collection('registros_tel').document(tel_limpo).set({
            'fazenda_id': fazenda_id,
            'ativo': True,
            'ts': datetime.datetime.now().isoformat(),
        })
        return True
    except Exception as e:
        st.error(f"Erro ao registrar: {e}")
        return False


def _historico_bot():
    try:
        db = firestore.client()
        return list(db.collection('conversas_bot').order_by(
            'ts', direction=firestore.Query.DESCENDING
        ).limit(20).stream())
    except Exception:
        return []


# ══════════════════════════════════════════════
# TAB BOT IA
# ══════════════════════════════════════════════
with tab_bot:

    # ── Seção 1: Cadastro do número ───────────
    with st.container(border=True):
        st.markdown("#### Seu número do WhatsApp")
        st.caption(
            "Informe o número que você usa no WhatsApp. "
            "Quando você enviar uma mensagem para o número do MilkShow, "
            "o sistema identifica automaticamente que é você e salva os dados na sua fazenda."
        )

        tel_salvo = get_config('telefone_wpp', '')
        tel_exibir = tel_salvo[2:] if tel_salvo.startswith('55') else tel_salvo  # remove 55 pra exibir

        col_tel, col_status = st.columns([3, 1])
        with col_tel:
            novo_tel = st.text_input(
                "Número (somente dígitos, com DDD):",
                value=tel_exibir,
                placeholder="77981258479",
                help="Digite apenas números. Exemplo: 77981258479",
            )
        with col_status:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if tel_salvo:
                st.markdown(
                    f"<div style='background:rgba(16,185,129,0.12);border:1px solid rgba(16,185,129,0.25);"
                    f"border-radius:8px;padding:8px 12px;font-size:0.84em;color:#6ee7b7;'>"
                    f"Ativo: +{tel_salvo}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div style='background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.2);"
                    "border-radius:8px;padding:8px 12px;font-size:0.84em;color:#fcd34d;'>"
                    "Sem número cadastrado</div>",
                    unsafe_allow_html=True,
                )

        if st.button("Salvar número", type="primary"):
            if novo_tel:
                tel_clean = _normalizar_tel(novo_tel)
                if len(tel_clean) < 12 or len(tel_clean) > 14:
                    st.error("Número inválido. Inclua DDD + número (ex: 77981258479).")
                else:
                    set_config('telefone_wpp', tel_clean)
                    _registrar_telefone(tel_clean)
                    st.success(f"Número +{tel_clean} cadastrado. Agora você pode usar o bot.")
                    time.sleep(0.8)
                    st.rerun()
            else:
                st.warning("Digite o número antes de salvar.")

    # ── Seção 2: Como usar ────────────────────
    with st.container(border=True):
        st.markdown("#### Como usar o Bot")
        st.markdown(
            "Envie mensagens de texto (ou áudio) para o número do MilkShow no WhatsApp "
            "e o sistema registra automaticamente em sua fazenda.\n\n"
            "**Exemplos do que você pode enviar:**"
        )
        exemplos = [
            ("Compras", "Comprei 5 sacos de ração por R$300 no agropecuário"),
            ("Compras", "Comprei ocitocina 3 vidros por R$45"),
            ("Sanidade", "Apliquei ivermectina no rebanho todo, custou R$80"),
            ("Sanidade", "Apliquei cortvet na Mansinha, 2 doses, R$25"),
            ("Gastos", "Paguei R$400 de mão de obra hoje"),
            ("Gastos", "Conta de luz da fazenda: R$180"),
            ("Leite", "Vendi 1200 litros por R$1800"),
            ("Consultas", "estoque  —  ver o que tem no armazém"),
        ]
        for cat, ex in exemplos:
            st.markdown(
                f"<div style='display:flex;gap:10px;margin-bottom:5px;'>"
                f"<span style='background:rgba(59,130,246,0.12);border-radius:6px;padding:2px 8px;"
                f"font-size:0.74em;color:#93c5fd;font-weight:600;white-space:nowrap;'>{cat}</span>"
                f"<span style='color:#94a3b8;font-size:0.88em;font-style:italic;'>{ex}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
        st.markdown("")
        st.caption(
            "O bot entende linguagem natural, pergunta campos que faltarem, "
            "mostra um resumo e só salva após sua confirmação."
        )

    # ── Seção 3: Chave de IA (avançado) ──────
    with st.expander("Configurações avançadas (chave de IA)"):
        st.caption(
            "O MilkShow usa Claude (Anthropic) para processar as mensagens. "
            "Normalmente esta chave já está configurada pelo administrador do sistema. "
            "Preencha somente se você recebeu uma chave própria."
        )
        with st.form("cfg_bot_keys"):
            anthropic_key = st.text_input(
                "ANTHROPIC_API_KEY:",
                value=get_config('anthropic_key', ''),
                type="password",
            )
            openai_key = st.text_input(
                "OPENAI_API_KEY (opcional — para transcrição de áudio):",
                value=get_config('openai_key', ''),
                type="password",
            )
            ngrok_token = st.text_input(
                "NGROK_AUTHTOKEN (opcional — túnel automático):",
                value=get_config('ngrok_token', ''),
                type="password",
                help="Crie conta gratuita em ngrok.com e copie o token em Dashboard → Your Authtoken",
            )
            if st.form_submit_button("Salvar chaves"):
                set_config('anthropic_key', anthropic_key)
                set_config('openai_key',    openai_key)
                set_config('ngrok_token',   ngrok_token)
                # Injeta como variável de ambiente para o processo atual
                if anthropic_key:
                    os.environ['ANTHROPIC_API_KEY'] = anthropic_key
                if ngrok_token:
                    os.environ['NGROK_AUTHTOKEN'] = ngrok_token
                st.success("Chaves salvas!")

    # ── Seção 4: Iniciar / Parar servidor bot ──
    st.divider()
    with st.container(border=True):
        st.markdown("#### Servidor do Bot (local)")
        st.caption(
            "Inicie o servidor para receber mensagens do WhatsApp. "
            "Após iniciar, use um túnel como ngrok para expor a porta pública. "
            "Exemplo: ngrok http 8000 — copie a URL e configure no Twilio como webhook."
        )

        if 'bot_proc' not in st.session_state:
            st.session_state.bot_proc = None

        col_porta, col_btn = st.columns([2, 3])
        porta = col_porta.number_input("Porta:", value=8000, step=1, min_value=1024, max_value=65535)

        rodando = st.session_state.bot_proc is not None and st.session_state.bot_proc.poll() is None

        with col_btn:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if rodando:
                st.markdown(
                    "<div style='background:rgba(16,185,129,0.12);border:1px solid rgba(16,185,129,0.3);"
                    "border-radius:8px;padding:8px 14px;font-size:0.84em;color:#6ee7b7;display:inline-block;'>"
                    f"Servidor rodando na porta {porta}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div style='background:rgba(100,116,139,0.1);border:1px solid rgba(100,116,139,0.2);"
                    "border-radius:8px;padding:8px 14px;font-size:0.84em;color:#94a3b8;display:inline-block;'>"
                    "Servidor parado</div>",
                    unsafe_allow_html=True,
                )

        b_ini, b_par = st.columns(2)
        if b_ini.button("Iniciar Bot", type="primary", disabled=rodando, use_container_width=True):
            bot_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "whatsapp_bot.py")
            import sys
            proc = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "whatsapp_bot:app",
                 "--host", "0.0.0.0", "--port", str(int(porta))],
                cwd=os.path.dirname(os.path.dirname(__file__)),
            )
            st.session_state.bot_proc = proc
            st.success(f"Servidor iniciado! PID {proc.pid} — porta {int(porta)}")
            time.sleep(0.6)
            st.rerun()

        if b_par.button("Parar Bot", disabled=not rodando, use_container_width=True):
            try:
                st.session_state.bot_proc.terminate()
                st.session_state.bot_proc.wait(timeout=5)
            except Exception:
                pass
            st.session_state.bot_proc = None
            st.warning("Servidor parado.")
            time.sleep(0.6)
            st.rerun()

        if rodando:
            # Tenta ler a URL do ngrok salva no Firebase pelo bot
            ngrok_url = ""
            try:
                db = firestore.client()
                doc = db.collection("config").document("ngrok_url").get()
                if doc.exists:
                    ngrok_url = doc.to_dict().get("url", "")
            except Exception:
                pass

            if ngrok_url:
                st.success(f"Webhook ativo: `{ngrok_url}`")
                st.caption("Cole esta URL no Twilio Console → Phone Numbers → Seu número → Messaging → Webhook.")
            else:
                st.info(
                    "Para expor o bot publicamente, defina a variável de ambiente "
                    "`NGROK_AUTHTOKEN` com seu token do ngrok.com (plano gratuito) "
                    "e reinicie o servidor — a URL aparecerá aqui automaticamente.\n\n"
                    "Ou abra outro terminal e rode: `ngrok http 8080`"
                )

    # ── Seção 4b: Alertas proativos ──────────
    st.divider()
    with st.container(border=True):
        st.markdown("#### Alertas Proativos por WhatsApp")
        st.caption(
            "Configure para o bot enviar alertas automaticamente todo dia às 7h "
            "e um relatório semanal toda segunda-feira. "
            "Requer TWILIO_ACCOUNT_SID e TWILIO_AUTH_TOKEN."
        )
        with st.form("cfg_twilio"):
            t1, t2 = st.columns(2)
            twilio_sid   = t1.text_input("TWILIO_ACCOUNT_SID:", value=get_config('twilio_sid', ''), type="password")
            twilio_token = t2.text_input("TWILIO_AUTH_TOKEN:", value=get_config('twilio_token', ''), type="password")
            twilio_from  = st.text_input(
                "Número remetente (Twilio):",
                value=get_config('twilio_from', '+14155238886'),
                help="Número do Twilio WhatsApp sandbox ou número próprio"
            )
            if st.form_submit_button("Salvar credenciais Twilio"):
                set_config('twilio_sid',   twilio_sid)
                set_config('twilio_token', twilio_token)
                set_config('twilio_from',  twilio_from)
                if twilio_sid:   os.environ['TWILIO_ACCOUNT_SID'] = twilio_sid
                if twilio_token: os.environ['TWILIO_AUTH_TOKEN']  = twilio_token
                if twilio_from:  os.environ['TWILIO_FROM']        = f"whatsapp:{twilio_from}"
                st.success("Credenciais Twilio salvas!")

        st.divider()
        st.caption("Disparar manualmente (para testar):")
        ca, cb = st.columns(2)
        if ca.button("Disparar Alertas Agora", use_container_width=True):
            try:
                import httpx
                r = httpx.post("http://localhost:8080/disparar_alertas", timeout=15)
                res = r.json()
                enviados = sum(1 for x in res.get("disparados", []) if x.get("enviado"))
                st.success(f"Alertas disparados para {enviados} número(s).")
            except Exception as e:
                st.error(f"Erro: {e} — verifique se o bot está rodando.")
        if cb.button("Enviar Relatório Semanal Agora", use_container_width=True):
            try:
                import httpx
                r = httpx.post("http://localhost:8080/relatorio_semanal", timeout=15)
                res = r.json()
                enviados = sum(1 for x in res.get("disparados", []) if x.get("enviado"))
                st.success(f"Relatório enviado para {enviados} número(s).")
            except Exception as e:
                st.error(f"Erro: {e} — verifique se o bot está rodando.")

    # ── Seção 5: Histórico de conversas ──────
    st.divider()
    st.markdown("#### Histórico de Conversas")
    try:
        docs = _historico_bot()
        if docs:
            import pandas as pd
            rows = []
            for d in docs:
                d_dict = d.to_dict()
                tel_raw = d.id
                # Formata como (XX) XXXXX-XXXX
                tel_fmt = tel_raw[2:] if tel_raw.startswith('55') else tel_raw
                if len(tel_fmt) == 11:
                    tel_fmt = f"({tel_fmt[:2]}) {tel_fmt[2:7]}-{tel_fmt[7:]}"
                rows.append({
                    "Número":           tel_fmt,
                    "Estado":           d_dict.get("estado", "—"),
                    "Tipo Pendente":    d_dict.get("tipo",   "—"),
                    "Última Atividade": d_dict.get("ts", "—")[:16],
                })
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        else:
            st.caption("Nenhuma conversa registrada ainda.")
    except Exception:
        st.caption("Histórico indisponível — verifique a conexão com o Firebase.")

# ══════════════════════════════════════════════
# TAB PREÇOS POR PERÍODO
# ══════════════════════════════════════════════
with tab_preco:
    st.subheader("Tabela de Preços do Leite por Período")
    st.caption(
        "Registre aqui o preço real recebido por litro em cada mês. "
        "O BI usará automaticamente esses valores nos cálculos de rentabilidade."
    )

    import pandas as pd
    precos_cfg = [c for c in st.session_state.db.get('config', [])
                  if str(c.get('chave', '')).startswith('preco_periodo_')]

    if precos_cfg:
        df_precos = pd.DataFrame([
            {
                "Período": c['chave'].replace('preco_periodo_', ''),
                "Preço (R$/L)": c['valor'],
                "doc_id": c['doc_id'],
            }
            for c in precos_cfg
        ]).sort_values("Período", ascending=False)
        st.dataframe(
            df_precos.drop(columns=['doc_id']),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Nenhum preço por período cadastrado ainda.")

    st.divider()
    with st.form("cfg_preco_periodo"):
        cp1, cp2 = st.columns(2)
        mes_ref  = cp1.date_input("Mês de Referência:", datetime.date.today().replace(day=1))
        preco_p  = cp2.number_input("Preço (R$/L):", min_value=0.5, max_value=10.0,
                                     step=0.05, value=float(get_config('preco_leite', PRECO_PADRAO_LEITE)))
        if st.form_submit_button("Adicionar Preço", type="primary"):
            chave = f"preco_periodo_{mes_ref.strftime('%Y-%m')}"
            set_config(chave, preco_p)
            st.success(f"Preço de R$ {preco_p:.2f}/L registrado para {mes_ref.strftime('%m/%Y')}!")
            time.sleep(0.8)
            st.rerun()

# ══════════════════════════════════════════════
# TAB ZONA DE PERIGO
# ══════════════════════════════════════════════
with tab_perigo:
    st.subheader("Zona de Perigo")
    st.error(
        "**ATENÇÃO:** Esta ação apagará **TODOS** os dados do sistema — "
        "animais, financeiro, estoque, produção e sanitário. "
        "Esta operação é **IRREVERSÍVEL** e não pode ser desfeita!"
    )

    st.markdown("---")
    st.markdown("Para confirmar, **digite exatamente** `CONFIRMAR RESET` no campo abaixo:")
    confirmacao = st.text_input("Confirmação:", placeholder="CONFIRMAR RESET")

    if st.button("Apagar Tudo — Reset de Fábrica", type="primary"):
        if confirmacao == "CONFIRMAR RESET":
            with st.spinner("Apagando todos os dados..."):
                limpar_banco_completo()
            st.success("Banco de dados resetado com sucesso!")
            time.sleep(2)
            st.rerun()
        else:
            st.error(
                "Texto de confirmação incorreto. "
                "Digite exatamente: **CONFIRMAR RESET**"
            )

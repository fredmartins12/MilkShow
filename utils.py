"""
utils.py — MilkShow shared module
Firebase connection, CRUD operations, constants, CSS theme and helper functions.
"""
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import datetime
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import io
import json
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import timedelta

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
DIAS_PVE        = 45
DIAS_DIAGNOSTICO = 30
DIAS_SECAGEM    = 60
GESTACAO        = 283
DIAS_DESMAME    = 90
PRECO_PADRAO_LEITE = 2.50
DENSIDADE_LEITE = 1.032
BASE_PASTO_LITROS = 4.0
FATOR_CONVERSAO  = 3.0
MAXIMO_POR_REFEICAO = 6.0

CATEGORIAS_RECEITA  = ["Venda de Leite", "Venda de Animais", "Serviços", "Outras Receitas"]
CATEGORIAS_DESPESA  = ["Ração / Nutrição", "Medicamento / Sanitário", "Infraestrutura",
                       "Mão de Obra", "Energia", "Compra de Animais", "Outros"]
CATEGORIAS_FINANCEIRAS = CATEGORIAS_RECEITA + CATEGORIAS_DESPESA
TIPOS_SANITARIOS = ["Vacina", "Vermífugo", "Antibiótico", "Hormônio", "Casqueamento", "Outros"]
COLECOES = ["animais", "financeiro", "estoque", "producao", "sanitario", "config", "logs"]
CACHE_TTL_SEGUNDOS = 60   # recarrega dados do Firebase a cada 60s

# ─────────────────────────────────────────────
# FIREBASE
# ─────────────────────────────────────────────
@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        try:
            # 1) Tenta st.secrets (pode não existir em dev local)
            firebase_key_secret = None
            try:
                if "FIREBASE_KEY" in st.secrets:
                    firebase_key_secret = st.secrets["FIREBASE_KEY"]
            except Exception:
                pass  # secrets.toml ausente — tudo bem, tenta firebase_key.json

            if firebase_key_secret is not None:
                import json
                val = firebase_key_secret
                if isinstance(val, str):
                    val = val.replace("'", '"')
                    key_dict = json.loads(val)
                else:
                    key_dict = dict(val)
                if "private_key" in key_dict:
                    key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")
                cred = credentials.Certificate(key_dict)
                firebase_admin.initialize_app(cred)
            # 2) Tenta arquivo local firebase_key.json
            elif os.path.exists("firebase_key.json"):
                cred = credentials.Certificate("firebase_key.json")
                firebase_admin.initialize_app(cred)
            else:
                st.error("Chave do Firebase não encontrada! Coloque o arquivo **firebase_key.json** na pasta do projeto ou configure os Secrets.")
                st.stop()
        except Exception as e:
            st.error(f"Erro crítico na conexão Firebase: {e}")
            st.stop()
    return firestore.client()


def get_db():
    return init_firebase()

# ─────────────────────────────────────────────
# CRUD
# ─────────────────────────────────────────────
def _fazenda_id() -> str:
    """Returns current farm ID (supports multi-farm)."""
    return st.session_state.get('fazenda_id', 'default')


def _coll(db, nome: str):
    """Returns Firestore collection scoped to the current farm."""
    fid = _fazenda_id()
    if fid == 'default':
        return db.collection(nome)
    return db.collection('fazendas').document(fid).collection(nome)


def carregar_dados(force: bool = False):
    """Load all collections from Firestore. Respects CACHE_TTL_SEGUNDOS."""
    agora = datetime.datetime.now().timestamp()
    ultimo = st.session_state.get('_data_ts', 0)
    expirado = (agora - ultimo) > CACHE_TTL_SEGUNDOS

    if force or 'db' not in st.session_state or expirado:
        db = get_db()
        st.session_state.db = {col: [] for col in COLECOES}
        for col in COLECOES:
            try:
                docs = _coll(db, col).stream()
                for doc in docs:
                    d = doc.to_dict()
                    d['doc_id'] = doc.id
                    st.session_state.db[col].append(d)
            except Exception:
                pass
        st.session_state['_data_ts'] = agora


def _registrar_log(acao: str, colecao: str, detalhe: str = ''):
    """Write an audit log entry (fire-and-forget, never raises)."""
    try:
        db = get_db()
        usuario = st.session_state.get('usuario_email', 'sistema')
        entry = {
            'ts':       datetime.datetime.now().isoformat(),
            'usuario':  usuario,
            'acao':     acao,
            'colecao':  colecao,
            'detalhe':  detalhe[:200],
        }
        _coll(db, 'logs').add(entry)
        if 'logs' not in st.session_state.db:
            st.session_state.db['logs'] = []
        entry['doc_id'] = ''
        st.session_state.db['logs'].append(entry)
    except Exception:
        pass


def adicionar_item(colecao, dados):
    db = get_db()
    ref = _coll(db, colecao).add(dados)
    dados['doc_id'] = ref[1].id
    if colecao not in st.session_state.db:
        st.session_state.db[colecao] = []
    st.session_state.db[colecao].append(dados)
    _registrar_log('ADD', colecao, str(dados.get('nome') or dados.get('desc') or dados.get('chave') or '')[:80])


def atualizar_item(colecao, doc_id, novos_dados):
    db = get_db()
    _coll(db, colecao).document(doc_id).update(novos_dados)
    for i, item in enumerate(st.session_state.db[colecao]):
        if item.get('doc_id') == doc_id:
            st.session_state.db[colecao][i].update(novos_dados)
            break
    _registrar_log('UPDATE', colecao, f'doc={doc_id} {list(novos_dados.keys())}')


def deletar_item(colecao, doc_id):
    db = get_db()
    _coll(db, colecao).document(doc_id).delete()
    deletado = next((d for d in st.session_state.db.get(colecao, []) if d.get('doc_id') == doc_id), {})
    st.session_state.db[colecao] = [
        d for d in st.session_state.db[colecao] if d.get('doc_id') != doc_id
    ]
    _registrar_log('DELETE', colecao, str(deletado.get('nome') or deletado.get('id') or doc_id)[:80])


def salvar_lote(colecao, dados_editados):
    db = get_db()
    batch = db.batch()
    count = 0
    for row in dados_editados:
        if row.get('doc_id'):
            ref = _coll(db, colecao).document(row['doc_id'])
            batch.set(ref, row, merge=True)
            count += 1
            if count >= 400:
                batch.commit()
                batch = db.batch()
                count = 0
    if count > 0:
        batch.commit()
    _registrar_log('BATCH_SAVE', colecao, f'{count} registros')
    del st.session_state.db
    st.rerun()


def limpar_banco_completo():
    db = get_db()
    batch = db.batch()
    count = 0
    for col in COLECOES:
        for doc in _coll(db, col).list_documents():
            batch.delete(doc)
            count += 1
            if count >= 400:
                batch.commit()
                batch = db.batch()
                count = 0
    if count > 0:
        batch.commit()
    del st.session_state.db

# ─────────────────────────────────────────────
# CONFIG STORE
# ─────────────────────────────────────────────
def get_config(chave, default=None):
    for c in st.session_state.db.get('config', []):
        if c.get('chave') == chave:
            return c.get('valor', default)
    return default


def set_config(chave, valor):
    for c in st.session_state.db.get('config', []):
        if c.get('chave') == chave:
            atualizar_item('config', c['doc_id'], {'valor': valor})
            return
    adicionar_item('config', {'chave': chave, 'valor': valor})

# ─────────────────────────────────────────────
# BUSINESS LOGIC
# ─────────────────────────────────────────────
def calcular_meta_racao(prod_anterior: float) -> float:
    """Returns the daily feed target (kg) based on previous day's milk production."""
    return max((prod_anterior - BASE_PASTO_LITROS) / FATOR_CONVERSAO, 0.5)


# Categorias que envolvem produto físico (devem aparecer no Armazém)
CATEGORIAS_COM_ESTOQUE = {"Ração / Nutrição", "Medicamento / Sanitário"}


def registrar_compra_produto(
    prod_nome: str,
    qtd: float,
    unidade: str,
    valor_total: float,
    cat_fin: str,
    fornecedor: str = '',
    data: str = '',
    desc_extra: str = '',
) -> None:
    """
    Atomic: updates stock (weighted-average) AND creates the financial expense record.
    Called by both Armazém and Financeiro so the logic lives in one place.
    """
    data = data or str(datetime.date.today())
    custo_un = valor_total / qtd if qtd else 0

    # ── stock (média ponderada) ──────────────────
    encontrado = False
    for item in st.session_state.db.get('estoque', []):
        if item['item'].strip().lower() == prod_nome.strip().lower():
            val_ant    = item['qtd'] * item['custo_medio']
            nova_qtd   = item['qtd'] + qtd
            novo_medio = (val_ant + valor_total) / nova_qtd
            atualizar_item('estoque', item['doc_id'], {
                'qtd': nova_qtd, 'custo_medio': novo_medio, 'un': unidade,
            })
            encontrado = True
            break
    if not encontrado:
        adicionar_item('estoque', {
            'item': prod_nome, 'qtd': qtd, 'un': unidade, 'custo_medio': custo_un,
        })

    # ── financial ───────────────────────────────
    desc = desc_extra or f"Compra {prod_nome} ({qtd} {unidade})"
    if fornecedor:
        desc += f" — {fornecedor}"
    adicionar_item('financeiro', {
        'data':   data,
        'cat':    cat_fin,
        'desc':   desc,
        'valor':  valor_total,
        'tipo':   'Geral',
        'animal': None,
        'origem': 'armazem',
    })


def baixar_estoque(item_nome: str, qtd_baixa: float) -> tuple:
    """
    Reduces stock quantity. Returns (success: bool, msg: str).
    """
    for item in st.session_state.db.get('estoque', []):
        if item['item'].strip().lower() == item_nome.strip().lower():
            if item['qtd'] < qtd_baixa:
                return False, f"Estoque insuficiente: disponível {item['qtd']:.1f} {item.get('un','')}"
            nova_qtd = round(item['qtd'] - qtd_baixa, 4)
            atualizar_item('estoque', item['doc_id'], {'qtd': nova_qtd})
            return True, f"Baixa de {qtd_baixa:.1f} realizada. Saldo: {nova_qtd:.1f} {item.get('un','')}"
    return False, f"Produto '{item_nome}' não encontrado no estoque."


def registrar_procedimento_sanitario(
    tipo: str,
    prod: str,
    modo: str,
    animal: str | None,
    custo: float,
    obs: str = '',
    baixar_do_estoque: bool = False,
    qtd_estoque: float = 0.0,
    data: str = '',
) -> list[str]:
    """
    Atomic: creates sanitary record + optional stock deduction + financial record.
    Returns list of warning messages.
    """
    data = data or str(datetime.date.today())
    avisos = []

    # sanitário
    adicionar_item('sanitario', {
        'data':   data,
        'tipo':   tipo,
        'prod':   prod,
        'modo':   modo,
        'animal': animal,
        'custo':  custo,
        'obs':    obs,
    })

    # baixa no estoque
    if baixar_do_estoque and qtd_estoque > 0:
        ok, msg = baixar_estoque(prod, qtd_estoque)
        if not ok:
            avisos.append(f"Estoque: {msg}")

    # financeiro
    if custo > 0:
        adicionar_item('financeiro', {
            'data':   data,
            'cat':    'Medicamento / Sanitário',
            'desc':   f"{tipo} — {prod}",
            'valor':  custo,
            'tipo':   'Geral' if modo == 'Rebanho Todo' else 'Individual',
            'animal': animal,
            'origem': 'sanitario',
        })

    return avisos


def registrar_compra_animal(
    animal_id: str,
    nome: str,
    status: str,
    valor: float,
    lote: str = 'Geral',
    nasc: str = '',
    sexo: str = 'Fêmea',
    fornecedor: str = '',
    data: str = '',
) -> None:
    """
    Atomic: creates animal record + financial expense "Compra de Animais".
    """
    data = data or str(datetime.date.today())

    adicionar_item('animais', {
        'id':      animal_id,
        'nome':    nome,
        'status':  status,
        'lote':    lote,
        'sexo':    sexo,
        'nasc':    nasc or None,
        'freq':    2 if status == 'Lactação' else 0,
        'prenhez': False,
        'dt_parto': None,
        'dt_insem': None,
        'colostro': True,
        'mae_id':  None,
    })

    desc = f"Compra animal: {nome} (#{animal_id})"
    if fornecedor:
        desc += f" — {fornecedor}"
    adicionar_item('financeiro', {
        'data':   data,
        'cat':    'Compra de Animais',
        'desc':   desc,
        'valor':  valor,
        'tipo':   'Geral',
        'animal': animal_id,
        'origem': 'rebanho',
    })


def get_custo_racao():
    """Returns the weighted-average cost of 'ração' from stock. Falls back to R$ 2.00."""
    for item in st.session_state.db.get('estoque', []):
        nome = item.get('item', '').lower()
        if any(k in nome for k in ['ração', 'racao', 'concentrado', 'silagem']):
            c = item.get('custo_medio', 0)
            if c and c > 0:
                return float(c)
    return 2.00


def calcular_saldo():
    df = pd.DataFrame(st.session_state.db['financeiro'])
    if df.empty:
        return 0.0, 0.0, 0.0
    rec  = df[df['cat'].isin(CATEGORIAS_RECEITA)]['valor'].sum()
    desp = df[df['cat'].isin(CATEGORIAS_DESPESA)]['valor'].sum()
    return float(rec - desp), float(rec), float(desp)


def processar_alertas():
    hoje = datetime.date.today()
    alertas = []
    for animal in st.session_state.db.get("animais", []):
        doc_id = animal.get('doc_id')
        nome   = animal.get('nome') or f"Animal {doc_id or '?'}"

        if animal.get('status') in ['Lactação', 'Seca']:
            dt_insem_str = animal.get('dt_insem')
            dt_parto_str = animal.get('dt_parto')

            try:
                d_insem = (datetime.datetime.strptime(dt_insem_str, "%Y-%m-%d").date()
                           if dt_insem_str else None)
            except (ValueError, TypeError):
                d_insem = None

            try:
                d_parto = (datetime.datetime.strptime(dt_parto_str, "%Y-%m-%d").date()
                           if dt_parto_str else None)
            except (ValueError, TypeError):
                d_parto = None

            if d_insem and not animal.get('prenhez'):
                dias = (hoje - d_insem).days
                if dias >= DIAS_DIAGNOSTICO:
                    alertas.append({"nivel": "critico", "msg": f"CONFIRMAR PRENHEZ: {nome}",
                                    "detalhe": f"Inseminada há {dias} dias", "acao": "diagnostico",
                                    "doc_id": doc_id, "animal": nome})

            if not animal.get('prenhez') and not d_insem and d_parto and animal.get('status') == 'Lactação':
                dias = (hoje - d_parto).days
                if dias > DIAS_PVE:
                    alertas.append({"nivel": "critico", "msg": f"INSEMINAR: {nome}",
                                    "detalhe": f"Vazia há {dias} dias", "acao": "inseminar",
                                    "doc_id": doc_id, "animal": nome})

            if animal.get('prenhez') and d_insem and animal.get('status') == 'Lactação':
                prev_parto = d_insem + timedelta(days=GESTACAO)
                dias_secar = (prev_parto - timedelta(days=DIAS_SECAGEM) - hoje).days
                if dias_secar <= 0:
                    alertas.append({"nivel": "critico", "msg": f"SECAR VACA: {nome}",
                                    "detalhe": "Risco para o bezerro!", "acao": "secar",
                                    "doc_id": doc_id, "animal": nome})

        if animal.get('status') == 'Bezerro':
            d_nasc_str = animal.get('nasc') or str(hoje)
            try:
                d_nasc = datetime.datetime.strptime(d_nasc_str, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                continue
            idade = (hoje - d_nasc).days
            if idade <= 2 and not animal.get('colostro'):
                alertas.append({"nivel": "critico", "msg": f"DAR COLOSTRO: {nome}",
                                "detalhe": "Recém-nascido!", "acao": "colostro",
                                "doc_id": doc_id, "animal": nome})
            if idade >= DIAS_DESMAME:
                alertas.append({"nivel": "atencao", "msg": f"DESMAME: {nome}",
                                "detalhe": f"Idade: {idade} dias", "acao": "desmamar",
                                "doc_id": doc_id, "animal": nome})
    return alertas


def calcular_bi(df_prod, df_fin, periodo_ini, periodo_fim):
    if df_prod.empty:
        return None
    custo_racao_kg = get_custo_racao()
    total_leite     = float(df_prod['leite'].sum())
    total_racao_kg  = float(df_prod['racao'].sum())

    receita_leite = 0.0
    p_ini_str = str(periodo_ini)
    p_fim_str = str(periodo_fim)
    if not df_fin.empty:
        for _, row in df_fin.iterrows():
            if row['cat'] == "Venda de Leite":
                ref = str(row.get('ref_ini', ''))
                data = str(row.get('data', ''))
                if ref and ref not in ('None', 'NaT', 'nan') and p_ini_str <= ref <= p_fim_str:
                    receita_leite += row['valor']
                elif (not ref or ref in ('None', 'NaT', 'nan')) and p_ini_str <= data <= p_fim_str:
                    receita_leite += row['valor']

    gastos_fixos = 0.0
    if not df_fin.empty:
        mask = (df_fin['cat'].isin(CATEGORIAS_DESPESA) &
                (df_fin['data'] >= periodo_ini) &
                (df_fin['data'] <= periodo_fim))
        gastos_fixos = float(df_fin[mask]['valor'].sum())

    custo_racao_total = total_racao_kg * custo_racao_kg
    custo_total       = custo_racao_total + gastos_fixos
    preco_medio       = receita_leite / total_leite if total_leite > 0 else 0.0
    custo_litro       = custo_total / total_leite if total_leite > 0 else 0.0
    lucro             = receita_leite - custo_total

    return {
        "receita": receita_leite, "custo_racao": custo_racao_total,
        "gastos_extras": gastos_fixos, "custo_total": custo_total,
        "lucro": lucro, "custo_litro": custo_litro,
        "preco_medio": preco_medio, "producao_total": total_leite,
        "custo_racao_kg": custo_racao_kg,
    }

# ─────────────────────────────────────────────
# SCORE DE SAÚDE DO REBANHO
# ─────────────────────────────────────────────
def calcular_score_rebanho() -> dict:
    """
    Returns a health score 0-100 and a breakdown dict.
    Deductions:
      - Each critical alert : -10 pts (max -40)
      - Each attention alert : -4 pts (max -20)
      - No milk today       : -10 pts
      - Prod drop >20% vs yesterday : -10 pts
      - Uncovered cows today (≥1 lactating with 0 records) : -3 pts each (max -15)
    """
    alertas   = processar_alertas()
    criticos  = sum(1 for a in alertas if a['nivel'] == 'critico')
    atencoes  = sum(1 for a in alertas if a['nivel'] == 'atencao')

    hoje_str  = str(datetime.date.today())
    ontem_str = str(datetime.date.today() - timedelta(days=1))
    df_prod   = pd.DataFrame(st.session_state.db.get('producao', []))

    prod_hoje  = 0.0
    prod_ontem = 0.0
    vacas_sem_ordenha = 0

    lactacao = [a for a in st.session_state.db.get('animais', []) if a.get('status') == 'Lactação']

    if not df_prod.empty:
        df_prod['data'] = df_prod['data'].astype(str)
        prod_hoje  = float(df_prod[df_prod['data'] == hoje_str]['leite'].sum())
        prod_ontem = float(df_prod[df_prod['data'] == ontem_str]['leite'].sum())
        ids_hoje   = set(df_prod[df_prod['data'] == hoje_str]['id_animal'].unique())
        vacas_sem_ordenha = sum(1 for v in lactacao if v['id'] not in ids_hoje)

    score = 100
    detalhes = {}

    d_criticos = min(criticos * 10, 40)
    score -= d_criticos
    detalhes['alertas_criticos'] = {'valor': criticos, 'desconto': d_criticos}

    d_atencoes = min(atencoes * 4, 20)
    score -= d_atencoes
    detalhes['alertas_atencao'] = {'valor': atencoes, 'desconto': d_atencoes}

    d_sem_leite = 10 if prod_hoje == 0 and lactacao else 0
    score -= d_sem_leite
    detalhes['sem_producao_hoje'] = {'valor': int(prod_hoje == 0), 'desconto': d_sem_leite}

    d_queda = 0
    if prod_ontem > 0 and prod_hoje < prod_ontem * 0.80:
        d_queda = 10
    score -= d_queda
    detalhes['queda_producao'] = {'valor': round((prod_ontem - prod_hoje) / max(prod_ontem, 1) * 100, 1), 'desconto': d_queda}

    d_vacas = min(vacas_sem_ordenha * 3, 15)
    score -= d_vacas
    detalhes['vacas_sem_ordenha'] = {'valor': vacas_sem_ordenha, 'desconto': d_vacas}

    score = max(score, 0)

    if score >= 85:
        cor, icone, label = '#10b981', '', 'Excelente'
    elif score >= 65:
        cor, icone, label = '#f59e0b', '', 'Atenção'
    else:
        cor, icone, label = '#ef4444', '', 'Crítico'

    return {
        'score': score,
        'cor': cor,
        'icone': icone,
        'label': label,
        'detalhes': detalhes,
    }


# ─────────────────────────────────────────────
# FIREBASE AUTH (REST)
# ─────────────────────────────────────────────
def firebase_login(email: str, senha: str) -> tuple[bool, str]:
    """Authenticates via Firebase Auth REST API. Returns (ok, error_msg)."""
    import urllib.request
    api_key = _secret('FIREBASE_API_KEY', '')
    if not api_key:
        # try reading from firebase_key.json project_id isn't the api key; skip auth
        return True, ''   # no key configured → bypass (dev mode)

    url = f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}'
    payload = json.dumps({'email': email, 'password': senha, 'returnSecureToken': True}).encode()
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
            st.session_state['usuario_email'] = data.get('email', email)
            st.session_state['auth_token']    = data.get('idToken', '')
            return True, ''
    except Exception as e:
        msg = str(e)
        try:
            import urllib.error
            if isinstance(e, urllib.error.HTTPError):
                body = json.loads(e.read())
                msg = body.get('error', {}).get('message', msg)
        except Exception:
            pass
        return False, msg


def requer_autenticacao() -> bool:
    """
    If FIREBASE_API_KEY is configured, gate the app behind a login form.
    Returns True if user is authenticated (or no key configured).
    """
    api_key = _secret('FIREBASE_API_KEY', '')
    if not api_key:
        return True   # auth not configured → open access

    if st.session_state.get('auth_token'):
        return True

    st.markdown(
        '<div style="max-width:380px;margin:80px auto 0;">', unsafe_allow_html=True
    )
    st.markdown("## MilkShow")
    with st.form('login_form'):
        email = st.text_input('E-mail')
        senha = st.text_input('Senha', type='password')
        if st.form_submit_button('Entrar', type='primary', use_container_width=True):
            ok, err = firebase_login(email, senha)
            if ok:
                st.rerun()
            else:
                st.error(f'{err}')
    st.markdown('</div>', unsafe_allow_html=True)
    return False


# ─────────────────────────────────────────────
# SIDEBAR MINI-RESUMO
# ─────────────────────────────────────────────
def sidebar_mini_resumo():
    """Renders a compact KPI strip at the bottom of the sidebar."""
    animais = st.session_state.db.get('animais', [])
    lact    = sum(1 for a in animais if a.get('status') == 'Lactação')
    total   = len(animais)

    hoje_str = str(datetime.date.today())
    df_prod  = pd.DataFrame(st.session_state.db.get('producao', []))
    prod_hoje = 0.0
    if not df_prod.empty:
        df_prod['data'] = df_prod['data'].astype(str)
        prod_hoje = float(df_prod[df_prod['data'] == hoje_str]['leite'].sum())

    saldo, _, _ = calcular_saldo()
    saldo_cor   = '#43a047' if saldo >= 0 else '#ef5350'

    score = calcular_score_rebanho()

    st.sidebar.markdown('---')
    st.sidebar.markdown(
        f"""
        <div style="padding:8px 4px 4px; font-size:0.78em; color:#64748b;">
          <div style="display:flex;justify-content:space-between;margin-bottom:5px;">
            <span>Rebanho</span><strong style="color:#cbd5e1;">{lact}/{total}</strong>
          </div>
          <div style="display:flex;justify-content:space-between;margin-bottom:5px;">
            <span>Produção hoje</span><strong style="color:#cbd5e1;">{prod_hoje:.0f} L</strong>
          </div>
          <div style="display:flex;justify-content:space-between;margin-bottom:10px;">
            <span>Saldo</span><strong style="color:{saldo_cor};">R$ {saldo:,.0f}</strong>
          </div>
          <div style="background:rgba(255,255,255,0.04);border-radius:8px;padding:8px 12px;
                      border:1px solid rgba(255,255,255,0.08);text-align:center;">
            <span style="font-size:0.82em;color:#475569;display:block;margin-bottom:4px;">Saúde do Rebanho</span>
            <strong style="font-size:1.4em;color:{score['cor']};">{score['score']}</strong>
            <span style="color:{score['cor']};font-size:0.78em;"> / 100 · {score['label']}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# TOAST NOTIFICATIONS
# ─────────────────────────────────────────────
def toast(mensagem: str, tipo: str = 'success'):
    """
    Shows a floating toast notification via injected JS/CSS.
    tipo: 'success' | 'error' | 'warning' | 'info'
    """
    cores = {
        'success': ('#052e16', '#6ee7b7', ''),
        'error':   ('#3b0000', '#fca5a5', ''),
        'warning': ('#361e00', '#fcd34d', ''),
        'info':    ('#0d3349', '#81d4fa', 'ℹ️'),
    }
    bg, cor, icon = cores.get(tipo, cores['info'])
    html = f"""
    <style>
    @keyframes slideIn {{
      from {{ transform: translateX(120%); opacity: 0; }}
      to   {{ transform: translateX(0);   opacity: 1; }}
    }}
    @keyframes fadeOut {{
      from {{ opacity: 1; }}
      to   {{ opacity: 0; transform: translateX(120%); }}
    }}
    .ms-toast {{
      position: fixed; bottom: 24px; right: 24px; z-index: 99999;
      background: {bg}; color: {cor};
      border: 1px solid {cor}44; border-radius: 12px;
      padding: 14px 20px; font-family: Inter, sans-serif;
      font-size: 14px; font-weight: 500;
      box-shadow: 0 8px 32px rgba(0,0,0,0.5);
      animation: slideIn 0.35s ease, fadeOut 0.4s ease 3.2s forwards;
      max-width: 340px; line-height: 1.5;
    }}
    </style>
    <div class="ms-toast">{icon} {mensagem}</div>
    <script>
      setTimeout(() => {{
        document.querySelectorAll('.ms-toast').forEach(el => el.remove());
      }}, 3700);
    </script>
    """
    components.html(html, height=0)


# ─────────────────────────────────────────────
# KEYBOARD SHORTCUTS
# ─────────────────────────────────────────────
def injetar_atalhos_teclado():
    """
    Injects JS keyboard shortcuts:
      R → click sidebar refresh button
      ? → toggle shortcut help overlay
    """
    components.html("""
    <script>
    document.addEventListener('keydown', function(e) {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      if (e.key === 'r' || e.key === 'R') {
        // find and click the "Atualizar Dados" button
        const btns = window.parent.document.querySelectorAll('button');
        for (const b of btns) {
          if (b.innerText.includes('Atualizar')) { b.click(); break; }
        }
      }
      if (e.key === '?') {
        const existing = window.parent.document.getElementById('ms-help');
        if (existing) { existing.remove(); return; }
        const div = window.parent.document.createElement('div');
        div.id = 'ms-help';
        div.innerHTML = `
          <div style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.7);
                      z-index:99998;display:flex;align-items:center;justify-content:center;">
            <div style="background:#0a1810;border:1px solid #43a047;border-radius:16px;
                        padding:32px 40px;color:#c8e6c9;font-family:Inter,sans-serif;min-width:280px;">
              <h3 style="color:#a5d6a7;margin-top:0;">⌨️ Atalhos de Teclado</h3>
              <p><kbd style="background:#1c3022;padding:2px 8px;border-radius:4px;">R</kbd> — Atualizar dados</p>
              <p><kbd style="background:#1c3022;padding:2px 8px;border-radius:4px;">?</kbd> — Este menu</p>
              <p style="margin-top:20px;font-size:0.8em;color:#4caf50;">Clique em qualquer lugar para fechar</p>
            </div>
          </div>`;
        div.onclick = () => div.remove();
        window.parent.document.body.appendChild(div);
      }
    });
    </script>
    """, height=0)


# ─────────────────────────────────────────────
# AUTO-REFRESH COUNTDOWN
# ─────────────────────────────────────────────
def auto_refresh_contador():
    """Shows a subtle countdown in the sidebar and triggers rerun at TTL."""
    agora   = datetime.datetime.now().timestamp()
    ultimo  = st.session_state.get('_data_ts', agora)
    restam  = max(0, int(CACHE_TTL_SEGUNDOS - (agora - ultimo)))

    st.sidebar.markdown(
        f'<div style="text-align:center;font-size:0.68em;color:#475569;padding:2px 0 8px;">'
        f'Atualiza em {restam}s</div>',
        unsafe_allow_html=True,
    )
    if restam == 0:
        st.session_state.pop('db', None)
        st.rerun()


# ─────────────────────────────────────────────
# RELATÓRIO PDF COMPLETO
# ─────────────────────────────────────────────
def _pdf_txt(text: str) -> str:
    """Sanitize text for fpdf2 Helvetica (Latin-1): replace common Unicode chars."""
    return (str(text)
            .replace('\u2014', ' - ')   # em dash
            .replace('\u2013', '-')      # en dash
            .replace('\u2022', '*')      # bullet
            .replace('\u2019', "'")      # right single quote
            .replace('\u201c', '"')      # left double quote
            .replace('\u201d', '"')      # right double quote
            .replace('\u00b7', '.')      # middle dot
            .encode('latin-1', errors='replace').decode('latin-1'))


def gerar_relatorio_pdf_completo() -> bytes:
    """Generates a full farm management report as PDF."""
    try:
        from fpdf import FPDF
    except ImportError:
        st.warning('Instale fpdf2: pip install fpdf2')
        return b''

    hoje = datetime.date.today()
    nome_fazenda = get_config('nome_fazenda', 'Fazenda')
    animais      = st.session_state.db.get('animais', [])
    alertas      = processar_alertas()
    score        = calcular_score_rebanho()
    saldo, rec, desp = calcular_saldo()

    df_prod = pd.DataFrame(st.session_state.db.get('producao', []))
    prod_30d = 0.0
    prod_hoje_val = 0.0
    if not df_prod.empty:
        df_prod['data'] = df_prod['data'].astype(str)
        ini_30 = str(hoje - timedelta(days=30))
        prod_30d = float(df_prod[df_prod['data'] >= ini_30]['leite'].sum())
        prod_hoje_val = float(df_prod[df_prod['data'] == str(hoje)]['leite'].sum())

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Header
    pdf.set_fill_color(18, 40, 22)
    pdf.rect(0, 0, 210, 35, 'F')
    pdf.set_font('Helvetica', 'B', 18)
    pdf.set_text_color(165, 214, 167)
    pdf.set_xy(10, 8)
    pdf.cell(0, 10, _pdf_txt(f'MilkShow - {nome_fazenda}'), ln=True)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(100, 180, 100)
    pdf.set_x(10)
    pdf.cell(0, 8, _pdf_txt(f'Relatorio Gerencial  -  {hoje.strftime("%d/%m/%Y")}'), ln=True)

    pdf.set_text_color(30, 30, 30)
    pdf.ln(8)

    def section(titulo):
        pdf.set_fill_color(230, 245, 230)
        pdf.set_font('Helvetica', 'B', 11)
        pdf.cell(0, 8, _pdf_txt(titulo), ln=True, fill=True)
        pdf.ln(2)

    def row(label, valor, destaque=False):
        pdf.set_font('Helvetica', 'B' if destaque else '', 9)
        pdf.cell(80, 6, _pdf_txt(label), border='B')
        pdf.cell(0, 6, _pdf_txt(str(valor)), border='B', ln=True)

    # Score
    section('Score de Saúde do Rebanho')
    row('Score Geral', f"{score['score']} / 100 - {score['label']}", destaque=True)
    row('Alertas Críticos', score['detalhes']['alertas_criticos']['valor'])
    row('Alertas de Atenção', score['detalhes']['alertas_atencao']['valor'])
    pdf.ln(4)

    # Rebanho
    section('Rebanho')
    from collections import Counter
    status_count = Counter(a.get('status', '?') for a in animais)
    row('Total de Animais', len(animais))
    for status, qtd in status_count.most_common():
        row(f'  • {status}', qtd)
    pdf.ln(4)

    # Produção
    section('Produção')
    row('Produção Hoje', f'{prod_hoje_val:.1f} L')
    row('Produção Últimos 30 dias', f'{prod_30d:.1f} L')
    row('Média Diária (30d)', f'{prod_30d/30:.1f} L/dia')
    pdf.ln(4)

    # Financeiro
    section('Financeiro')
    row('Receitas Totais',  f'R$ {rec:,.2f}')
    row('Despesas Totais',  f'R$ {desp:,.2f}')
    row('Saldo em Caixa',   f'R$ {saldo:,.2f}', destaque=True)
    pdf.ln(4)

    # Alertas
    if alertas:
        section(f'Alertas Pendentes ({len(alertas)})')
        for a in alertas[:15]:
            icone = '!! ' if a['nivel'] == 'critico' else ' > '
            pdf.set_font('Helvetica', '', 8)
            pdf.cell(0, 5, _pdf_txt(f"{icone}{a['msg']} - {a.get('detalhe','')}"), ln=True)
        if len(alertas) > 15:
            pdf.set_font('Helvetica', 'I', 8)
            pdf.cell(0, 5, f'... e mais {len(alertas)-15} alertas.', ln=True)

    # Footer
    pdf.set_y(-18)
    pdf.set_font('Helvetica', 'I', 7)
    pdf.set_text_color(130, 130, 130)
    pdf.cell(0, 6, _pdf_txt(f'Gerado por MilkShow em {hoje.strftime("%d/%m/%Y")} - gestaodeleite.app'), align='C')

    return bytes(pdf.output())


# ─────────────────────────────────────────────
# ALERTS (EMAIL / WHATSAPP)
# ─────────────────────────────────────────────
def _secret(key: str, default: str = '') -> str:
    """Reads from st.secrets first; falls back to Firestore config."""
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        return get_config(key, default)


def enviar_email_alertas(alertas):
    """Sends alert digest via SMTP. Credentials read from st.secrets (preferred) or config collection."""
    smtp_host   = _secret('smtp_host')
    smtp_port   = int(_secret('smtp_port') or 587)
    smtp_user   = _secret('smtp_user')
    smtp_pass   = _secret('smtp_pass')
    email_dest  = _secret('email_dest')

    if not all([smtp_host, smtp_user, smtp_pass, email_dest]):
        return False, "Configure o e-mail nas Configurações antes de enviar alertas."

    corpo = "\n".join([f"• [{a['nivel'].upper()}] {a['msg']} — {a.get('detalhe','')}"
                       for a in alertas])
    msg = MIMEMultipart()
    msg['From']    = smtp_user
    msg['To']      = email_dest
    msg['Subject'] = f"MilkShow — {len(alertas)} alertas pendentes"
    msg.attach(MIMEText(f"Olá!\n\nAlertas do rebanho:\n\n{corpo}\n\n— MilkShow", 'plain', 'utf-8'))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, email_dest, msg.as_string())
        return True, "E-mail enviado com sucesso!"
    except Exception as e:
        return False, str(e)


def enviar_whatsapp_alertas(alertas):
    """Sends WhatsApp message via Twilio. Credentials read from st.secrets (preferred) or config collection."""
    try:
        from twilio.rest import Client
    except ImportError:
        return False, "Instale twilio: pip install twilio"

    account_sid = _secret('twilio_sid')
    auth_token  = _secret('twilio_token')
    from_num    = _secret('twilio_from')
    to_num      = _secret('twilio_to')

    if not all([account_sid, auth_token, from_num, to_num]):
        return False, "Configure o Twilio nas Configurações."

    linhas = [f"- {a['msg']} : {a.get('detalhe', '')}" for a in alertas]
    corpo  = "\n".join(linhas)
    n      = len(alertas)
    texto  = f"*MilkShow - {n} alertas*\n\n{corpo}"
    try:
        client = Client(account_sid, auth_token)
        client.messages.create(body=texto, from_=f"whatsapp:{from_num}", to=f"whatsapp:{to_num}")
        return True, "WhatsApp enviado com sucesso!"
    except Exception as e:
        return False, str(e)

# ─────────────────────────────────────────────
# EXPORT
# ─────────────────────────────────────────────
def exportar_excel(dfs: dict) -> bytes:
    """
    Receives a dict {sheet_name: DataFrame} and returns an Excel file as bytes.
    """
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        for sheet, df in dfs.items():
            if not df.empty:
                df.to_excel(writer, sheet_name=sheet[:31], index=False)
    return buf.getvalue()


def exportar_pdf_simples(titulo: str, df: pd.DataFrame) -> bytes:
    """Generates a simple PDF table from a DataFrame using fpdf2."""
    try:
        from fpdf import FPDF
    except ImportError:
        st.warning("Exportação PDF indisponível. Instale a dependência: `pip install fpdf2`")
        return b""

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, _pdf_txt(titulo), ln=True)
    pdf.set_font("Helvetica", "", 8)
    pdf.ln(4)

    col_w = min(190 // max(len(df.columns), 1), 40)
    # Header
    pdf.set_fill_color(30, 100, 40)
    pdf.set_text_color(255, 255, 255)
    for col in df.columns:
        pdf.cell(col_w, 7, _pdf_txt(str(col))[:18], border=1, fill=True)
    pdf.ln()
    # Rows
    pdf.set_text_color(0, 0, 0)
    for _, row in df.iterrows():
        for val in row:
            pdf.cell(col_w, 6, _pdf_txt(str(val))[:18], border=1)
        pdf.ln()

    return bytes(pdf.output())

# ─────────────────────────────────────────────
# DATE HELPER
# ─────────────────────────────────────────────
def fmt_date(d):
    if d is None:
        return None
    try:
        if pd.isnull(d):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(d, (pd.Timestamp, datetime.datetime)):
        return d.strftime('%Y-%m-%d')
    if isinstance(d, datetime.date):
        return d.strftime('%Y-%m-%d')
    return str(d).split('T')[0]

# ─────────────────────────────────────────────
# CSS THEME
# ─────────────────────────────────────────────
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ═══════════════════════════════════════════
   BASE
   ═══════════════════════════════════════════ */
*, *::before, *::after { box-sizing: border-box; }

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #0a0d14; }
::-webkit-scrollbar-thumb { background: #2a3347; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #3b4f6e; }

/* ═══════════════════════════════════════════
   APP BACKGROUND
   ═══════════════════════════════════════════ */
.stApp {
    background: #0a0d14;
    background-attachment: fixed;
}
.main .block-container {
    background: transparent;
    padding-top: 1.5rem;
    padding-bottom: 3rem;
    max-width: 1400px;
}

/* ═══════════════════════════════════════════
   SIDEBAR
   ═══════════════════════════════════════════ */
[data-testid="stSidebar"] {
    background: #0d1117 !important;
    border-right: 1px solid rgba(255,255,255,0.07) !important;
    box-shadow: 4px 0 24px rgba(0,0,0,0.4) !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div { color: #94a3b8 !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #e2e8f0 !important; }

/* Sidebar nav links */
[data-testid="stSidebarNavItems"] a {
    border-radius: 8px !important;
    margin: 1px 6px !important;
    padding: 8px 14px !important;
    transition: all 0.15s ease !important;
    border: 1px solid transparent !important;
    color: #94a3b8 !important;
}
[data-testid="stSidebarNavItems"] a:hover {
    background: rgba(255,255,255,0.06) !important;
    color: #e2e8f0 !important;
}
[data-testid="stSidebarNavItems"] a[aria-current="page"] {
    background: rgba(59,130,246,0.12) !important;
    border-color: rgba(59,130,246,0.25) !important;
    color: #93c5fd !important;
}

/* ═══════════════════════════════════════════
   TYPOGRAPHY
   ═══════════════════════════════════════════ */
h1 { color: #f1f5f9 !important; font-weight: 700 !important; letter-spacing: -0.5px !important; line-height: 1.2 !important; }
h2 { color: #e2e8f0 !important; font-weight: 600 !important; letter-spacing: -0.3px !important; }
h3 { color: #cbd5e1 !important; font-weight: 600 !important; }
h4 { color: #94a3b8 !important; font-weight: 600 !important; }
p, li { color: #94a3b8 !important; line-height: 1.6 !important; }

/* ═══════════════════════════════════════════
   METRIC CARDS
   ═══════════════════════════════════════════ */
[data-testid="metric-container"] {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 12px !important;
    padding: 18px 16px !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.3) !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}
[data-testid="metric-container"]:hover {
    border-color: rgba(255,255,255,0.14) !important;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4) !important;
}
[data-testid="stMetricValue"] {
    color: #f1f5f9 !important;
    font-weight: 700 !important;
    font-size: 1.55em !important;
    line-height: 1.2 !important;
    letter-spacing: -0.4px !important;
}
[data-testid="stMetricLabel"] {
    color: #64748b !important;
    font-size: 0.74em !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.7px !important;
    margin-bottom: 4px !important;
}
[data-testid="stMetricDelta"] { font-size: 0.72em !important; font-weight: 500 !important; }

/* ═══════════════════════════════════════════
   BUTTONS
   ═══════════════════════════════════════════ */
.stButton > button {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    color: #cbd5e1 !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 0.86em !important;
    padding: 8px 18px !important;
    transition: all 0.15s ease !important;
}
.stButton > button:hover {
    background: rgba(255,255,255,0.09) !important;
    border-color: rgba(255,255,255,0.18) !important;
    color: #f1f5f9 !important;
}
.stButton > button[kind="primary"] {
    background: #1d4ed8 !important;
    border: 1px solid #2563eb !important;
    color: #fff !important;
    box-shadow: 0 2px 10px rgba(29,78,216,0.35) !important;
}
.stButton > button[kind="primary"]:hover {
    background: #2563eb !important;
    box-shadow: 0 4px 18px rgba(37,99,235,0.45) !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="secondary"] {
    background: transparent !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    color: #94a3b8 !important;
}
.stDownloadButton > button {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    color: #94a3b8 !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    transition: all 0.15s ease !important;
}
.stDownloadButton > button:hover {
    background: rgba(255,255,255,0.09) !important;
    border-color: rgba(255,255,255,0.18) !important;
    color: #e2e8f0 !important;
}

/* ═══════════════════════════════════════════
   INPUTS
   ═══════════════════════════════════════════ */
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea {
    background-color: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    color: #e2e8f0 !important;
    border-radius: 8px !important;
    font-size: 0.9em !important;
    transition: all 0.15s ease !important;
}
[data-baseweb="input"] input:focus,
[data-baseweb="textarea"] textarea:focus {
    border-color: rgba(59,130,246,0.6) !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.12) !important;
}
[data-baseweb="select"] > div {
    background-color: rgba(255,255,255,0.05) !important;
    border-color: rgba(255,255,255,0.1) !important;
    color: #e2e8f0 !important;
    border-radius: 8px !important;
}

/* Input labels */
[data-testid="stSelectbox"] label,
[data-testid="stMultiSelect"] label,
[data-testid="stNumberInput"] label,
[data-testid="stTextInput"] label,
[data-testid="stTextArea"] label,
[data-testid="stDateInput"] label,
[data-testid="stRadio"] label:first-child,
[data-testid="stCheckbox"] label {
    color: #64748b !important;
    font-size: 0.78em !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.6px !important;
}

/* ═══════════════════════════════════════════
   TABS
   ═══════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {
    gap: 2px !important;
    background: rgba(255,255,255,0.03) !important;
    border-bottom: 1px solid rgba(255,255,255,0.08) !important;
    padding: 4px 4px 0 !important;
    border-radius: 10px 10px 0 0 !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 7px 7px 0 0 !important;
    color: #64748b !important;
    border: none !important;
    padding: 9px 18px !important;
    font-weight: 500 !important;
    font-size: 0.85em !important;
    transition: color 0.15s ease !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: #cbd5e1 !important;
    background: rgba(255,255,255,0.04) !important;
}
.stTabs [aria-selected="true"] {
    background: rgba(59,130,246,0.12) !important;
    color: #93c5fd !important;
    border-bottom: 2px solid #3b82f6 !important;
    font-weight: 600 !important;
}

/* ═══════════════════════════════════════════
   CONTAINERS & EXPANDERS
   ═══════════════════════════════════════════ */
[data-testid="stExpander"] {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 10px !important;
    transition: border-color 0.15s ease !important;
}
[data-testid="stExpander"]:hover { border-color: rgba(255,255,255,0.14) !important; }
[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stContainer"] > div {
    border-color: rgba(255,255,255,0.08) !important;
    border-radius: 10px !important;
    background: rgba(255,255,255,0.02) !important;
}

/* ═══════════════════════════════════════════
   DATAFRAME / TABLES
   ═══════════════════════════════════════════ */
[data-testid="stDataFrame"] {
    border-radius: 10px !important;
    overflow: hidden !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    box-shadow: 0 2px 16px rgba(0,0,0,0.3) !important;
}

/* ═══════════════════════════════════════════
   ALERTS
   ═══════════════════════════════════════════ */
[data-testid="stAlert"] { border-radius: 8px !important; }
div[data-testid="stAlert"] > div[role="alert"] { border-radius: 8px !important; }

/* ═══════════════════════════════════════════
   PROGRESS BAR
   ═══════════════════════════════════════════ */
.stProgress > div > div {
    background: linear-gradient(90deg, #1d4ed8, #3b82f6) !important;
    border-radius: 4px !important;
}
.stProgress > div {
    background: rgba(255,255,255,0.07) !important;
    border-radius: 4px !important;
    height: 8px !important;
}

/* ═══════════════════════════════════════════
   DIVIDER
   ═══════════════════════════════════════════ */
hr {
    border: none !important;
    height: 1px !important;
    background: rgba(255,255,255,0.08) !important;
    margin: 20px 0 !important;
}

/* ═══════════════════════════════════════════
   CAPTION / SMALL TEXT
   ═══════════════════════════════════════════ */
.stCaption p,
[data-testid="stCaptionContainer"] p {
    color: #475569 !important;
    font-size: 0.79em !important;
}

/* ═══════════════════════════════════════════
   SIDEBAR BRANDING
   ═══════════════════════════════════════════ */
.sidebar-title {
    font-size: 1.3em;
    font-weight: 700;
    color: #e2e8f0;
    margin-bottom: 2px;
    letter-spacing: -0.4px;
}
.sidebar-sub {
    font-size: 0.68em;
    color: #475569 !important;
    -webkit-text-fill-color: #475569;
    margin-bottom: 18px;
    letter-spacing: 1px;
    text-transform: uppercase;
    font-weight: 500;
}

/* ═══════════════════════════════════════════
   PAGE BANNER
   ═══════════════════════════════════════════ */
.page-banner {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-left: 3px solid #3b82f6;
    border-radius: 10px;
    padding: 20px 28px;
    margin-bottom: 24px;
}
.page-banner h1 {
    margin: 0 0 4px 0 !important;
    font-size: 1.5em !important;
    color: #f1f5f9 !important;
    -webkit-text-fill-color: #f1f5f9 !important;
    font-weight: 700 !important;
    letter-spacing: -0.4px !important;
    line-height: 1.2 !important;
}
.page-banner p {
    margin: 0 !important;
    color: #64748b !important;
    -webkit-text-fill-color: #64748b !important;
    font-size: 0.84em !important;
    font-weight: 400 !important;
}

/* ═══════════════════════════════════════════
   STATUS CHIPS
   ═══════════════════════════════════════════ */
.chip-green  { background: rgba(16,185,129,0.12); color: #6ee7b7; border: 1px solid rgba(16,185,129,0.25); border-radius: 6px; padding: 2px 10px; font-size: 0.75em; font-weight: 600; }
.chip-red    { background: rgba(239,68,68,0.12);  color: #fca5a5; border: 1px solid rgba(239,68,68,0.25);  border-radius: 6px; padding: 2px 10px; font-size: 0.75em; font-weight: 600; }
.chip-yellow { background: rgba(245,158,11,0.12); color: #fcd34d; border: 1px solid rgba(245,158,11,0.25); border-radius: 6px; padding: 2px 10px; font-size: 0.75em; font-weight: 600; }

/* ═══════════════════════════════════════════
   FORM CONTAINER
   ═══════════════════════════════════════════ */
[data-testid="stForm"] {
    background: rgba(255,255,255,0.02) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 10px !important;
}
</style>
"""

def apply_theme():
    st.markdown(_CSS, unsafe_allow_html=True)


def page_banner(icon: str, title: str, subtitle: str = ""):
    st.markdown(
        f'<div class="page-banner"><h1>{title}</h1>'
        f'<p>{subtitle}</p></div>',
        unsafe_allow_html=True
    )


def score_gauge_html(score: int, cor: str, label: str, icone: str) -> str:
    """Returns HTML/SVG circular gauge for the herd health score."""
    import math
    r = 46
    circ = 2 * math.pi * r      # ~289
    dash = (score / 100) * circ
    gap  = circ - dash
    if score >= 80:
        glow    = "rgba(16,185,129,0.30)"
        track   = "#0d1f1a"
        glow2   = "rgba(16,185,129,0.12)"
    elif score >= 60:
        glow    = "rgba(245,158,11,0.28)"
        track   = "#1f1700"
        glow2   = "rgba(245,158,11,0.10)"
    else:
        glow    = "rgba(239,68,68,0.28)"
        track   = "#1f0a0a"
        glow2   = "rgba(239,68,68,0.10)"

    return f"""<div style="
        display:flex;flex-direction:column;align-items:center;justify-content:center;
        background:rgba(255,255,255,0.04);
        border:1px solid rgba(255,255,255,0.1);border-radius:14px;
        padding:28px 24px 24px;
        box-shadow:0 4px 24px rgba(0,0,0,0.5);
        position:relative;overflow:hidden;text-align:center;">
      <div style="font-size:0.65em;color:#475569;text-transform:uppercase;
          letter-spacing:1.5px;margin-bottom:18px;font-weight:600;position:relative;z-index:1;">
        Saúde do Rebanho
      </div>
      <div style="position:relative;width:138px;height:138px;z-index:1;">
        <svg width="138" height="138" viewBox="0 0 138 138" style="transform:rotate(-90deg);">
          <circle cx="69" cy="69" r="{r}" fill="none" stroke="{track}" stroke-width="12"/>
          <circle cx="69" cy="69" r="{r}" fill="none" stroke="url(#sg)" stroke-width="12"
                  stroke-linecap="round"
                  stroke-dasharray="{dash:.2f} {gap:.2f}"
                  style="filter:drop-shadow(0 0 8px {cor});"/>
          <defs>
            <linearGradient id="sg" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="{cor}bb"/>
              <stop offset="100%" stop-color="{cor}"/>
            </linearGradient>
          </defs>
        </svg>
        <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);z-index:2;">
          <div style="font-size:2.6em;font-weight:900;color:{cor};line-height:1;
              letter-spacing:-3px;filter:drop-shadow(0 0 12px {cor}99);">{score}</div>
          <div style="font-size:0.62em;color:#4a8050;font-weight:700;margin-top:1px;letter-spacing:1px;">/ 100</div>
        </div>
      </div>
      <div style="margin-top:16px;font-size:0.92em;font-weight:800;color:{cor};
          letter-spacing:0.4px;text-transform:uppercase;z-index:1;position:relative;
          filter:drop-shadow(0 0 6px {cor}66);">{icone} {label}</div>
    </div>"""

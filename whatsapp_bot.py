"""
whatsapp_bot.py — MilkShow WhatsApp AI Assistant
=================================================
Recebe mensagens do WhatsApp via Twilio / Z-API / Evolution API,
mantém estado da conversa no Firebase e salva registros automaticamente.

Fluxo de IA (menos caro → mais caro):
  Groq LLaMA 3.3 70B (grátis) → Gemini 2.0 Flash (grátis) → Claude Haiku (pago)

Fluxo de WhatsApp (menos caro → mais caro):
  Evolution API (grátis, self-hosted) → Z-API (~R$97/mês) → Twilio (por mensagem)

Setup rápido:
  1. pip install fastapi uvicorn httpx anthropic
  2. Defina no .env: GROQ_API_KEY, GOOGLE_API_KEY, ANTHROPIC_API_KEY, NGROK_AUTHTOKEN
  3. uvicorn whatsapp_bot:app --port 8080

Recursos:
  - Texto em linguagem natural ("comprei ocitocina a 30 reais")
  - Áudio (transcrição via Groq Whisper, grátis — modelo whisper-large-v3-turbo)
  - Foto de nota fiscal (Claude Vision)
  - Agenda do dia/semana, rentabilidade por animal, alertas proativos
  - Cancelamento ("não", "cancela")
  - Listagem de registros recentes ("resumo", "estoque")
"""

import os
import json
import re
import datetime
import threading
from dotenv import load_dotenv
load_dotenv()
import logging
from typing import Optional

import httpx
from fastapi import FastAPI, Form, Response, Request, Header, HTTPException
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("milkshow_bot")

from starlette.middleware.cors import CORSMiddleware
from mobile_api import mobile_router

app = FastAPI(title="MilkShow WhatsApp Bot", version="1.0", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mobile_router)

# Token interno para proteger endpoints administrativos
# Defina BOT_ADMIN_TOKEN no .env — se não definido, endpoints admin ficam desabilitados
_ADMIN_TOKEN = os.environ.get("BOT_ADMIN_TOKEN", "")

def _verificar_admin(authorization: str = Header(default="")):
    """Valida Bearer token para endpoints administrativos."""
    if not _ADMIN_TOKEN:
        raise HTTPException(status_code=503, detail="Admin token não configurado")
    token = authorization.replace("Bearer ", "").strip()
    if token != _ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Não autorizado")


# ─────────────────────────────────────────────
# FIREBASE
# ─────────────────────────────────────────────
def _db():
    if not firebase_admin._apps:
        key_file = os.path.join(os.path.dirname(__file__), "firebase_key.json")
        cred = credentials.Certificate(key_file)
        firebase_admin.initialize_app(cred)
    return firestore.client()


def _normalizar_tel(raw: str) -> str:
    """Strips whatsapp: prefix and non-digits, ensures '55' prefix."""
    digits = re.sub(r'\D', '', raw.replace("whatsapp:", "").strip())
    if not digits.startswith('55'):
        digits = '55' + digits
    return digits


def _variantes_tel(tel: str):
    """Gera todas as variações possíveis do número para lookup."""
    variantes = [tel]
    # Sem código do país
    sem_55 = tel[2:] if tel.startswith('55') else tel
    variantes.append(sem_55)
    # Com/sem nono dígito (DDD + 9 + número)
    # Ex: 557781258479 <-> 5577981258479
    if tel.startswith('55'):
        resto = tel[2:]  # DDD + número
        if len(resto) == 10:  # sem nono dígito → adiciona 9
            com_9 = '55' + resto[:2] + '9' + resto[2:]
            variantes.append(com_9)
            variantes.append(resto[:2] + '9' + resto[2:])
        elif len(resto) == 11 and resto[2] == '9':  # com nono → remove 9
            sem_9 = '55' + resto[:2] + resto[3:]
            variantes.append(sem_9)
            variantes.append(resto[:2] + resto[3:])
    return list(dict.fromkeys(variantes))  # remove duplicatas mantendo ordem


# Mapeamento: tipo de ação → permissão necessária
# Usuários sem "admin" nas permissões são verificados contra este mapa
_PERM_POR_TIPO = {
    "PRODUCAO_LEITE":   "ordenha",
    "PRODUCAO_MULTIPLA":"ordenha",
    "VENDA_LEITE":      "ordenha",
    "NOVO_ANIMAL":      "rebanho",
    "COMPRA_ANIMAL":    "rebanho",
    "VENDA_ANIMAL":     "rebanho",
    "MORTE_ANIMAL":     "rebanho",
    "REPRODUCAO":       "rebanho",
    "GASTO_GERAL":      "financeiro",
    "GASTO_SANITARIO":  "financeiro",
    "COMPRA_PRODUTO":   "armazem",
    "USO_PRODUTO":      "armazem",
}

# Tipos que são apenas consulta — qualquer usuário ativo pode fazer
_TIPOS_CONSULTA = {"RESUMO", "RELATORIO", "CONSULTA", "AGENDA", "ESTOQUE_INFO"}

# Labels amigáveis das permissões (usados no dashboard e nas mensagens)
PERMISSOES_LABELS = {
    "admin":      "Acesso Total",
    "ordenha":    "Ordenha",
    "rebanho":    "Rebanho",
    "financeiro": "Financeiro",
    "armazem":    "Armazém",
}


def _find_fazenda(tel_limpo: str) -> Optional[str]:
    """Retorna fazenda_id pelo número, com cache de 30 min."""
    info = _find_user_info(tel_limpo)
    return info["fazenda_id"] if info else None


def _find_user_info(tel_limpo: str) -> Optional[dict]:
    """Retorna {fazenda_id, permissoes, nome} do número. Cache 30 min."""
    key = f"usr:{tel_limpo}"
    cached = _cache_get(key)
    if cached is not None:
        return cached if cached != "__none__" else None
    db = _db()
    for variante in _variantes_tel(tel_limpo):
        doc = db.collection('registros_tel').document(variante).get()
        if doc.exists and doc.to_dict().get('ativo', True):
            d = doc.to_dict()
            info = {
                "fazenda_id":  d.get('fazenda_id', 'default'),
                "permissoes":  d.get('permissoes', ['admin']),  # sem campo = admin (retrocompat)
                "nome":        d.get('nome', ''),
            }
            log.info(f"[{tel_limpo}] variante '{variante}' perms={info['permissoes']}")
            _cache_set(key, info, 1800)
            return info
    _cache_set(key, "__none__", 300)
    return None


def _tem_permissao(permissoes: list, tipo_acao: str) -> bool:
    """Verifica se o usuário pode executar o tipo de ação."""
    if "admin" in permissoes:
        return True
    if tipo_acao in _TIPOS_CONSULTA:
        return True
    perm_necessaria = _PERM_POR_TIPO.get(tipo_acao)
    if perm_necessaria is None:
        return True  # tipo desconhecido: não bloqueia
    return perm_necessaria in permissoes


def _msg_sem_permissao(tipo_acao: str) -> str:
    perm = _PERM_POR_TIPO.get(tipo_acao, tipo_acao)
    label = PERMISSOES_LABELS.get(perm, perm)
    return (
        f"Você não tem permissão para registrar *{label}*. "
        f"Fale com o gestor da fazenda para liberar seu acesso."
    )


def _coll(fazenda_id: str, nome: str):
    """Returns the correct Firestore collection scoped to the farm."""
    db = _db()
    if fazenda_id == 'default':
        return db.collection(nome)
    return db.collection('fazendas').document(fazenda_id).collection(nome)


# ─────────────────────────────────────────────
# ESTADO DA CONVERSA (por número de telefone)
# Cache em memória elimina roundtrips Firebase por mensagem.
# ─────────────────────────────────────────────
_CONV_MEM: dict = {}   # tel → conv dict
_CONV_LOCK = threading.Lock()
_CONV_TTL  = 7200      # 2h — igual ao TTL de abandono de conversa

def _get_conv(tel: str) -> dict:
    """Lê do cache em memória; cai no Firebase só na primeira vez."""
    with _CONV_LOCK:
        entry = _CONV_MEM.get(tel)
        if entry:
            return dict(entry)          # cópia para não vazar referência

    # Cache miss — lê Firebase uma única vez
    try:
        doc = _db().collection("conversas_bot").document(tel).get()
        conv = doc.to_dict() if doc.exists else {}
    except Exception:
        conv = {}

    if not conv:
        conv = {"historico": [], "estado": "idle", "dados": {}, "tipo": None}

    with _CONV_LOCK:
        _CONV_MEM[tel] = conv
    return dict(conv)


def _save_conv(tel: str, conv: dict):
    """Grava em memória imediatamente; persiste no Firebase em background."""
    conv["ts"] = datetime.datetime.now().isoformat()
    with _CONV_LOCK:
        _CONV_MEM[tel] = dict(conv)

    def _write():
        try:
            _db().collection("conversas_bot").document(tel).set(conv)
        except Exception as e:
            log.warning(f"conv save error: {e}")
    threading.Thread(target=_write, daemon=True).start()


def _clear_conv(tel: str, ultimo_salvo: dict = None):
    """Limpa a conversa preservando o último registro salvo para contexto pós-salvar."""
    vazio = {"historico": [], "estado": "idle", "dados": {}, "tipo": None,
             "ts": datetime.datetime.now().isoformat()}
    if ultimo_salvo:
        vazio["ultimo_salvo"] = ultimo_salvo   # persiste para próxima mensagem
    with _CONV_LOCK:
        _CONV_MEM[tel] = vazio

    def _write():
        try:
            _db().collection("conversas_bot").document(tel).set(vazio)
        except Exception as e:
            log.warning(f"conv clear error: {e}")
    threading.Thread(target=_write, daemon=True).start()


# ─────────────────────────────────────────────
# CACHE EM MEMÓRIA + RATE LIMIT
# Reduz leituras Firebase e tokens de IA em ~70%
# ─────────────────────────────────────────────
_CACHE: dict = {}
_RATE:  dict = {}
_LOCK  = threading.Lock()

# ── Fila de mensagens por número (anti-flood offline) ────────
# Quando o produtor fica sem internet e manda várias mensagens,
# ao reconectar chegam todas de uma vez. Guardamos em fila e
# processamos juntas após uma janela de 4s sem nova mensagem.
_FILA:  dict = {}   # tel → [{"texto": ..., "ts": ...}]
_FILA_LOCK = threading.Lock()
_FILA_JANELA = 0.5  # segundos de espera por mais mensagens (anti-flood offline)
_JID_CACHE: dict = {}   # tel_limpo → remoteJid original (para LIDs do novo WhatsApp)

import asyncio as _asyncio_fila


async def _encaminhar_apos_janela(tel: str, fazenda_id: str, enviar_fn, permissoes=None):
    """Aguarda FILA_JANELA segundos e processa todas as mensagens acumuladas."""
    await _asyncio_fila.sleep(_FILA_JANELA)
    with _FILA_LOCK:
        msgs = _FILA.pop(tel, [])
    if not msgs:
        return

    if len(msgs) == 1:
        texto_final = msgs[0]["texto"]
    else:
        # Agrupa as mensagens em uma só, separadas por " | "
        partes = [m["texto"] for m in msgs]
        texto_final = " | ".join(partes)
        log.info(f"[{tel}] {len(msgs)} mensagens agrupadas: '{texto_final[:80]}'")

    resposta = _processar(tel, texto_final, fazenda_id, permissoes)
    enviar_fn(tel, resposta)


async def _enfileirar(tel: str, texto: str, fazenda_id: str, enviar_fn, permissoes=None) -> bool:
    """Adiciona mensagem na fila. Retorna True se deve aguardar (há fila ativa).
    Retorna False se pode processar imediatamente (primeira mensagem, sem fila).
    """
    with _FILA_LOCK:
        agora = datetime.datetime.now()
        if tel not in _FILA:
            # Primeira mensagem — processa imediatamente, sem fila
            return False
        # Já existe fila — adiciona e reinicia o timer
        _FILA[tel].append({"texto": texto, "ts": agora})

    # Cancela o task anterior e cria novo com janela reiniciada
    # (o asyncio.create_task vai sobrescrever o timer)
    _asyncio_fila.create_task(_encaminhar_apos_janela(tel, fazenda_id, enviar_fn, permissoes))
    return True


def _iniciar_fila(tel: str, texto: str):
    """Registra o início de uma fila para este número."""
    with _FILA_LOCK:
        _FILA[tel] = [{"texto": texto, "ts": datetime.datetime.now()}]


def _cache_get(key: str):
    with _LOCK:
        e = _CACHE.get(key)
        if e and e[1] > datetime.datetime.now():
            return e[0]
    return None


def _cache_set(key: str, value, ttl: int = 300):
    with _LOCK:
        _CACHE[key] = (value, datetime.datetime.now() + datetime.timedelta(seconds=ttl))


def _cache_del(prefix: str):
    """Invalida todas as entradas cujo key começa com prefix."""
    with _LOCK:
        for k in [k for k in list(_CACHE) if k.startswith(prefix)]:
            del _CACHE[k]


def _rate_ok(tel: str, max_por_min: int = 10) -> bool:
    """True se o número ainda não atingiu o limite de mensagens por minuto.
    Usa apenas memória local — evita roundtrip Firebase por mensagem."""
    agora  = datetime.datetime.now()
    janela = agora - datetime.timedelta(minutes=1)
    with _LOCK:
        hist = [t for t in _RATE.get(tel, []) if t > janela]
        if len(hist) >= max_por_min:
            _RATE[tel] = hist
            return False
        hist.append(agora)
        _RATE[tel] = hist
    return True


# ── Leitores com cache ───────────────────────
def _cached_animais(fazenda_id: str) -> list:
    key = f"anm:{fazenda_id}"
    r = _cache_get(key)
    if r is not None:
        return r
    try:
        docs = [d.to_dict() for d in _coll(fazenda_id, "animais").stream()]
    except Exception:
        docs = []
    _cache_set(key, docs, 600)   # 10 min
    return docs


def _resolver_animal(fazenda_id: str, nome_ia: str):
    """Resolve o nome retornado pela IA para o nome exato cadastrado no Firebase.
    A IA já fez a correspondência semântica e deve retornar o nome exato da lista.
    Este fallback só corrige diferença de capitalização.
    Retorna (nome_resolvido, id_resolvido).
    """
    if not nome_ia:
        return nome_ia, nome_ia
    todos = _cached_animais(fazenda_id)
    lower = nome_ia.lower().strip()
    for a in todos:
        if a.get("nome", "").lower() == lower:
            return a["nome"], a.get("id", a["nome"])
    # Sem match → devolve o que a IA enviou (IA já deveria ter pedido confirmação)
    return nome_ia, nome_ia


def _cached_estoque(fazenda_id: str) -> list:
    key = f"est:{fazenda_id}"
    r = _cache_get(key)
    if r is not None:
        return r
    try:
        docs = [d.to_dict() for d in _coll(fazenda_id, "estoque").stream()]
    except Exception:
        docs = []
    _cache_set(key, docs, 600)
    return docs


def _cached_producao(fazenda_id: str, ini: str, fim: str = None) -> list:
    key = f"prod:{fazenda_id}:{ini}:{fim or 'open'}"
    r = _cache_get(key)
    if r is not None:
        return r
    try:
        q = _coll(fazenda_id, "producao").where(filter=FieldFilter("data", ">=", ini))
        if fim:
            q = q.where(filter=FieldFilter("data", "<=", fim))
        docs = [d.to_dict() for d in q.stream()]
    except Exception:
        docs = []
    _cache_set(key, docs, 300)   # 5 min (produção muda com frequência)
    return docs


def _cached_financeiro(fazenda_id: str, ini: str, fim: str = None) -> list:
    key = f"fin:{fazenda_id}:{ini}:{fim or 'open'}"
    r = _cache_get(key)
    if r is not None:
        return r
    try:
        q = _coll(fazenda_id, "financeiro").where(filter=FieldFilter("data", ">=", ini))
        if fim:
            q = q.where(filter=FieldFilter("data", "<=", fim))
        docs = [d.to_dict() for d in q.stream()]
    except Exception:
        docs = []
    _cache_set(key, docs, 600)
    return docs


# ─────────────────────────────────────────────
# CONTEXTO DO REBANHO
# ─────────────────────────────────────────────
def _ctx_animais(fazenda_id: str) -> str:
    docs = _cached_animais(fazenda_id)
    lst  = [f"{a.get('nome','?')} (#{a.get('id','?')}, {a.get('status','')})"
            for a in docs if a.get('status') != 'Vendido']
    return ", ".join(lst[:25]) or "nenhum cadastrado"


def _ctx_estoque(fazenda_id: str) -> str:
    docs = _cached_estoque(fazenda_id)
    lst  = [f"{e.get('item','?')} ({e.get('qtd',0):.1f} {e.get('un','')})"
            for e in docs]
    return "\n".join(lst) or "estoque vazio"


def _classificar_pergunta(texto: str) -> set:
    """Detecta quais seções de contexto são necessárias para responder a mensagem.
    Retorna subconjunto de: rebanho, producao, financeiro, reproducao, estoque, agenda, rentabilidade.
    Retorna None se a mensagem não parece ser uma pergunta (é um registro).
    """
    lower = texto.lower()
    secoes: set = set()

    if any(p in lower for p in ['produc', 'ordenh', 'litro', 'leite', 'produziu', 'média', 'media', 'semana']):
        secoes.add('producao')
        secoes.add('rebanho')  # IA precisa ver lista de animais para pedir por animal
    if any(p in lower for p in ['financ', 'saldo', 'gasto', 'receita', 'despesa', 'pagou', 'paguei',
                                  'custo do mes', 'lucro do mes', 'quanto recebi', 'quanto gastei',
                                  'quanto paguei', 'ração custou', 'conta de', 'boleto']):
        secoes.add('financeiro')
    if any(p in lower for p in ['fazer hoje', 'fazer semana', 'tarefa', 'pendente', 'agenda',
                                  'essa semana', 'esta semana', 'o que tem', 'previsao', 'previsão',
                                  'o que fazer', 'o que ta pra']):
        secoes.add('agenda')
    if any(p in lower for p in ['custo', 'lucro', 'prejuizo', 'prejuízo', 'rentavel', 'rentável',
                                  'margem', 'lucrativa', 'vale a pena', 'compensa', 'custo por litro',
                                  'ganho por', 'to ganhando', 'estou ganhando', 'to perdendo']):
        secoes.add('rentabilidade')
        secoes.add('producao')
    if any(p in lower for p in ['rebanho', 'animais', 'quantos animais', 'quantas vacas', 'prenha',
                                  'prenhez', 'status', 'bezerro', 'novilha', 'vaca', 'touro', 'secar',
                                  'seca ', 'secas', 'lactacao', 'lactação']):
        secoes.add('rebanho')
    if any(p in lower for p in ['estoque', 'armazem', 'armazém', 'quanto tem de', 'tenho de',
                                  'quanto tem ', 'tenho ainda', 'sobrou', 'acabou']):
        secoes.add('estoque')
    if any(p in lower for p in ['insemina', 'cobertura', 'reproducao', 'reprodução', 'pariou',
                                  'pariu', 'parto', 'prenhez', 'quando inseminei', 'quando pariu',
                                  'secar', 'secagem', 'abortou', 'perdeu a cria']):
        secoes.add('reproducao')
        secoes.add('rebanho')
    # Pergunta ampla ou genérica → carrega tudo relevante
    if not secoes:
        if any(p in lower for p in ['?', 'qual', 'quanto', 'quando', 'como ta', 'como está',
                                     'situacao', 'situação', 'resumo', 'me fala', 'me diz']):
            secoes = {'rebanho', 'producao', 'financeiro', 'estoque'}
    return secoes


def _ctx_dados_fazenda(fazenda_id: str, secoes: set = None) -> str:
    """Monta contexto seletivo da fazenda. secoes=None → todas as seções.
    Usa cache em memória para evitar leituras Firebase repetidas.
    """
    TODAS = {'rebanho', 'producao', 'financeiro', 'reproducao', 'estoque', 'agenda', 'rentabilidade'}
    if secoes is None:
        secoes = TODAS

    hoje         = datetime.date.today()
    ini_mes      = hoje.replace(day=1).isoformat()
    hoje_iso     = hoje.isoformat()
    ini_7d       = (hoje - datetime.timedelta(days=7)).isoformat()
    primeiro_mes = hoje.replace(day=1)
    fim_mes_ant  = (primeiro_mes - datetime.timedelta(days=1)).isoformat()
    ini_mes_ant  = (primeiro_mes - datetime.timedelta(days=primeiro_mes.day)).replace(day=1).isoformat()

    ctx = []

    # ── Carrega dados base uma única vez (cache) ──
    animais_raw  = _cached_animais(fazenda_id)  if secoes & {'rebanho', 'agenda', 'reproducao', 'rentabilidade'} else []
    prod_mes_raw = _cached_producao(fazenda_id, ini_mes)               if secoes & {'producao', 'agenda', 'rentabilidade'} else []
    prod_ant_raw = _cached_producao(fazenda_id, ini_mes_ant, fim_mes_ant) if 'producao' in secoes else []
    fin_mes_raw  = _cached_financeiro(fazenda_id, ini_mes)             if secoes & {'financeiro', 'rentabilidade'} else []
    fin_ant_raw  = _cached_financeiro(fazenda_id, ini_mes_ant, fim_mes_ant) if 'financeiro' in secoes else []
    est_raw      = _cached_estoque(fazenda_id)  if secoes & {'estoque', 'rentabilidade'} else []

    def _parse_dt(s):
        try:
            return datetime.datetime.strptime(str(s)[:10], "%Y-%m-%d").date() if s else None
        except Exception:
            return None

    def _agregar(docs):
        total = 0.0
        por_ani: dict = {}
        for d in docs:
            total += d.get('leite', 0)
            n = d.get('nome_animal', '?')
            por_ani[n] = por_ani.get(n, 0) + d.get('leite', 0)
        return total, por_ani

    # ── REBANHO ───────────────────────────────
    if 'rebanho' in secoes and animais_raw:
        try:
            por_status: dict = {}
            for a in animais_raw:
                s = a.get('status', '?')
                por_status.setdefault(s, []).append(a.get('nome', '?'))
            total_animais = len(animais_raw)
            ctx.append(f"REBANHO ({total_animais} animais):")
            for s, nomes in por_status.items():
                ctx.append(f"  {s} ({len(nomes)}): {', '.join(nomes[:20])}")
            prenhes = [a.get('nome') for a in animais_raw if a.get('prenhez')]
            if prenhes:
                ctx.append(f"  Prenhes confirmadas ({len(prenhes)}): {', '.join(prenhes)}")
            # Datas relevantes por animal (inseminação, parto)
            inseminadas = [(a.get('nome'), a.get('dt_insem')) for a in animais_raw if a.get('dt_insem') and not a.get('prenhez')]
            if inseminadas:
                ctx.append("  Inseminadas aguardando diagnóstico: " +
                            ", ".join(f"{n} ({d})" for n, d in inseminadas[:5]))
            partos = [(a.get('nome'), a.get('dt_parto')) for a in animais_raw
                      if a.get('dt_parto') and str(a.get('dt_parto')) >= hoje_iso]
            if partos:
                ctx.append("  Partos previstos: " +
                            ", ".join(f"{n} em {d}" for n, d in partos[:5]))
        except Exception:
            pass

    # ── PRODUÇÃO ──────────────────────────────
    total_mes = 0.0
    por_ani_mes: dict = {}
    if secoes & {'producao', 'rentabilidade'}:
        try:
            total_mes, por_ani_mes = _agregar(prod_mes_raw)
            total_mes_ant, _       = _agregar(prod_ant_raw)
            total_7d, _  = _agregar([d for d in prod_mes_raw if d.get('data', '') >= ini_7d])
            total_hoje, _ = _agregar([d for d in prod_mes_raw if d.get('data', '') == hoje_iso])
            dias_mes  = hoje.day
            media_dia = total_mes / dias_mes if dias_mes else 0
            var_pct   = ((total_mes - total_mes_ant) / total_mes_ant * 100) if total_mes_ant else None
            top = sorted(por_ani_mes.items(), key=lambda x: x[1], reverse=True)[:8]
            if 'producao' in secoes:
                ctx.append(f"\nPRODUCAO:")
                ctx.append(f"  Hoje ({hoje_iso}): {total_hoje:.0f} L")
                ctx.append(f"  Ultimos 7 dias: {total_7d:.0f} L")
                ctx.append(f"  Mes atual ({hoje.strftime('%B/%Y')}): {total_mes:.0f} L "
                           f"(media {media_dia:.0f} L/dia"
                           + (f", {var_pct:+.0f}% vs mes anterior)" if var_pct is not None else ")"))
                ctx.append(f"  Mes anterior: {total_mes_ant:.0f} L")
                if top:
                    ctx.append("  Por vaca (mes): " + ", ".join(f"{n}={v:.0f}L" for n, v in top))
        except Exception:
            pass

    # ── FINANCEIRO ────────────────────────────
    if 'financeiro' in secoes:
        try:
            def _fin_resumo(docs):
                rec = sum(d.get('valor', 0) for d in docs if 'Venda' in d.get('cat', ''))
                des = sum(d.get('valor', 0) for d in docs if 'Venda' not in d.get('cat', ''))
                return rec, des
            rec_mes, des_mes = _fin_resumo(fin_mes_raw)
            rec_ant, des_ant = _fin_resumo(fin_ant_raw)
            ctx.append(f"\nFINANCEIRO MES ATUAL: "
                       f"Receitas R${rec_mes:.0f} / Despesas R${des_mes:.0f} / "
                       f"Saldo R${rec_mes - des_mes:.0f}")
            ctx.append(f"  Mes anterior: Receitas R${rec_ant:.0f} / Despesas R${des_ant:.0f} / "
                       f"Saldo R${rec_ant - des_ant:.0f}")
            # Totais por categoria (para perguntas como "quanto gastei com ração?")
            por_cat: dict = {}
            for d in fin_mes_raw:
                c = d.get('cat', 'Outros')
                por_cat[c] = por_cat.get(c, 0) + d.get('valor', 0)
            if por_cat:
                ctx.append("  Por categoria: " + " | ".join(
                    f"{c} R${v:.0f}" for c, v in sorted(por_cat.items(), key=lambda x: -x[1])
                ))
            ultimos = sorted(fin_mes_raw, key=lambda d: d.get('data', ''), reverse=True)[:8]
            if ultimos:
                ctx.append("  Ultimos lancamentos:")
                for d in ultimos:
                    ctx.append(f"    [{d.get('data','')}] {d.get('cat','')} — "
                                f"{d.get('desc','')} R${d.get('valor', 0):.0f}")
        except Exception:
            pass

    # ── REPRODUÇÃO ────────────────────────────
    if 'reproducao' in secoes and animais_raw:
        try:
            animais_rep = [a for a in animais_raw if a.get("status") in ("Lactação", "Seca")]
            if animais_rep:
                total_rep = len(animais_rep)
                prenhes_n = sum(1 for a in animais_rep if a.get("prenhez"))
                tx_pren   = prenhes_n / total_rep * 100 if total_rep else 0
                janela_ideal = []
                inseminar_agora = []
                for a in animais_rep:
                    if a.get("prenhez") or a.get("dt_insem"):
                        continue
                    dp = _parse_dt(a.get("dt_parto"))
                    if not dp:
                        continue
                    dias_pp = (hoje - dp).days
                    if 45 <= dias_pp <= 90:
                        janela_ideal.append(f"{a.get('nome','?')} ({dias_pp}d pós-parto)")
                    elif dias_pp > 90:
                        inseminar_agora.append(f"{a.get('nome','?')} ({dias_pp}d sem inseminar)")
                ctx.append(f"\nREPRODUCAO:")
                ctx.append(f"  Taxa de prenhez: {tx_pren:.0f}% ({prenhes_n}/{total_rep})")
                if janela_ideal:
                    ctx.append(f"  Janela ideal p/ inseminacao (45-90d pos-parto): {', '.join(janela_ideal[:5])}")
                if inseminar_agora:
                    ctx.append(f"  Inseminacao atrasada (>90d): {', '.join(inseminar_agora[:5])}")
        except Exception:
            pass
        try:
            rep_docs = list(_coll(fazenda_id, "sanitario")
                            .where(filter=FieldFilter("tipo", "==", "Reprodução")).stream())
            rep_docs = sorted(rep_docs, key=lambda d: d.to_dict().get('data', ''), reverse=True)[:6]
            if rep_docs:
                ctx.append("\nREPRODUCAO RECENTE:")
                for d in rep_docs:
                    dd = d.to_dict()
                    ctx.append(f"  [{dd.get('data','')}] {dd.get('animal','?')} — {dd.get('prod','?')}")
        except Exception:
            pass

    # ── ESTOQUE ───────────────────────────────
    if 'estoque' in secoes and est_raw:
        try:
            ctx.append(f"\nESTOQUE ({len(est_raw)} itens):")
            for e in est_raw:
                ctx.append(f"  {e.get('item','?')}: {e.get('qtd',0):.1f} {e.get('un','')} "
                            f"(custo medio R${e.get('custo_medio',0):.2f})")
        except Exception:
            pass

    # ── AGENDA ────────────────────────────────
    if 'agenda' in secoes and animais_raw:
        try:
            GESTACAO     = 283
            DIAS_SECAR   = 60
            DIAS_DIAGN   = 30
            DIAS_PVE     = 45
            DIAS_DESMAME = 90
            SEMANA_ISO   = (hoje + datetime.timedelta(days=7)).isoformat()
            tarefas_hoje   = []
            tarefas_semana = []
            ordenhados_hoje = {d.get('id_animal') for d in prod_mes_raw if d.get('data') == hoje_iso}

            for a in animais_raw:
                nome   = a.get('nome', '?')
                status = a.get('status', '')
                d_insem = _parse_dt(a.get('dt_insem'))
                d_parto = _parse_dt(a.get('dt_parto'))
                d_nasc  = _parse_dt(a.get('nasc'))

                if status == 'Lactação':
                    if a.get('id') not in ordenhados_hoje:
                        tarefas_hoje.append(f"Ordenhar {nome}")
                    if d_insem and not a.get('prenhez'):
                        dias_insem = (hoje - d_insem).days
                        if dias_insem >= DIAS_DIAGN:
                            tarefas_hoje.append(f"Confirmar prenhez: {nome} (inseminada ha {dias_insem}d)")
                        elif dias_insem >= DIAS_DIAGN - 7:
                            tarefas_semana.append(f"Confirmar prenhez em breve: {nome} (faltam {DIAS_DIAGN - dias_insem}d)")
                    if not a.get('prenhez') and not d_insem and d_parto:
                        dias_vazia = (hoje - d_parto).days
                        if dias_vazia > DIAS_PVE:
                            tarefas_hoje.append(f"Inseminar {nome} (vazia ha {dias_vazia}d)")
                    if a.get('prenhez') and d_insem:
                        prev_parto = d_insem + datetime.timedelta(days=GESTACAO)
                        d_secar    = prev_parto - datetime.timedelta(days=DIAS_SECAR)
                        dias_secar = (d_secar - hoje).days
                        if dias_secar <= 0:
                            tarefas_hoje.append(f"Secar {nome} URGENTE (parto previsto {prev_parto.isoformat()})")
                        elif dias_secar <= 7:
                            tarefas_semana.append(f"Secar {nome} em {dias_secar}d (parto ~{prev_parto.isoformat()})")
                        dias_parto = (prev_parto - hoje).days
                        if 0 <= dias_parto <= 7:
                            tarefas_semana.append(f"Parto previsto: {nome} em ~{dias_parto}d ({prev_parto.isoformat()})")
                        elif dias_parto < 0:
                            tarefas_hoje.append(f"Parto em atraso: {nome} (previsto {prev_parto.isoformat()})")
                if status == 'Bezerro' and d_nasc:
                    idade_bez = (hoje - d_nasc).days
                    if idade_bez <= 2 and not a.get('colostro'):
                        tarefas_hoje.append(f"Dar colostro: {nome} (nasceu ha {idade_bez}d)")
                    if idade_bez >= DIAS_DESMAME:
                        tarefas_semana.append(f"Desmamar: {nome} ({idade_bez}d de idade)")

            if tarefas_hoje or tarefas_semana:
                ctx.append("\nAGENDA:")
                if tarefas_hoje:
                    ctx.append(f"  HOJE ({hoje_iso}):")
                    for t in tarefas_hoje:
                        ctx.append(f"    - {t}")
                if tarefas_semana:
                    ctx.append(f"  ESTA SEMANA (ate {SEMANA_ISO}):")
                    for t in tarefas_semana:
                        ctx.append(f"    - {t}")
            else:
                ctx.append("\nAGENDA: Nenhuma tarefa pendente identificada.")
        except Exception:
            pass

    # ── RENTABILIDADE ─────────────────────────
    if 'rentabilidade' in secoes and por_ani_mes and total_mes > 0:
        try:
            custo_racao_kg = 2.0
            for e in est_raw:
                nome_e = e.get('item', '').lower()
                if any(k in nome_e for k in ['racao', 'ração', 'concentrado', 'silagem']):
                    c = e.get('custo_medio', 0)
                    if c and float(c) > 0:
                        custo_racao_kg = float(c)
                        break
            preco_litro = 2.50
            vendas_leite = [d for d in fin_mes_raw if d.get('cat') == 'Venda de Leite']
            total_val_vendas = sum(d.get('valor', 0) for d in vendas_leite)
            if total_val_vendas > 0 and total_mes > 0:
                preco_litro = total_val_vendas / total_mes
            custos_fixos_mes = sum(
                d.get('valor', 0) for d in fin_mes_raw
                if d.get('cat') not in ('Venda de Leite', 'Venda de Animal') and not d.get('animal')
            )
            racao_ani: dict = {}
            for d in prod_mes_raw:
                n = d.get('nome_animal', '?')
                racao_ani[n] = racao_ani.get(n, 0) + d.get('racao', 0)
            vet_ani: dict = {}
            for d in fin_mes_raw:
                ani = d.get('animal')
                if ani and d.get('cat') not in ('Venda de Leite', 'Venda de Animal'):
                    vet_ani[ani] = vet_ani.get(ani, 0) + d.get('valor', 0)
            ctx.append(f"\nRENTABILIDADE POR ANIMAL (mes atual, preco R${preco_litro:.2f}/L):")
            animais_rent = []
            for nome_a, litros_a in por_ani_mes.items():
                c_racao = racao_ani.get(nome_a, 0) * custo_racao_kg
                c_vet   = vet_ani.get(nome_a, 0)
                c_fixo  = (litros_a / total_mes) * custos_fixos_mes
                c_total = c_racao + c_vet + c_fixo
                receita = litros_a * preco_litro
                lucro   = receita - c_total
                c_litro = c_total / litros_a if litros_a > 0 else 0
                l_litro = preco_litro - c_litro
                animais_rent.append((nome_a, litros_a, c_litro, l_litro, lucro))
            animais_rent.sort(key=lambda x: x[4])
            for nome_a, litros_a, c_l, l_l, lucro in animais_rent:
                status_rent = "PREJUIZO" if lucro < 0 else ("ATENCAO" if l_l < preco_litro * 0.1 else "OK")
                ctx.append(
                    f"  {nome_a}: {litros_a:.0f}L | custo R${c_l:.2f}/L | "
                    f"lucro R${l_l:.2f}/L | total R${lucro:.0f} [{status_rent}]"
                )
        except Exception:
            pass

    return "\n".join(ctx) if ctx else "sem dados disponíveis"


def _salvar_sugestao(fazenda_id: str, pergunta: str):
    """Salva sugestões de perguntas não respondidas para análise futura."""
    try:
        _db().collection("sugestoes_bot").add({
            "fazenda_id": fazenda_id,
            "pergunta": pergunta,
            "ts": datetime.datetime.now().isoformat(),
        })
    except Exception:
        pass


def _parse_float(v) -> float:
    """Converte valor monetário em float de forma robusta.
    Aceita: 300, "300", "R$300", "300,50", "R$ 1.200,00", "trezentos" (passa 0).
    """
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r'[^\d.,]', '', str(v))   # remove tudo exceto dígitos, vírgula, ponto
    if not s:
        return 0.0
    # "1.200,50" → "1200.50"  |  "300,50" → "300.50"  |  "300.50" → "300.50"
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return 0.0


def _buscar_no_estoque(fazenda_id: str, nome_produto: str) -> Optional[dict]:
    """Busca produto no estoque por similaridade de nome (case-insensitive, parcial)."""
    try:
        docs = list(_coll(fazenda_id, "estoque").stream())
        nome_lower = nome_produto.lower()
        # Busca exata primeiro
        for d in docs:
            if d.to_dict().get('item', '').lower() == nome_lower:
                return {"doc_id": d.id, **d.to_dict()}
        # Busca parcial
        for d in docs:
            item = d.to_dict().get('item', '').lower()
            if nome_lower in item or item in nome_lower:
                return {"doc_id": d.id, **d.to_dict()}
        return None
    except Exception:
        return None


# ─────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────
SYSTEM = """
Você é o assistente do MilkShow, sistema de gestão de fazenda leiteira.
Interprete mensagens de WhatsApp de produtores rurais — texto, áudio transcrito ou dados extraídos de foto de nota fiscal.
Responda em português brasileiro, curto e direto (máximo 4 linhas).

ANIMAIS NO REBANHO:
{animais}

ESTOQUE ATUAL:
{estoque}

DADOS DA FAZENDA (use para responder perguntas):
{dados_fazenda}

MEMÓRIA DA FAZENDA (preferências e termos customizados):
{memoria}

{ultimo_salvo}

LINGUAGEM DO PRODUTOR — aceite TODAS as variações abaixo:
- Erros de ortografia: "raçao","vacin","antibiotico","ivermctina","ocitosina","penicilna"
- Gírias/regionalismos: "remo"/"remédio"=medicamento, "bicho"/"animal"=animal, "garrote"=novilho macho,
  "bezerra/bezerro/bezero"=filhote, "vaca solteira/seca/secou"=seca, "mandei cobrir/cobrí"=cobertura,
  "tá prenha/emprenhada/confirmada"=prenhez confirmada, "perdeu a cria/abortou/aborto"=Aborto,
  "ordenhei"/"tirei leite"/"capinei"/"capinagem"=produção, "vendi pro laticínio/cooperativa"=VENDA_LEITE,
  "apliquei"/"dei"/"botei"/"usei"=GASTO_SANITARIO (aplicação), "tratei"/"curei"=GASTO_SANITARIO,
  "comprei no agro"/"comprei no agropecuário"=COMPRA_PRODUTO com fornecedor=agropecuário,
  "funcionário"/"peão"/"vaqueiro"/"diarista"/"ajudante"=Mão de Obra,
  "diesel"/"gasolina"/"combustivel"=Combustível,
  "consertei"/"reparei"/"manutenção"/"quebrou"=GASTO_GERAL categoria Manutenção,
  "paguei o veterinário"/"visita técnica"/"técnico veio"=GASTO_GERAL categoria Serviços,
  "botei pra secar"/"vou secar"=REPRODUCAO evento Secagem,
  "vaca pariu"/"novilha pariou"/"parto"=REPRODUCAO evento Parto,
  "devolução"/"estorno"=ajuste financeiro, "luz"/"energia"/"conta de energia"=Energia
- Valores: "300 reais", "R$300", "trezentos reais", "300,00", "3 conto" = R$300
- Quantidades: "5 saco", "cinco sacos", "5sc", "5 bags" = 5 unidades
- Datas: "hoje", "ontem", "segunda", "dia 10", "semana passada" = inferir data correta
- Unidades: "vidro/frasco/ampola"=dose/frasco, "saco/sc/bag"=sc, "litro/L/lt"=L

TIPOS DE REGISTRO:

1. COMPRA_PRODUTO — qualquer compra de produto para a fazenda
   Obrigatórios: produto, qtd, unidade, valor
   Opcional: fornecedor
   Aceita: "comprei","gastei com","paguei por","adquiri","trouxe"
   CATEGORIA FINANCEIRA — infira corretamente pelo produto:
   - "Ração / Nutrição": ração, milho, soja, silagem, sal mineral, farelo, concentrado, capim, feno
   - "Medicamento / Sanitário": vacina, vermífugo, antibiótico, hormônio, ocitocina, ivermectina, penicilina, brucelose, aftosa, raiva, calmosil, cortvet
   - "Infraestrutura": arame, madeira, cimento, tela, cano, bomba, cerca, material de construção
   - "Outros": qualquer produto que não se encaixe acima
   NUNCA coloque infraestrutura ou medicamentos em "Ração / Nutrição".

2. GASTO_SANITARIO — aplicação de qualquer medicamento, vacina, procedimento veterinário
   Obrigatórios: produto, tipo_sanitario, modo, custo
   CUSTO É OBRIGATÓRIO — se o produtor não informar, PERGUNTE: "Qual foi o custo desse procedimento?"
   Se individual: animal
   Opcional: qtd_usada
   tipo_sanitario (infira): Vacina | Antibiótico | Hormônio | Vermífugo | Casqueamento | Outros
   Mapeamento: ocitocina/oxitocina=Hormônio, ivermectina/ivomec=Vermífugo,
               penicilina/amoxicilina/enrofloxacina/cortvet=Antibiótico,
               aftosa/brucelose/raiva=Vacina, casqueamento/casco=Casqueamento
   Aceita: "apliquei","dei","usei","tratei","vacinou","curei","botei"

3. GASTO_GERAL — despesas operacionais (não envolve produto físico comprado)
   Obrigatórios: descricao, valor, categoria
   categoria: Mão de Obra | Energia | Combustível | Manutenção | Serviços | Outros
   CATEGORIA — infira corretamente:
   - Mão de Obra: peão, funcionário, vaqueiro, diarista, ajudante, salário, pagamento de pessoal
   - Combustível: diesel, gasolina, álcool, abastecimento
   - Energia: luz, energia elétrica, conta de energia, conta de água
   - Manutenção: consertei, reparei, quebrou, manutenção (sem compra de material explícita)
   - Serviços: veterinário, técnico, agrônomo, visita técnica, inseminador externo
   - Outros: qualquer despesa que não se encaixe acima
   DISTINÇÃO IMPORTANTE:
   - "consertei a cerca" → GASTO_GERAL Manutenção (serviço de reparo)
   - "comprei arame e madeira" → COMPRA_PRODUTO Infraestrutura (compra de material)
   - "apliquei ivermectina" → GASTO_SANITARIO (aplicação de medicamento)
   - "paguei veterinário para vacinar" → GASTO_GERAL Serviços (pagamento de serviço externo)

4. VENDA_LEITE — venda de leite ao laticínio/cooperativa
   Obrigatórios: litros, valor
   AMBOS SÃO OBRIGATÓRIOS — litros E valor. Se faltar um dos dois, PERGUNTE antes de confirmar.
   Opcional: laticinio
   Aceita: "vendi leite","recebi do laticínio","cooperativa pagou"
   ATENÇÃO: só use quando for venda de LEITE. Venda de animal é VENDA_ANIMAL.

4b. VENDA_ANIMAL — venda de vaca, novilha, bezerro ou touro
    Obrigatórios: animal (nome), valor
    Opcional: obs (ex: "foi junto com o bezerro")
    Aceita: "vendi a vaca","vendi a Pintada","vendeu o garrote"
    Ao confirmar: remove o animal do rebanho (status=Vendido) e lança receita no financeiro.

5. PRODUCAO_LEITE — ordenha individual de um único animal
   Obrigatórios: litros, animal
   Opcional: turno (1=manhã,2=tarde,3=noite), data
   Aceita: "tirei","ordenhei","produção de hoje","manhã deu","tarde foram"
   REGRA CRÍTICA — NUNCA registre produção como "Rebanho" se houver mais de 1 vaca em lactação.
   Se o produtor informar total sem especificar animal (ex: "ordenha de hoje 450 litros"):
   → Liste as vacas em lactação da lista ANIMAIS NO REBANHO e pergunte quanto cada uma produziu.
   → Exemplo: "Me informa os litros de cada vaca: Mimosa, Estrela, Rainha — quanto cada uma produziu?"
   → Use PRODUCAO_MULTIPLA quando informar todas de uma vez.
   → Só use animal="Rebanho" se houver UMA única vaca em lactação OU produtor disser explicitamente
     "não sei de cada uma" — nesse caso avise que a análise por animal ficará comprometida.

6. NOVO_ANIMAL — nascimento ou cadastro gratuito de animal
   Obrigatórios: nome, sexo, status_animal
   Opcional: nasc, lote, id_animal
   status_animal: Lactação | Seca | Novilha | Bezerro
   Aceita: "nasceu bezerro","cadastra","nova vaca" (SEM valor de compra)
   ATENÇÃO: se houver valor pago pelo animal, use COMPRA_ANIMAL, não NOVO_ANIMAL.

6b. COMPRA_ANIMAL — compra de animal (tem valor monetário envolvido)
    Obrigatórios: nome, valor, status_animal
    Opcional: sexo, nasc, lote
    Aceita: "comprei uma vaca por R$X","adquiri novilha","comprei garrote"

7. REPRODUCAO — eventos reprodutivos
   Obrigatórios: animal, evento, data
   DATA É OBRIGATÓRIA — sem data correta os cálculos de prenhez, secagem e parto ficam errados.
   Se não informar, pergunte: "Qual a data da [inseminação/parto/etc]? (ex: hoje, ontem, dia 15)"
   evento: Inseminação | Cobertura | Prenhez Confirmada | Prenhez Negativa | Parto | Secagem | Aborto
   Opcional: obs, custo
   Aceita: "inseminei","cobri","pariou","pariu","prenha","emprenhada","secar","perdeu a cria","abortou"
   CASO ESPECIAL — "vaca pariu" sem informar qual: pergunte "Qual vaca pariu? (verifique a lista do rebanho)"
   CASO ESPECIAL — "pariu"/"pariou" + mencionar o bezerro/bezerra: registre REPRODUCAO Parto para a vaca
     E pergunte: "Quer cadastrar o bezerro(a) também? Se sim, me diz o nome e o sexo."
   CASO ESPECIAL — "botei pra secar [animal]" sem data: use a data de hoje como data da secagem.

8. PERGUNTA — produtor quer saber algo sobre os dados da fazenda
   Exemplos gerais: "qual minha produção esta semana?", "quanto gastei este mês?", "quais vacas estão secas?",
             "qual vaca produz mais?", "qual meu saldo?", "quanto tenho de ivermectina?",
             "quando inseminei a Rainha?", "quantos animais tenho?"
   Exemplos de AGENDA (use seção AGENDA dos dados):
             "o que tenho pra fazer hoje?", "o que tem pra fazer essa semana?",
             "quais tarefas tenho hoje?", "tem alguma vaca pra inseminar?",
             "tem parto previsto?", "alguma vaca pra secar?", "o que ta pendente?"
   Exemplos de RENTABILIDADE (use seção RENTABILIDADE POR ANIMAL dos dados):
             "quanto custa produzir um litro?", "qual vaca dá mais prejuízo?",
             "estou tendo lucro?", "qual o custo por litro da Rainha?",
             "qual vaca mais cara pra manter?", "quais vacas estão no prejuízo?",
             "vale a pena manter a Moreninha?", "qual meu lucro por litro?",
             "qual a vaca mais rentável?", "quanto to ganhando por litro?"
   Use estado CONSULTA. Responda com os dados disponíveis no contexto DADOS DA FAZENDA abaixo.
   Para perguntas de rentabilidade: cite o custo/L, lucro/L e status (OK/ATENCAO/PREJUIZO) de cada animal.
   Se a pergunta for sobre algo que não está nos dados, use estado SEM_RESPOSTA.

9. PRODUCAO_MULTIPLA — foto ou lista com produção de múltiplos animais OU múltiplos dias
   ATENÇÃO: é APENAS litros produzidos. NUNCA peça, calcule ou mostre valor de venda, preço/litro,
   valor total ou valor comercializado. Esses campos não existem em PRODUCAO_MULTIPLA.
   Se os dados já foram extraídos da imagem, NÃO os peça de novo — use-os diretamente.
   "fazenda inteira", "rebanho todo", "produção geral" → animal = "Rebanho".

   REGRA CRÍTICA — IDENTIFICAÇÃO DE ANIMAL:
   Qualquer nome que aparecer (no título da tabela, no texto, na foto) deve ser verificado contra
   a lista ANIMAIS NO REBANHO abaixo. Se o nome NÃO estiver na lista → é nome de produtor ou fazenda
   → use animal = "Rebanho". Se estiver na lista → é o nome do animal, use-o.
   NUNCA invente que um nome é de vaca sem confirmar na lista de animais.

   FORMAS QUE O PRODUTOR PODE ENVIAR (todas devem funcionar):
   - Foto de tabela com datas e litros (mensal)
   - Foto de quadro/lousa manuscrito
   - Texto: "Rainha 18, Moreninha 12, Pintada 9"
   - Texto: "ordenha de hoje 450L" → sem animais → pergunte se quer dividir por vaca ou salvar como Rebanho
   - Áudio descrevendo a produção
   - Partes separadas em mensagens diferentes → agrupe e confirme tudo junto

   DOIS casos possíveis:

   CASO A — múltiplos animais no mesmo dia:
   Use "dados": {"data": "YYYY-MM-DD"},
       "itens": [{"animal":"Rainha","litros":18}, {"animal":"Moreninha","litros":12}, ...]
   Cada item: animal (verificado na lista), litros. Opcional: turno.

   CASO B — produção total por dia ao longo de vários dias (tabela mensal):
   Use "dados": {"animal": "Rebanho"} (ou nome da vaca se confirmado na lista),
       "itens": [{"data":"DD/MM/AAAA","litros":45}, {"data":"DD/MM/AAAA","litros":"//"},...]
   "//" ou "—" ou em branco = sem dado naquele dia → inclua com litros: "//" (o sistema ignora).
   Uma entrada por linha, cada uma com a data correta daquele dia.

REGRAS GERAIS:
- TOLERE erros de digitação — interprete pela intenção, não pela grafia exata.
- Extraia o máximo de campos. Pergunte SOMENTE o que estiver faltando, um por vez.
- Quando tiver todos os obrigatórios, mostre RESUMO COMPLETO e pergunte "Confirma? (sim/não)".
- Confirma: "sim","s","ok","pode","isso","correto","isso mesmo","bora","certo","isso aí" → SALVAR
- Cancela: "não","n","cancela","errado","para","volta","esquece" → CANCELAR
- CORREÇÃO MID-FLOW: se o produtor corrigir um valor durante a conversa ("é 300, não 200" / "na verdade foram 25 litros"), atualize o campo e mostre o resumo corrigido. Não reinicie.
- Qualquer pergunta sobre dados da fazenda ("quanto produzi?","qual meu saldo?","quais vacas secas?","quando inseminei X?","quanto gastei com ração?") → estado CONSULTA, responda usando DADOS DA FAZENDA acima.
- Se nao tiver os dados suficientes para responder → estado SEM_RESPOSTA, texto: "Desculpe, nao consigo responder a isso ainda. Vou anotar sua sugestao para a proxima versao."
- NUNCA invente valores monetários. Se faltar, pergunte.
- Se a mensagem começa com "[Nota fiscal]" → dados já extraídos, use COMPRA_INSUMO/GASTO_SANITARIO diretamente.
- Se começa com "[Foto tabela mensal de producao]" → PRODUCAO_MULTIPLA caso B: animal no topo, itens com data+litros de cada dia. Entradas "//" são dias sem ordenha — inclua com litros:"//". Confirme com o produtor antes de salvar.
- Se começa com "[Foto producao do dia]" → PRODUCAO_MULTIPLA caso A: vários animais, mesma data. Confirme antes de salvar.
- MÚLTIPLOS TIPOS em uma mensagem (sem " | "): ex "apliquei ivermectina e comprei ração" → identifique cada ação, registre as que tem dados completos e pergunte os faltantes. Exemplo de resposta: "Ivermectina aplicada (registrada). E a ração: quanto custou e qual quantidade?"

VALIDAÇÕES OBRIGATÓRIAS — pergunte ao produtor antes de aceitar:
1. ESTOQUE: se o tipo for GASTO_SANITARIO e o produto NÃO estiver na lista de ESTOQUE ATUAL,
   avise: "Não encontrei [produto] no estoque. Deseja registrar assim mesmo?"
   Se confirmar, salve normalmente. Se negar, pergunte o nome correto.
2. ANIMAL: o produtor pode mencionar animais por apelido ou variação do nome cadastrado.
   Você tem acesso à lista completa em ANIMAIS NO REBANHO — use-a para identificar.
   Regras (por ordem):
   - Corresponda APENAS pelo nome cadastrado, nunca por característica visual/física
   - Correspondência direta: "Mimosa", "a Mimosa", "mimosinha", "Mimosona" → nome "Mimosa" na lista ✓
   - Diminutivo/aumentativo/artigo do mesmo nome → aceite se há só 1 na lista com aquela raiz
   - Característica visual ("a pintada", "a amarela", "a malhada") sem equivalente na lista → PERGUNTE
   - Se encontrou UM único correspondente pelo nome → use o nome EXATO da lista, sem perguntar
   - Se encontrou MAIS DE UM possível → pergunte: "Qual vaca você quis dizer? [lista as opções]"
   - Se não encontrou nenhum → pergunte: "Não encontrei '[nome]' no rebanho. Qual é o nome cadastrado?"
   IMPORTANTE: No JSON, campo "animal" deve ser SEMPRE o nome exato como está em ANIMAIS NO REBANHO.
3. DADOS INCOERENTES: questione se encontrar:
   - Valor = 0 ou negativo em compra/venda
   - Litros > 1000 para um único animal por dia
   - Litros > 10000 para o rebanho todo por dia
   - Quantidade negativa
   - Data futura (mais de 1 dia no futuro)
   Pergunte: "Confirma [dado]? Parece incomum."
4. MENSAGEM INCOMPREENSÍVEL: se não entender o que o produtor quis dizer,
   responda estado COLETANDO: "Não entendi bem. Pode explicar de outra forma?"
   NUNCA tente adivinhar um tipo de registro quando não tiver certeza.
5. TIPO INCERTO: se a mensagem puder ser de dois tipos diferentes, pergunte:
   "Isso é [opção A] ou [opção B]?"

MÚLTIPLOS PRODUTOS/ANIMAIS NA MESMA MENSAGEM:
- Se mencionar 2+ produtos distintos → use "itens" (array), salva cada um separado.
- Se o valor total não estiver dividido por produto → pergunte os valores individuais.
- Exemplo: [{"produto":"Milho","qtd":60,"unidade":"kg","valor":180},{"produto":"Soja","qtd":40,"unidade":"kg","valor":120}]

CONTEXTO PÓS-SALVAR — após salvar um registro, o produtor pode mandar mensagem complementar:
- "usei no mês de abril", "foi usado em abril", "é referente a abril" → o produtor está dizendo que
  aqueles itens foram consumidos em abril. A compra JÁ FOI SALVA. NÃO registre de novo.
  Responda: "Entendido! Os registros foram feitos. Os gastos de ração de abril já estão lançados. Posso ajudar com mais alguma coisa?"
- "já tem os valores", "você já sabe", "é o mesmo valor" → o produtor está confirmando usar
  dados que o bot já tem. Use os dados do histórico — NÃO peça de novo.
- Se o produtor mencionar algo que já foi salvo e quiser CORRIGIR → peça o que está errado
  e atualize (GASTO_GERAL com data corrigida), sem duplicar.
- NUNCA peça ao produtor um valor que já apareceu no histórico da conversa.

MENSAGENS AGRUPADAS (produtor ficou sem internet):
- Se a mensagem contiver " | " separando partes, significa que o produtor mandou várias mensagens seguidas sem internet e elas foram agrupadas automaticamente.
- Trate cada parte separada por " | " como uma mensagem independente e processe todas.
- Exemplo: "comprei racao 300 reais | apliquei ivermectina no rebanho | ordenha foi 450 litros"
  → salva 3 registros separados: COMPRA_PRODUTO + GASTO_SANITARIO + PRODUCAO_LEITE
- Ao confirmar, informe quantos registros foram salvos: "3 registros salvos com sucesso."
- Se alguma parte for ambígua, salva o que deu e pergunta só o que ficou pendente.
- PRODUCAO_MULTIPLA com muitos itens (>5): NO campo "texto" do CONFIRMANDO, NÃO liste todos os itens.
  Use resumo compacto: "📋 Rebanho — 30 dias, total 1.452 L. Confirma? (sim/não)"
  MAS o campo "itens" do JSON DEVE sempre conter o array completo — nunca omita os itens do JSON.

RESPONDA SEMPRE EM JSON VÁLIDO sem markdown:
{"texto":"mensagem ao produtor","estado":"COLETANDO|CONFIRMANDO|SALVAR|CANCELAR|CONSULTA|SEM_RESPOSTA","tipo":"COMPRA_PRODUTO|COMPRA_ANIMAL|GASTO_SANITARIO|GASTO_GERAL|VENDA_LEITE|VENDA_ANIMAL|PRODUCAO_LEITE|PRODUCAO_MULTIPLA|NOVO_ANIMAL|REPRODUCAO|DESCONHECIDO","dados":{"produto":null,"qtd":null,"unidade":null,"valor":null,"fornecedor":null,"tipo_sanitario":null,"modo":null,"animal":null,"qtd_usada":null,"descricao":null,"categoria":null,"litros":null,"turno":null,"data":null,"laticinio":null,"nome":null,"sexo":null,"status_animal":null,"nasc":null,"lote":null,"id_animal":null,"evento":null,"obs":null,"custo":null},"itens":null}
"""


# ─────────────────────────────────────────────
# AGENTES POR DOMÍNIO — system prompts focados
# ─────────────────────────────────────────────

# Seção reutilizada em todos os agentes
_COMMON_TAIL = """
LINGUAGEM — aceite variações ortográficas, gírias e regionalismos:
- "remo"/"remédio"=medicamento, "bicho"/"animal"=animal, "garrote"=novilho, "bezerra/bezerro"=filhote
- "sim","s","ok","pode","isso","correto","bora","certo" → SALVAR; "não","n","cancela","errado","volta" → CANCELAR
- CORREÇÃO MID-FLOW: se o produtor corrigir um valor durante a coleta, atualize e mostre resumo corrigido.
- Valores: "300 reais","R$300","trezentos reais","3 conto"=R$300; Datas: "hoje","ontem","segunda","dia 10"=inferir.
- Unidades: "saco/sc/bag"=sc, "litro/L/lt"=L, "vidro/frasco/ampola"=dose/frasco.

CONTEXTO PÓS-SALVAR: {ultimo_salvo}
Se o produtor referenciar "esses itens","isso","os mesmos" refere-se ao último registro. NÃO registre de novo.

REGRAS GERAIS:
- Extraia o máximo de campos. Pergunte SOMENTE o que estiver faltando, um por vez.
- Quando tiver todos os obrigatórios, mostre RESUMO COMPLETO e pergunte "Confirma? (sim/não)".
- NUNCA invente valores monetários. Se faltar, pergunte.
- MENSAGEM INCOMPREENSÍVEL → estado COLETANDO: "Não entendi bem. Pode explicar de outra forma?"
- DADOS INCOERENTES (valor negativo, litros >1000/animal, data futura) → pergunte antes de aceitar.

RESPONDA SEMPRE EM JSON VÁLIDO sem markdown:
{"texto":"mensagem ao produtor","estado":"COLETANDO|CONFIRMANDO|SALVAR|CANCELAR|CONSULTA|SEM_RESPOSTA","tipo":"TIPO_AQUI","dados":{"produto":null,"qtd":null,"unidade":null,"valor":null,"fornecedor":null,"tipo_sanitario":null,"modo":null,"animal":null,"qtd_usada":null,"descricao":null,"categoria":null,"litros":null,"turno":null,"data":null,"laticinio":null,"nome":null,"sexo":null,"status_animal":null,"nasc":null,"lote":null,"id_animal":null,"evento":null,"obs":null,"custo":null,"chave":null,"valor_novo":null,"operacao":null,"protocolo":null,"litros_correto":null,"raca":null,"mae":null},"itens":null}
"""

SYSTEM_CLASSIFICADOR = """Você é um classificador de mensagens de WhatsApp de produtores rurais de fazendas leiteiras.
Leia a mensagem e retorne APENAS JSON com o domínio e o tipo mais provável.

DOMÍNIOS e TIPOS:
- producao: PRODUCAO_LEITE | PRODUCAO_MULTIPLA | VENDA_LEITE | CORRIGIR_PRODUCAO | APAGAR_PRODUCAO
- financeiro: COMPRA_PRODUTO | GASTO_GERAL | VENDA_ANIMAL | COMPRA_ANIMAL | CORRIGIR_LANCAMENTO | APAGAR_LANCAMENTO
- rebanho: NOVO_ANIMAL | COMPRA_ANIMAL | REPRODUCAO | ATUALIZAR_ANIMAL
- armazem: GASTO_SANITARIO | COMPRA_PRODUTO | AGENDAR_SANITARIO | EXECUTAR_PROTOCOLO | APAGAR_ITEM_ESTOQUE
- config: ALTERAR_CONFIG | AJUSTAR_ESTOQUE
- consulta: PERGUNTA

EXEMPLOS de roteamento:
"ordenha de hoje 450 litros" → producao / PRODUCAO_LEITE
"tirei 320 essa manhã" → producao / PRODUCAO_LEITE
"a Mimosa deu 22 litros" → producao / PRODUCAO_LEITE
"capinei 280 hoje" → producao / PRODUCAO_LEITE
"capinagem hoje foi boa, 420 litros" → producao / PRODUCAO_LEITE
"ordenhei de manhã, 18 litros da Estrela" → producao / PRODUCAO_LEITE
"Rainha 25, Mimosa 18, Estrela 21, Pintada 15" → producao / PRODUCAO_MULTIPLA
"Rainha: 22L, Mimosa: 18L" → producao / PRODUCAO_MULTIPLA
"[Foto producao do dia] Mimosa: 22L\nRainha: 25L" → producao / PRODUCAO_MULTIPLA
"[Foto tabela mensal de producao]" → producao / PRODUCAO_MULTIPLA
"errei a produção da Rainha, foram 22 não 18" → producao / CORRIGIR_PRODUCAO
"apaga a ordenha errada de ontem" → producao / APAGAR_PRODUCAO
"comprei 5 sc ração por R$300" → financeiro / COMPRA_PRODUTO
"trouxe silagem do armazém, R$800" → financeiro / COMPRA_PRODUTO
"paguei o peão R$1.500 do mês" → financeiro / GASTO_GERAL
"paguei 3 conto pro peão" → financeiro / GASTO_GERAL
"abasteci com diesel R$380" → financeiro / GASTO_GERAL
"conta de luz chegou R$620" → financeiro / GASTO_GERAL
"consertei a bomba, R$250" → financeiro / GASTO_GERAL
"paguei veterinário externo R$300" → financeiro / GASTO_GERAL
"corrija o gasto de diesel, foi R$200 não R$150" → financeiro / CORRIGIR_LANCAMENTO
"apaga o lançamento duplicado de ontem" → financeiro / APAGAR_LANCAMENTO
"inseminei a Rainha hoje" → rebanho / REPRODUCAO
"cobri a Mimosa hoje com o touro" → rebanho / REPRODUCAO
"muda a raça da Mimosa para Girolanda" → rebanho / ATUALIZAR_ANIMAL
"apliquei ivermectina no rebanho, R$80" → armazem / GASTO_SANITARIO
"botei ocitosina na Rainha, R$15" → armazem / GASTO_SANITARIO
"dei penicilina pra Estrela, R$35" → armazem / GASTO_SANITARIO
"vacin o rebanho contra aftosa R$200" → armazem / GASTO_SANITARIO
"ivermctina no gado R$80" → armazem / GASTO_SANITARIO
"ocitosina na Rainha R$12" → armazem / GASTO_SANITARIO
"casquiei o rebanho hoje, R$300" → armazem / GASTO_SANITARIO
"dei remo no rebanho, R$60" → armazem / GASTO_SANITARIO
"agenda vacinação do rebanho para sexta" → armazem / AGENDAR_SANITARIO
"realizei a vacinação agendada" → armazem / EXECUTAR_PROTOCOLO
"executei o protocolo de brucelose" → armazem / EXECUTAR_PROTOCOLO
"fiz a vacinação que tava agendada" → armazem / EXECUTAR_PROTOCOLO
"apaga a ivermectina do estoque, acabou" → armazem / APAGAR_ITEM_ESTOQUE
"muda o preço do leite para R$2,80" → config / ALTERAR_CONFIG
"muda a meta de produção para 500 litros" → config / ALTERAR_CONFIG
"altera o custo por litro pra R$1,20" → config / ALTERAR_CONFIG
"ajusta o estoque de ração para 10 sacos" → config / AJUSTAR_ESTOQUE
"adiciona 5 sacos de ração no estoque" → config / AJUSTAR_ESTOQUE
"qual minha produção essa semana?" → consulta / PERGUNTA

REGRAS CRÍTICAS:
- "Nome1 N, Nome2 N, ..." onde N é um número → PRODUCAO_MULTIPLA (litros por animal), NUNCA REPRODUCAO
- casquear/casqueamento → armazem / GASTO_SANITARIO (procedimento veterinário), NUNCA GASTO_GERAL
- "realizei/executei/fiz o protocolo/vacinação agendada" → armazem / EXECUTAR_PROTOCOLO
- "minha meta é X litros/custo por litro/preço do leite" → config / ALTERAR_CONFIG (NÃO produção!)
- "adicionar ao estoque/tem X sacos" → config / AJUSTAR_ESTOQUE (não COMPRA_PRODUTO)
- "botei X no/na/nas + animal/rebanho" onde X é medicamento → armazem / GASTO_SANITARIO, NÃO producao
- "apliquei/dei/usei/botei + medicamento" → armazem / GASTO_SANITARIO
- peão/vaqueiro/diarista/funcionário + valor → financeiro / GASTO_GERAL (Mão de Obra)
- pagar veterinário externo → financeiro / GASTO_GERAL Serviços (não GASTO_SANITARIO)
- GASTO_SANITARIO = aplicação de produto VETERINÁRIO no animal (ivermectina, vacina, antibiótico, casqueamento, ocitocina, hormônio)
- GASTO_GERAL = pagamento de serviço externo ou conta (luz, diesel, peão, veterinário externo, manutenção)
- "meta é X litros" = config, não producao — é uma CONFIGURAÇÃO, não registro de produção

LISTA DE ANIMAIS (para identificar nomes):
{animais}

Retorne SOMENTE: {"dominio":"...","tipo":"..."}
"""

SYSTEM_PRODUCAO = """Você é o agente de PRODUÇÃO do MilkShow, assistente de fazenda leiteira.
Registre ordenha individual, produções múltiplas e vendas de leite.

ANIMAIS EM LACTAÇÃO:
{animais}

MEMÓRIA DA FAZENDA:
{memoria}

{ultimo_salvo_bloco}

TIPOS QUE VOCÊ GERENCIA:

PRODUCAO_LEITE — ordenha individual de um único animal
  Obrigatórios: litros, animal. Opcional: turno (1=manhã,2=tarde,3=noite), data.
  REGRA CRÍTICA: NUNCA use animal="Rebanho" se houver mais de 1 vaca em lactação.
  Se o total não especificar animal → liste as vacas e pergunte quanto cada uma produziu.
  Aceita: "tirei","ordenhei","produção de hoje","manhã deu","tarde foram"

PRODUCAO_MULTIPLA — foto/lista com múltiplos animais OU vários dias
  É APENAS litros. NUNCA peça valor de venda, preço/litro ou valor total.
  Se os dados já foram extraídos de imagem, NÃO peça de novo — use diretamente.
  IDENTIFICAÇÃO: qualquer nome deve ser verificado na lista ANIMAIS. Se NÃO estiver → animal="Rebanho".
  CASO A (múltiplos animais, mesmo dia): "dados":{"data":"YYYY-MM-DD"}, "itens":[{"animal":"X","litros":18},...]
  CASO B (produção total por dia, vários dias): "dados":{"animal":"Rebanho"}, "itens":[{"data":"DD/MM","litros":45},...]
  "//" ou "—" ou em branco = sem dado → inclua com litros:"//"
  PRODUCAO_MULTIPLA com >5 itens: NO "texto" use resumo compacto ("30 dias, total 1.452 L"), MAS "itens" deve ter o array completo.

VENDA_LEITE — venda de leite ao laticínio/cooperativa
  Obrigatórios: litros E valor (AMBOS — se faltar um, PERGUNTE).
  Opcional: laticinio.
  ATENÇÃO: só use para venda de LEITE. Venda de animal é VENDA_ANIMAL (domínio financeiro).
  Aceita: "vendi leite","recebi do laticínio","cooperativa pagou"

CORRIGIR_PRODUCAO — corrigir produção já registrada
  Obrigatórios: animal, data, litros_correto.
  Opcional: turno.
  O sistema apaga o registro antigo e salva o valor correto.
  Mostre resumo: "Corrigir produção de [animal] em [data]: [X] L → [Y] L. Confirma?"
  Aceita: "errei a produção","corrija a ordenha","foi [X] não [Y]","registrei errado"

APAGAR_PRODUCAO — apagar registro de produção incorreto ou duplicado
  Obrigatórios: animal, data. Opcional: turno, litros (para identificar qual dos registros).
  SEMPRE peça confirmação antes de apagar. Mostre: "Apagar produção de [animal] em [data] ([X] L). Confirma?"
  Aceita: "apaga a ordenha","remove o registro de produção","exclui a produção de"
""" + _COMMON_TAIL

SYSTEM_FINANCEIRO = """Você é o agente FINANCEIRO do MilkShow, assistente de fazenda leiteira.
Registre compras de produtos, despesas operacionais, vendas e compras de animais.

ESTOQUE ATUAL (para inferir categoria):
{estoque}

MEMÓRIA DA FAZENDA:
{memoria}

{ultimo_salvo_bloco}

TIPOS QUE VOCÊ GERENCIA:

COMPRA_PRODUTO — qualquer compra de produto/insumo para a fazenda
  Obrigatórios: produto, qtd, unidade, valor. Opcional: fornecedor.
  Aceita: "comprei","gastei com","paguei por","adquiri","trouxe"
  CATEGORIA FINANCEIRA — infira pelo produto:
  - "Ração / Nutrição": ração, milho, soja, silagem, sal mineral, farelo, concentrado, capim, feno
  - "Medicamento / Sanitário": vacina, vermífugo, antibiótico, hormônio, ocitocina, ivermectina
  - "Infraestrutura": arame, madeira, cimento, tela, cano, bomba, cerca, material de construção
  - "Outros": qualquer produto que não se encaixe acima
  NUNCA coloque infraestrutura ou medicamentos em "Ração / Nutrição".
  MÚLTIPLOS PRODUTOS: use "itens" (array); se valor total não dividido, pergunte valores individuais.

GASTO_GERAL — despesas operacionais (sem produto físico comprado)
  Obrigatórios: descricao, valor, categoria.
  categoria: Mão de Obra | Energia | Combustível | Manutenção | Serviços | Outros
  - Mão de Obra: peão, funcionário, vaqueiro, diarista, salário
  - Combustível: diesel, gasolina, álcool, abastecimento
  - Energia: luz, energia elétrica, conta de energia, conta de água
  - Manutenção: consertei, reparei, quebrou (sem compra de material)
  - Serviços: veterinário externo, técnico, agrônomo, inseminador externo
  DISTINÇÃO: "comprei arame"→COMPRA_PRODUTO; "consertei a cerca"→GASTO_GERAL Manutenção.

VENDA_ANIMAL — venda de vaca, novilha, bezerro ou touro
  Obrigatórios: animal (nome), valor. Opcional: obs.
  Ao confirmar: remove animal do rebanho (status=Vendido) e lança receita no financeiro.

COMPRA_ANIMAL — compra de animal (tem valor monetário)
  Obrigatórios: nome, valor, status_animal. Opcional: sexo, nasc, lote.
  Aceita: "comprei uma vaca por R$X","adquiri novilha","comprei garrote"
  status_animal: Lactação | Seca | Novilha | Bezerro

CORRIGIR_LANCAMENTO — corrigir valor ou descrição de lançamento financeiro já registrado
  Obrigatórios: descricao (fragmento do que foi registrado), data, valor_novo.
  Opcional: valor (valor antigo para confirmar qual lançamento).
  O sistema localiza o lançamento pela descrição+data e atualiza o valor.
  Mostre resumo: "Corrigir lançamento '[desc]' de [data]: R$[X] → R$[Y]. Confirma?"
  Aceita: "corrija o gasto","foi R$X não R$Y","o valor estava errado","muda o lançamento"

APAGAR_LANCAMENTO — apagar lançamento financeiro incorreto ou duplicado
  Obrigatórios: descricao (fragmento), data. Opcional: valor (para identificar exato).
  SEMPRE mostre o que será apagado e peça confirmação: "Apagar '[desc]' de [data] — R$[X]. Confirma?"
  Aceita: "apaga o lançamento","remove o gasto","exclui a despesa","lançamento duplicado"
""" + _COMMON_TAIL

SYSTEM_REBANHO = """Você é o agente do REBANHO do MilkShow, assistente de fazenda leiteira.
Gerencie cadastro de animais e eventos reprodutivos.

ANIMAIS NO REBANHO:
{animais}

MEMÓRIA DA FAZENDA:
{memoria}

{ultimo_salvo_bloco}

TIPOS QUE VOCÊ GERENCIA:

NOVO_ANIMAL — nascimento ou cadastro gratuito
  Obrigatórios: nome, sexo, status_animal. Opcional: nasc, lote, id_animal.
  status_animal: Lactação | Seca | Novilha | Bezerro
  ATENÇÃO: se houver valor pago → use COMPRA_ANIMAL (domínio financeiro), não NOVO_ANIMAL.

COMPRA_ANIMAL — compra de animal (tem valor monetário)
  Obrigatórios: nome, valor, status_animal. Opcional: sexo, nasc, lote.

REPRODUCAO — eventos reprodutivos
  Obrigatórios: animal, evento, data.
  DATA É OBRIGATÓRIA — sem data, os cálculos de prenhez/secagem/parto ficam errados.
  Se não informar data → pergunte: "Qual a data da [inseminação/parto/etc]? (ex: hoje, ontem, dia 15)"
  evento: Inseminação | Cobertura | Prenhez Confirmada | Prenhez Negativa | Parto | Secagem | Aborto
  Opcional: obs, custo.
  Aceita: "inseminei","cobri","pariou","pariu","prenha","emprenhada","secar","perdeu a cria","abortou"
  CASO "botei pra secar [animal]" sem data → use data de hoje.
  CASO "vaca pariu" sem especificar qual → pergunte "Qual vaca pariu?"
  CASO "pariou" + mencionou bezerro → registre REPRODUCAO Parto E pergunte se quer cadastrar o bezerro.

ATUALIZAR_ANIMAL — atualizar dados cadastrais de um animal
  Obrigatórios: animal (nome exato), e ao menos UM campo para atualizar.
  Campos atualizáveis: raca, obs, lote, nasc (data nascimento), mae (nome da mãe).
  Mostre o que vai mudar: "Atualizar [animal]: [campo] → [novo valor]. Confirma?"
  NÃO use para mudança de status reprodutivo (use REPRODUCAO) nem para venda (use VENDA_ANIMAL).
  Aceita: "muda a raça","atualiza o lote","coloca na observação","corrige o nascimento","a mãe dela é"

IDENTIFICAÇÃO DE ANIMAL (sempre verificar na lista ANIMAIS NO REBANHO):
  - Correspondência direta/diminutivo do mesmo nome → aceite se há só 1 na lista com essa raiz
  - Característica visual ("a pintada","a amarela") sem equivalente na lista → PERGUNTE
  - Mais de um correspondente possível → pergunte qual
  - Não encontrado → pergunte "Não encontrei '[nome]' no rebanho. Qual é o nome cadastrado?"
  - No JSON, campo "animal" deve ser SEMPRE o nome exato como está na lista.
""" + _COMMON_TAIL

SYSTEM_ARMAZEM = """Você é o agente do ARMAZÉM/SANITÁRIO do MilkShow, assistente de fazenda leiteira.
Gerencie aplicações de medicamentos, vacinas e uso de insumos do estoque.

ESTOQUE ATUAL:
{estoque}

ANIMAIS NO REBANHO (para identificar animal em GASTO_SANITARIO):
{animais}

MEMÓRIA DA FAZENDA:
{memoria}

{ultimo_salvo_bloco}

TIPOS QUE VOCÊ GERENCIA:

GASTO_SANITARIO — aplicação de medicamento, vacina ou procedimento veterinário
  Obrigatórios: produto, tipo_sanitario, modo, custo.
  CUSTO É OBRIGATÓRIO — se não informado, PERGUNTE: "Qual foi o custo desse procedimento?"
  Se individual: animal. Opcional: qtd_usada.
  tipo_sanitario (infira): Vacina | Antibiótico | Hormônio | Vermífugo | Casqueamento | Outros
  Mapeamentos:
    ocitocina/oxitocina → Hormônio
    ivermectina/ivomec → Vermífugo
    penicilina/amoxicilina/enrofloxacina/cortvet → Antibiótico
    aftosa/brucelose/raiva → Vacina
    casqueamento/casco → Casqueamento
  Aceita: "apliquei","dei","usei","tratei","vacinou","curei","botei"
  VALIDAÇÃO DE ESTOQUE: se o produto NÃO estiver na lista ESTOQUE ATUAL, avise:
    "Não encontrei [produto] no estoque. Deseja registrar assim mesmo?"
    Se confirmar → salve normalmente. Se negar → pergunte o nome correto.

COMPRA_PRODUTO (insumos/medicamentos) — quando comprar produto para estoque
  Obrigatórios: produto, qtd, unidade, valor. Opcional: fornecedor.
  Categoria "Medicamento / Sanitário" para vacinas, vermífugos, antibióticos, hormônios.
  Categoria "Ração / Nutrição" para ração, concentrado, sal mineral.
  Categoria "Infraestrutura" para materiais de construção.

AGENDAR_SANITARIO — agendar protocolo veterinário futuro (vacinação, exame, tratamento)
  Obrigatórios: tipo_sanitario, protocolo (nome do procedimento/vacina), data (data futura), animal (ou "Rebanho").
  Opcional: obs, custo (estimado).
  Este tipo AGENDA para o futuro — diferente de GASTO_SANITARIO que registra algo já feito.
  Aceita: "agenda vacinação","programa exame","marcar tratamento","protocolo para","agendar"
  Mostre resumo com data futura: "Agendar: [protocolo] para [animal] em [data]. Confirma?"
  DATA É OBRIGATÓRIA — se não informar, pergunte: "Para qual data quer agendar?"

EXECUTAR_PROTOCOLO — marcar protocolo sanitário agendado como executado/realizado
  Obrigatórios: protocolo (fragmento do nome) e/ou animal.
  Opcional: data (data em que foi executado, padrão = hoje), custo (real, se diferente do estimado).
  O sistema busca o protocolo pendente (executado=false) mais próximo que bata com os dados.
  Aceita: "executei","realizei","fiz a vacinação","cumpri o protocolo","fizemos o tratamento","já apliquei"
  Mostre o que encontrou antes de confirmar: "Marcar como executado: [protocolo] — [animal] agendado em [data]. Confirma?"

APAGAR_ITEM_ESTOQUE — remover item completamente do armazém
  Obrigatórios: produto (nome do item a remover).
  Use quando o produto acabou, foi descartado ou foi cadastrado errado.
  SEMPRE peça confirmação: "Remover [produto] do estoque. Confirma?"
  Aceita: "remove do estoque","apaga o item","exclui do armazém","acabou e não tenho mais","tira o [produto]"
""" + _COMMON_TAIL

SYSTEM_CONSULTA = """Você é o agente de CONSULTAS do MilkShow, assistente de fazenda leiteira.
Responda perguntas sobre dados da fazenda com base no contexto fornecido.

ANIMAIS NO REBANHO:
{animais}

ESTOQUE ATUAL:
{estoque}

DADOS DA FAZENDA:
{dados_fazenda}

MEMÓRIA DA FAZENDA:
{memoria}

{ultimo_salvo_bloco}

TIPOS QUE VOCÊ GERENCIA:

PERGUNTA — produtor quer saber algo sobre os dados da fazenda
  Use estado CONSULTA. Responda com os dados disponíveis no contexto DADOS DA FAZENDA.
  Resposta: curta e direta (máximo 4 linhas).

  Perguntas gerais: "qual minha produção esta semana?","quanto gastei?","quais vacas estão secas?",
    "qual vaca produz mais?","qual meu saldo?","quanto tenho de ivermectina?","quantos animais tenho?"

  Perguntas de AGENDA (use seção AGENDA dos dados):
    "o que tenho pra fazer hoje?","tem alguma vaca pra inseminar?","tem parto previsto?","o que ta pendente?"

  Perguntas de RENTABILIDADE (use seção RENTABILIDADE POR ANIMAL dos dados):
    "quanto custa produzir um litro?","qual vaca dá mais prejuízo?","estou tendo lucro?",
    "qual o custo por litro da [vaca]?","vale a pena manter a [vaca]?","qual minha vaca mais rentável?"
    → Cite custo/L, lucro/L e status (OK/ATENCAO/PREJUIZO) de cada animal relevante.

  Se a pergunta for sobre algo que não está nos dados → estado SEM_RESPOSTA:
    "Desculpe, não consigo responder a isso ainda."

RESPONDA SEMPRE EM JSON VÁLIDO sem markdown:
{"texto":"resposta ao produtor","estado":"CONSULTA|SEM_RESPOSTA","tipo":"PERGUNTA","dados":{},"itens":null}
"""

SYSTEM_CONFIG = """Você é o agente de CONFIGURAÇÃO do MilkShow, assistente de fazenda leiteira.
Gerencie configurações da fazenda e ajustes de estoque.

ESTOQUE ATUAL:
{estoque}

CONFIGURAÇÕES ATUAIS DA FAZENDA:
{dados_fazenda}

MEMÓRIA DA FAZENDA:
{memoria}

{ultimo_salvo_bloco}

TIPOS QUE VOCÊ GERENCIA:

ALTERAR_CONFIG — alterar configuração da fazenda
  Obrigatórios: chave, valor_novo.
  chave pode ser:
    "preco_leite" → preço por litro de leite pago ao produtor
    "custo_por_litro" → custo médio de produção por litro
    "meta_producao" → meta diária de litros
    "nome_fazenda" → nome da fazenda
  Mostre o que vai mudar: "Mudar [chave] de [atual] para [novo]. Confirma?"
  Aceita: "muda o preço do leite","meu custo por litro é","meta de produção é","quero definir","atualiza"

AJUSTAR_ESTOQUE — corrigir quantidade de um item no armazém manualmente
  Obrigatórios: produto, qtd, operacao.
  operacao: "definir" (setar exato), "adicionar" (somar), "remover" (subtrair).
  Mostre resumo: "Ajustar [produto]: [operacao] [X] [un]. Confirma?"
  Aceita: "ajusta o estoque","tenho [X] sacos de","corrija a quantidade de","inventário de"
  Exemplo: "tenho 8 sacos de ração" → AJUSTAR_ESTOQUE, produto=ração, qtd=8, operacao=definir
""" + _COMMON_TAIL

# Mapeamento domínio → quais seções de dados_fazenda carregar
_SECOES_POR_DOMINIO = {
    "producao":   ["producao"],
    "financeiro": ["financeiro", "estoque"],
    "rebanho":    ["animais", "reproducao"],
    "armazem":    ["estoque", "sanitario"],
    "config":     ["config", "estoque"],
    "consulta":   None,   # None = todas as seções
    "desconhecido": None,
}

# ─────────────────────────────────────────────
# CASCATA DE IAs — prioridade: grátis → pago
# Ordem: Groq (LLaMA grátis) → Gemini Flash (grátis) → Claude Haiku (pago)
# ─────────────────────────────────────────────
def _extrair_json(raw: str) -> dict:
    """Extrai JSON do texto retornado pela IA, tolerante a texto extra."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        try:
            return json.loads(m.group()) if m else {}
        except Exception:
            return {}


def _ia_groq(system: str, historico: list, fast: bool = False) -> str | None:
    """Groq — grátis: 30 req/min, 14.400 req/dia.
    fast=True → llama-3.1-8b-instant (~0.3s) para registros simples.
    fast=False → llama-3.3-70b-versatile (~1.5s) para consultas complexas.
    Em caso de rate limit (429), aguarda retry-after e tenta novamente.
    """
    key = os.environ.get("GROQ_API_KEY", "")
    if not key:
        return None
    model = "llama-3.1-8b-instant" if fast else "llama-3.3-70b-versatile"
    try:
        import httpx as _hx
        msgs = [{"role": "system", "content": system}] + historico[-8:]
        r = _hx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": model, "messages": msgs,
                  "max_tokens": 600, "temperature": 0.1},
            timeout=15,
        )
        if r.status_code == 429:
            # Rate limit — respeita retry-after e tenta novamente
            retry_after = float(r.headers.get("retry-after", "60"))
            wait = min(retry_after, 55)
            log.warning(f"Groq rate limit — aguardando {wait:.0f}s")
            import time as _t; _t.sleep(wait)
            r = _hx.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={"model": model, "messages": msgs,
                      "max_tokens": 600, "temperature": 0.1},
                timeout=15,
            )
        txt = r.json()["choices"][0]["message"]["content"].strip()
        log.info(f"IA: Groq OK ({model})")
        return txt
    except Exception as e:
        log.warning(f"Groq falhou: {e}")
        return None


def _ia_gemini(system: str, historico: list) -> str | None:
    """Gemini 2.0 Flash — grátis: 15 req/min, 1M tokens/dia."""
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key:
        return None
    try:
        import httpx as _hx
        # Gemini usa formato diferente — concatena system + histórico como turns
        contents = []
        for msg in historico[-8:]:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})
        body = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": contents,
            "generationConfig": {"maxOutputTokens": 600, "temperature": 0.1},
        }
        r = _hx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.0-flash:generateContent?key={key}",
            json=body,
            timeout=10,
        )
        txt = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        log.info("IA: Gemini OK")
        return txt
    except Exception as e:
        log.warning(f"Gemini falhou: {e}")
        return None


def _ia_claude(system: str, historico: list) -> str | None:
    """Claude Haiku — pago, usado só como último recurso."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return None
    try:
        from anthropic import Anthropic
        resp = Anthropic(api_key=key).messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            system=system,
            messages=historico[-8:],
        )
        txt = resp.content[0].text.strip()
        log.info("IA: Claude Haiku OK")
        return txt
    except Exception as e:
        log.warning(f"Claude Haiku falhou: {e}")
        return None


def _eh_mensagem_simples(historico: list) -> bool:
    """Detecta se a última mensagem é simples o suficiente para o modelo rápido.
    Usa llama-3.1-8b-instant (0.3s) em vez do 70B (1.5s).
    """
    if len(historico) > 2:          # conversa em andamento → usa modelo forte
        return False
    ultima = (historico[-1].get("content") or "").lower().strip()
    simples = [
        r'^\d+[.,]?\d*\s*(litros?|l)\b',           # "450 litros"
        r'^(sim|nao|não|ok|s|n|isso|correto|bora|pode|cancela?r?|esquece)$',
        r'^(ajuda|help|oi|olá|ola|estoque|resumo|reset|cancelar)$',
        r'^(sim|não),?\s*(confirma|cancela)',
    ]
    return any(re.match(p, ultima) for p in simples)


def _fast_path(texto: str, fazenda_id: str) -> dict | None:
    """Resolve registros óbvios sem chamar IA — retorno em <1ms.
    Cobre o caso mais comum: 'X litros [turno]' → PRODUCAO_LEITE direto.
    """
    hoje  = datetime.date.today().isoformat()
    lower = texto.lower().strip()

    # "450 litros" / "450l" / "450 litros tarde"
    m = re.match(
        r'^(\d+[.,]?\d*)\s*(?:litros?|l)\b'
        r'(?:\s+(?:de\s+)?(?:hoje|ontem))?\s*'
        r'(?:[,-]?\s*(manha|manhã|tarde|noite))?'
        r'(?:\s+(?:de\s+)?(?:hoje|ontem))?\s*$',
        lower
    )
    if m:
        litros = float(m.group(1).replace(',', '.'))
        turno_str = m.group(2) or "manhã"
        turno = {"manha": 1, "manhã": 1, "tarde": 2, "noite": 3}.get(turno_str, 1)
        if 0 < litros < 20000:
            turno_nome = {1: "Manhã", 2: "Tarde", 3: "Noite"}[turno]
            return {
                "texto": f"✅ *{litros:.0f} L* registrados — {turno_nome}.",
                "estado": "SALVAR", "tipo": "PRODUCAO_LEITE",
                "dados": {"litros": litros, "turno": turno, "data": hoje},
                "itens": None,
            }
    return None


def _get_memoria_fazenda(fazenda_id: str) -> str:
    """Carrega preferências aprendidas da fazenda — preço do leite, termos customizados."""
    key = f"mem:{fazenda_id}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    try:
        db  = _db()
        ref = db.collection("fazendas").document(fazenda_id) if fazenda_id != "default" \
              else db.collection("config").document("memoria_bot")
        doc = ref.collection("memoria_bot").document("preferencias").get() \
              if fazenda_id != "default" \
              else db.collection("config").document("memoria_bot").get()
        if doc.exists:
            d = doc.to_dict()
            linhas = []
            if d.get("preco_leite"):
                linhas.append(f"Preço do leite desta fazenda: R${d['preco_leite']}/L")
            if d.get("termos"):
                for orig, trad in d["termos"].items():
                    linhas.append(f'"{orig}" nesta fazenda = "{trad}"')
            if d.get("notas"):
                linhas.append(d["notas"])
            mem = "\n".join(linhas)
            _cache_set(key, mem, 3600)
            return mem
    except Exception:
        pass
    _cache_set(key, "", 3600)
    return ""


def _salvar_memoria(fazenda_id: str, chave: str, valor):
    """Persiste preferência aprendida para uso futuro."""
    try:
        db  = _db()
        if fazenda_id == "default":
            ref = db.collection("config").document("memoria_bot")
        else:
            ref = db.collection("fazendas").document(fazenda_id)\
                    .collection("memoria_bot").document("preferencias")
        ref.set({chave: valor}, merge=True)
        _cache_del(f"mem:{fazenda_id}")
    except Exception as e:
        log.warning(f"salvar_memoria: {e}")


def _ctx_ultimo_salvo(ultimo_salvo: dict | None) -> str:
    """Formata bloco de contexto do último registro salvo."""
    if not ultimo_salvo:
        return ""
    tipo_us  = ultimo_salvo.get("tipo", "")
    itens_us = ultimo_salvo.get("itens") or []
    dados_us = ultimo_salvo.get("dados") or {}
    if itens_us:
        resumo = ", ".join(
            f"{it.get('produto') or it.get('animal') or 'item'}"
            f" {it.get('qtd','')}{it.get('unidade','')} R${it.get('valor','?')}"
            for it in itens_us[:10]
        )
        ctx = f"ÚLTIMO REGISTRO SALVO: {tipo_us} — {resumo}."
    else:
        animal = dados_us.get('animal', '')
        valor  = dados_us.get('valor', '')
        ctx = f"ÚLTIMO REGISTRO SALVO: {tipo_us} — animal: {animal}, valor: R${valor}."
    return ctx + " Se o produtor referenciar 'esses itens', 'isso', 'os mesmos' etc., está se referindo a este registro."


# Tipos por domínio (para roteamento direto quando tipo já é conhecido)
_TIPOS_POR_DOMINIO: dict[str, set] = {
    "producao":   {"PRODUCAO_LEITE", "PRODUCAO_MULTIPLA", "VENDA_LEITE",
                   "CORRIGIR_PRODUCAO", "APAGAR_PRODUCAO"},
    "financeiro": {"COMPRA_PRODUTO", "GASTO_GERAL", "VENDA_ANIMAL", "COMPRA_ANIMAL",
                   "CORRIGIR_LANCAMENTO", "APAGAR_LANCAMENTO"},
    "rebanho":    {"NOVO_ANIMAL", "COMPRA_ANIMAL", "REPRODUCAO", "ATUALIZAR_ANIMAL"},
    "armazem":    {"GASTO_SANITARIO", "AGENDAR_SANITARIO", "EXECUTAR_PROTOCOLO", "APAGAR_ITEM_ESTOQUE"},
    "config":     {"ALTERAR_CONFIG", "AJUSTAR_ESTOQUE"},
    "consulta":   {"PERGUNTA"},
}

_DOMINIO_POR_TIPO: dict[str, str] = {
    t: d for d, ts in _TIPOS_POR_DOMINIO.items() for t in ts
}


def _pre_classificar_keywords(texto: str) -> tuple[str, str] | None:
    """Classificação rápida por palavras-chave antes de chamar a IA.
    Evita classificações erradas para casos muito comuns e ambíguos.
    Retorna (dominio, tipo) ou None para deixar a IA decidir.
    """
    import re as _re
    lower = texto.lower()

    # ── Serviço externo (vet pago por fora) — ANTES dos meds para evitar conflito com "vacinar"
    if any(k in lower for k in ['paguei veterinário','paguei o veterinário','paguei vet ',
                                  'paguei o vet','visita do vet','honorários do vet',
                                  'consulta veterinária','taxa de visita','visita técnica',
                                  'paguei técnico','paguei o técnico','paguei inseminador',
                                  'veterinário pra vacinar','vet pra vacinar',
                                  'paguei para vacinar','paguei pra vacinar']):
        return ("financeiro", "GASTO_GERAL")

    # ── Veterinário/sanitário — palavras de medicação/procedimento
    # 'vacin' como prefixo cobre: vacin (typo), vacina, vacinar, vacinei, vacinação
    _meds = ['ivermectina','ivermctina','ivermectin','ocitocina','ocitosina','oxitocina',
             'penicilina','penicilna','antibiotico','antibiótico','vermifugo','vermífugo',
             'vacin','aftosa','brucelose','brucel','mastite',
             'cortvet','cortisona','dexametasona','vitamina','antiparasit',
             'casquei','casquiei','casqueamento','casqueei','casco','casquear',
             'botei remo','dei remo','remo no','remo nas','remo pras',
             'botei ocitocina','botei ocitosina','botei penicilina','botei ivermectina',
             'usei dose','usei doses','apliquei dose','apliquei doses',
             'dei remédio','dei rémédio','dei remedio']
    if any(k in lower for k in _meds):
        # Se for agendamento futuro
        if any(k in lower for k in ['agenda','agendar','próxima','próximo','semana que vem',
                                      'para sexta','para quinta','para segunda','para terça','para quarta']):
            return ("armazem", "AGENDAR_SANITARIO")
        # Se for execução de protocolo já agendado
        if any(k in lower for k in ['executei','realizei','fiz o protocolo','fiz a vacinação',
                                      'executei o protocolo','realizei o protocolo']):
            return ("armazem", "EXECUTAR_PROTOCOLO")
        return ("armazem", "GASTO_SANITARIO")

    # ── Configuração — meta, custo, preço do leite
    if any(k in lower for k in ['minha meta','meta de produção','meta é','meta e ','meta:',
                                   'custo por litro','custo/litro','preço por litro',
                                   'preco por litro','valor do leite','pagar por litro',
                                   'laticinio vai pagar','laticínio vai pagar',
                                   'vai pagar por litro','vai pagar r$','cooperativa vai pagar']):
        return ("config", "ALTERAR_CONFIG")

    # ── Execução de protocolo já agendado (sem nome de medicamento)
    if any(k in lower for k in ['executei a vacinação','realizei a vacinação','fiz a vacinação',
                                  'executei o protocolo','realizei o protocolo',
                                  'executei o tratamento','realizei o tratamento']):
        return ("armazem", "EXECUTAR_PROTOCOLO")

    # ── Peão/vaqueiro/diarista — sempre GASTO_GERAL
    if any(k in lower for k in ['paguei o peão','paguei peão','paguei o vaqueiro',
                                  'paguei diarista','paguei o diarista','paguei funcionário',
                                  'salário do peão','salário do vaqueiro','conto pro peão',
                                  'conto pra diarista','paguei pro peão','paguei pra diarista']):
        return ("financeiro", "GASTO_GERAL")

    # ── Reprodução — secagem
    if any(k in lower for k in ['pra secar','para secar','vou secar','botei secar',
                                  'mandei secar','vai secar','botei pra secar','botar pra secar']):
        return ("rebanho", "REPRODUCAO")

    # ── Venda de animal (nome próprio + valor) — NÃO é venda de leite
    if _re.search(r'vend[ie][i]?\s+(a\s+|o\s+|um\s+|uma\s+)?\w', lower):
        if not any(k in lower for k in ['leite','litros','lati','cooper']):
            return ("financeiro", "VENDA_ANIMAL")

    # ── Produção de leite — gírias e padrões diretos
    _prod_kw = ['capinei','capinagem','ordenhei','tirei leite','tirei o leite',
                'ordenha de hoje','ordenha de manhã','ordenha de tarde',
                'litros essa manhã','litros essa tarde','litros de manhã','litros de tarde',
                'litros hoje','litros no total']
    if any(k in lower for k in _prod_kw):
        # Padrão lista animais dentro do mesmo texto → PRODUCAO_MULTIPLA
        if _re.search(r'[A-Za-zÀ-ú]{3,}\s+\d+\s*[,;]\s*[A-Za-zÀ-ú]{3,}\s+\d+', texto):
            return ("producao", "PRODUCAO_MULTIPLA")
        return ("producao", "PRODUCAO_LEITE")

    # ── Padrão "deu N [litros/de manhã]" — produção individual com nome de animal
    if _re.search(r'\bdeu\s+\d+[\.,]?\d*\s*(litros?|de\s+manh|de\s+tard|l\b)', lower):
        return ("producao", "PRODUCAO_LEITE")

    # ── Padrão lista de animais: "Nome N, Nome N" → PRODUCAO_MULTIPLA
    if _re.search(r'[A-Za-zÀ-ú]{3,}\s+\d+\s*[,;]\s*[A-Za-zÀ-ú]{3,}\s+\d+', texto):
        return ("producao", "PRODUCAO_MULTIPLA")

    return None


def _classificar_dominio(historico: list, animais: str) -> tuple[str, str]:
    """Usa Groq 8B (rápido) para classificar domínio e tipo da última mensagem.
    Retorna (dominio, tipo). Em caso de falha retorna ("desconhecido", "DESCONHECIDO").
    """
    # Tenta pré-classificação por palavras-chave antes de chamar a IA
    ultima_msg = historico[-1]["content"] if historico else ""
    pre = _pre_classificar_keywords(ultima_msg)
    if pre:
        log.info(f"Pre-classificador → domínio={pre[0]}, tipo={pre[1]}")
        return pre

    system = SYSTEM_CLASSIFICADOR.replace("{animais}", animais[:500])
    # Passa apenas a última mensagem do usuário para manter o classificador rápido
    ultima = [historico[-1]] if historico else []
    raw = _ia_groq(system, ultima, fast=True)
    if not raw:
        return ("desconhecido", "DESCONHECIDO")
    parsed = _extrair_json(raw)
    if not parsed:
        return ("desconhecido", "DESCONHECIDO")
    dominio = parsed.get("dominio", "desconhecido")
    tipo    = parsed.get("tipo", "DESCONHECIDO")
    log.info(f"Classificador → domínio={dominio}, tipo={tipo}")
    return (dominio, tipo)


def _chamar_agente(dominio: str, historico: list, animais: str, estoque: str,
                   dados_fazenda: str, memoria: str, ultimo_salvo: dict | None,
                   tipo_hint: str | None = None) -> dict:
    """Chama o agente específico do domínio com seu prompt focado.
    Fallback: cascata Groq 70B → Gemini → Claude → SYSTEM monolítico.
    """
    ctx_ultimo = _ctx_ultimo_salvo(ultimo_salvo)
    ultimo_salvo_bloco = f"CONTEXTO PÓS-SALVAR: {ctx_ultimo}" if ctx_ultimo else ""
    mem = memoria or "nenhuma preferência salva"

    # Seleciona system prompt do agente correto
    if dominio == "producao":
        system = (SYSTEM_PRODUCAO
                  .replace("{animais}", animais)
                  .replace("{memoria}", mem)
                  .replace("{ultimo_salvo_bloco}", ultimo_salvo_bloco))
    elif dominio == "financeiro":
        system = (SYSTEM_FINANCEIRO
                  .replace("{estoque}", estoque)
                  .replace("{memoria}", mem)
                  .replace("{ultimo_salvo_bloco}", ultimo_salvo_bloco))
    elif dominio == "rebanho":
        system = (SYSTEM_REBANHO
                  .replace("{animais}", animais)
                  .replace("{memoria}", mem)
                  .replace("{ultimo_salvo_bloco}", ultimo_salvo_bloco))
    elif dominio == "armazem":
        system = (SYSTEM_ARMAZEM
                  .replace("{estoque}", estoque)
                  .replace("{animais}", animais)
                  .replace("{memoria}", mem)
                  .replace("{ultimo_salvo_bloco}", ultimo_salvo_bloco))
    elif dominio == "consulta":
        system = (SYSTEM_CONSULTA
                  .replace("{animais}", animais)
                  .replace("{estoque}", estoque)
                  .replace("{dados_fazenda}", dados_fazenda)
                  .replace("{memoria}", mem)
                  .replace("{ultimo_salvo_bloco}", ultimo_salvo_bloco))
    elif dominio == "config":
        system = (SYSTEM_CONFIG
                  .replace("{estoque}", estoque)
                  .replace("{dados_fazenda}", dados_fazenda)
                  .replace("{memoria}", mem)
                  .replace("{ultimo_salvo_bloco}", ultimo_salvo_bloco))
    else:
        # Fallback: SYSTEM monolítico original
        system = (SYSTEM
                  .replace("{animais}", animais)
                  .replace("{estoque}", estoque)
                  .replace("{dados_fazenda}", dados_fazenda)
                  .replace("{memoria}", mem)
                  .replace("{ultimo_salvo}", ctx_ultimo))

    # Injeta tipo_hint do pre-classificador para garantir que o agente não mude o tipo
    if tipo_hint:
        system = system + f"\n\n⚠️ TIPO JÁ IDENTIFICADO PELO PRÉ-CLASSIFICADOR: {tipo_hint}. Use EXATAMENTE este tipo no JSON — não altere."

    # Cascata: Groq 70B → Gemini → Claude Haiku
    raw = _ia_groq(system, historico, fast=False)
    if not raw:
        raw = _ia_gemini(system, historico)
    if not raw:
        raw = _ia_claude(system, historico)

    if not raw:
        # Mesmo sem resposta da IA, preserva tipo do pré-classificador
        if tipo_hint:
            return {"texto": "Entendi! Aguarde um momento.", "estado": "COLETANDO", "tipo": tipo_hint, "dados": {}}
        return {"texto": "Erro ao processar. Tente novamente.", "estado": "ERRO", "tipo": None, "dados": {}}

    parsed = _extrair_json(raw)
    if not parsed:
        parsed = {"texto": raw[:300], "estado": "COLETANDO", "tipo": tipo_hint, "dados": {}}
    # Se o pré-classificador identificou o tipo, ele tem prioridade sobre o agente
    if tipo_hint and parsed.get("tipo") != tipo_hint:
        log.info(f"Pré-classificador override: agente={parsed.get('tipo')} → {tipo_hint}")
        parsed["tipo"] = tipo_hint
    return parsed


def _chamar_claude(historico: list, animais: str, estoque: str = "",
                   dados_fazenda: str = "", memoria: str = "",
                   ultimo_salvo: dict = None, tipo_atual: str = None) -> dict:
    """Orquestra agentes por domínio: Classificador → Agente Domínio → resultado.
    tipo_atual: tipo já identificado em conversa anterior (pula classificação).
    """
    tipo_hint = None
    # Se o tipo já é conhecido, roteia direto para o agente certo
    if tipo_atual and tipo_atual in _DOMINIO_POR_TIPO:
        dominio = _DOMINIO_POR_TIPO[tipo_atual]
        log.info(f"Roteamento direto → domínio={dominio} (tipo={tipo_atual})")
    else:
        # Primeira mensagem ou tipo desconhecido → classificador rápido
        # Verifica pré-classificador ANTES para extrair tipo_hint de alta confiança
        ultima_msg = historico[-1]["content"] if historico else ""
        pre = _pre_classificar_keywords(ultima_msg)
        if pre:
            dominio, tipo_hint = pre  # tipo_hint só é definido quando pré-classificador dispara
            log.info(f"Pre-classificador → domínio={dominio}, tipo={tipo_hint}")
        else:
            dominio, _ = _classificar_dominio(historico, animais)  # IA classifica, sem tipo_hint

    return _chamar_agente(dominio, historico, animais, estoque,
                          dados_fazenda, memoria, ultimo_salvo,
                          tipo_hint=tipo_hint)


def _processar(tel: str, texto: str, fazenda_id: str, permissoes: Optional[list] = None) -> str:
    if permissoes is None:
        permissoes = ["admin"]
    conv = _get_conv(tel)

    # TTL: abandona conversas COLETANDO/CONFIRMANDO com mais de 2h
    if conv.get("estado") not in ("idle", None):
        ts_str = conv.get("ts", "")
        if ts_str:
            try:
                idade = (datetime.datetime.now() -
                         datetime.datetime.fromisoformat(ts_str)).total_seconds()
                if idade > 7200:  # 2 horas
                    _clear_conv(tel)
                    conv = {"historico": [], "estado": "idle", "dados": {}, "tipo": None}
            except Exception:
                pass

    # Rate limit: máx 10 mensagens/min por número
    if not _rate_ok(tel, max_por_min=10):
        log.warning(f"[{tel}] rate limit atingido")
        return "Muitas mensagens em pouco tempo. Aguarde um momento e tente novamente."

    animais = _ctx_animais(fazenda_id)
    estoque = _ctx_estoque(fazenda_id)

    # Comandos rápidos (sem IA)
    lower = texto.lower().strip()
    if lower in ("ajuda", "help", "oi", "olá", "ola"):
        _clear_conv(tel)
        return (
            "*MilkShow Bot*\n"
            "Envie mensagens naturais como:\n"
            "- Comprei 5 sc racao por R$300\n"
            "- Apliquei ivermectina no rebanho, R$80\n"
            "- Paguei R$400 de mao de obra\n"
            "- Vendi 1200L por R$1800\n"
            "- Ordenha de hoje 450 litros\n"
            "- Inseminei a Rainha hoje\n"
            "- estoque | cancelar"
        )
    if lower in ("cancelar", "cancela", "reiniciar", "reset"):
        _clear_conv(tel)
        return "Conversa reiniciada. O que deseja registrar?"
    if lower == "estoque":
        return f"*Estoque atual:*\n{_ctx_estoque(fazenda_id)}"

    hist = conv.get("historico", [])
    hist.append({"role": "user", "content": texto})

    # Fast path — resolve registros simples sem IA
    if conv.get("estado") in ("idle", None):
        fp = _fast_path(texto, fazenda_id)
        if fp:
            log.info(f"[{tel}] fast_path: {fp['tipo']}")
            if fp["estado"] == "SALVAR" and fp.get("tipo") and fp.get("dados"):
                if _tem_permissao(permissoes, fp["tipo"]):
                    resposta_fp = _salvar(fp["tipo"], fp["dados"], fazenda_id, registrado_por=tel)
                    _clear_conv(tel)
                    return resposta_fp
                else:
                    _clear_conv(tel)
                    return _msg_sem_permissao(fp["tipo"])

    # Contexto seletivo: para consultas carrega dados da fazenda; outros domínios não precisam
    tipo_atual = conv.get("tipo")  # tipo já conhecido de turno anterior
    memoria    = _get_memoria_fazenda(fazenda_id)
    ultimo_salvo = conv.get("ultimo_salvo")

    # Determina domínio para decidir quais seções carregar
    if tipo_atual and tipo_atual in _DOMINIO_POR_TIPO:
        dominio_hint = _DOMINIO_POR_TIPO[tipo_atual]
    else:
        dominio_hint = None  # será descoberto pelo classificador

    # Carrega dados_fazenda conforme o domínio
    if dominio_hint in ("consulta", "config") or (dominio_hint is None and _classificar_pergunta(texto)):
        secoes = _classificar_pergunta(texto)
        dados_fazenda = _ctx_dados_fazenda(fazenda_id, secoes) if secoes else _ctx_dados_fazenda(fazenda_id, None)
    else:
        dados_fazenda = ""

    parsed   = _chamar_claude(hist, animais, estoque, dados_fazenda, memoria, ultimo_salvo,
                               tipo_atual=tipo_atual)
    estado   = parsed.get("estado", "COLETANDO")
    tipo_raw = parsed.get("tipo") or conv.get("tipo")
    # Normaliza tipos hallucinations → tipos canônicos
    _TIPO_ALIASES = {
        # Producao
        "REGISTRAR_PRODUCAO":  "PRODUCAO_LEITE",
        "REGISTRO_PRODUCAO":   "PRODUCAO_LEITE",
        "PRODUCAO":            "PRODUCAO_LEITE",
        "ORDENHA":             "PRODUCAO_LEITE",
        "CAPINA":              "PRODUCAO_LEITE",
        "COLHEITA_LEITE":      "PRODUCAO_LEITE",
        "COLHEITA":            "PRODUCAO_LEITE",
        "LEITE":               "PRODUCAO_LEITE",
        "MULTIPLO":            "PRODUCAO_MULTIPLA",
        "PRODUCAO_TOTAL":      "PRODUCAO_MULTIPLA",
        # Sanitario
        "REGISTRAR_SANITARIO": "GASTO_SANITARIO",
        "REGISTRO_SANITARIO":  "GASTO_SANITARIO",
        "SANITARIO":           "GASTO_SANITARIO",
        "TRATAMENTO":          "GASTO_SANITARIO",
        "TRATAMENTO_ANIMAL":   "GASTO_SANITARIO",
        "APLICACAO":           "GASTO_SANITARIO",
        "VACINACAO":           "GASTO_SANITARIO",
        "VERMIFUGACAO":        "GASTO_SANITARIO",
        # Financeiro
        "LANCAMENTO":          "GASTO_GERAL",
        "DESPESA":             "GASTO_GERAL",
        "COMPRA":              "COMPRA_PRODUTO",
        "VENDA":               "VENDA_LEITE",
        # Rebanho
        "ANIMAL":              "NOVO_ANIMAL",
        "CADASTRO_ANIMAL":     "NOVO_ANIMAL",
        "NASCIMENTO":          "NOVO_ANIMAL",
        "REPRODUCAO_ANIMAL":   "REPRODUCAO",
        "EVENTO_REPRODUTIVO":  "REPRODUCAO",
        "ATUALIZACAO_ANIMAL":  "ATUALIZAR_ANIMAL",
        # Protocolo
        "PROTOCOLO":           "EXECUTAR_PROTOCOLO",
        "EXECUTAR":            "EXECUTAR_PROTOCOLO",
        "AGENDAR":             "AGENDAR_SANITARIO",
        # Config
        "SALVAR_PREFERENCIA":  "ALTERAR_CONFIG",
        "CONFIGURACAO":        "ALTERAR_CONFIG",
        "CONFIG":              "ALTERAR_CONFIG",
        "PREFERENCIA":         "ALTERAR_CONFIG",
        "AJUSTE_ESTOQUE":      "AJUSTAR_ESTOQUE",
    }
    tipo = _TIPO_ALIASES.get(tipo_raw, tipo_raw) if tipo_raw else None
    novos    = {k: v for k, v in (parsed.get("dados") or {}).items() if v is not None}
    dados    = {**(conv.get("dados") or {}), **novos}
    resposta = parsed.get("texto", "Nao entendi. Tente novamente.")

    hist.append({"role": "assistant", "content": json.dumps(parsed, ensure_ascii=False)})

    # Verifica permissão assim que o tipo é identificado (1ª vez — conversa era idle)
    # Evita que o usuário passe por toda a coleta só para ser bloqueado no final
    if tipo and conv.get("estado") in ("idle", None) and not _tem_permissao(permissoes, tipo):
        _clear_conv(tel)
        return _msg_sem_permissao(tipo)

    if estado == "SALVAR":
        # Verifica de novo no SALVAR (segurança dupla — caso tipo mude durante coleta)
        if tipo and not _tem_permissao(permissoes, tipo):
            _clear_conv(tel)
            return _msg_sem_permissao(tipo)

        ultimo_salvo = None
        try:
            itens = parsed.get("itens") or conv.get("itens")
            # Fallback: varre histórico da conversa procurando itens de turn anterior
            if not itens and tipo == "PRODUCAO_MULTIPLA":
                for msg in reversed(hist):
                    try:
                        h = json.loads(msg.get("content", "{}"))
                        if h.get("itens"):
                            itens = h["itens"]
                            break
                    except Exception:
                        pass
            if tipo == "PRODUCAO_MULTIPLA" and itens:
                dados["itens"] = itens
                resposta = _salvar(tipo, dados, fazenda_id, registrado_por=tel)
                ultimo_salvo = {"tipo": tipo, "dados": dados, "itens": itens, "resposta": resposta}
            elif itens and isinstance(itens, list) and len(itens) > 1:
                msgs = []
                forn = dados.get("fornecedor") or ""
                for item in itens:
                    item.setdefault("fornecedor", forn)
                    msgs.append(_salvar(tipo, item, fazenda_id, registrado_por=tel))
                resposta = f"*{len(itens)} itens salvos:*\n" + "\n".join(
                    m.replace("*Salvo!*\n", "- ") for m in msgs
                )
                ultimo_salvo = {"tipo": tipo, "dados": dados, "itens": itens, "resposta": resposta}
            else:
                resposta = _salvar(tipo, dados, fazenda_id, registrado_por=tel)
                ultimo_salvo = {"tipo": tipo, "dados": dados, "itens": None, "resposta": resposta}
        except Exception as e:
            log.error(f"Erro ao salvar: {e}")
            resposta = f"Erro ao salvar: {str(e)[:120]}"
        _clear_conv(tel, ultimo_salvo=ultimo_salvo)

    elif estado == "CANCELAR":
        resposta = "Registro cancelado. Pode enviar outro se quiser."
        _clear_conv(tel)

    elif estado == "SEM_RESPOSTA":
        _salvar_sugestao(fazenda_id, texto)
        resposta = "Desculpe, nao consigo responder a isso ainda. Vou anotar sua sugestao para a proxima versao."
        _clear_conv(tel)

    elif estado == "CONSULTA":
        # Mantém histórico para permitir perguntas de follow-up ("e mais?", "e a segunda?")
        conv.update({"historico": hist, "estado": "idle", "dados": {}, "tipo": None})
        _save_conv(tel, conv)

    else:
        itens_parsed = parsed.get("itens")
        conv.update({"historico": hist, "estado": estado, "dados": dados, "tipo": tipo})
        if itens_parsed:
            conv["itens"] = itens_parsed
        elif conv.get("itens"):
            pass  # preserva itens anteriores — não sobrescreve com None
        # Consome ultimo_salvo após 1 uso (evita poluir contexto indefinidamente)
        if conv.get("ultimo_salvo") and estado in ("idle", None, "COLETANDO"):
            conv.pop("ultimo_salvo", None)
        _save_conv(tel, conv)

        # Botões interativos quando entra em confirmação
        if estado == "CONFIRMANDO":
            _enviar_botoes(tel, resposta, [("sim", "✅ Confirmar"), ("nao", "❌ Cancelar")])
            return "__botoes_enviados__"

    return resposta


# ─────────────────────────────────────────────
# SALVAR NO FIREBASE
# ─────────────────────────────────────────────
def _salvar(tipo: str, dados: dict, fazenda_id: str, registrado_por: str = "Bot WhatsApp") -> str:
    hoje = str(datetime.date.today())

    # Invalida cache das coleções que podem ser alteradas por este registro
    _cache_del(f"anm:{fazenda_id}")
    _cache_del(f"est:{fazenda_id}")
    _cache_del(f"prod:{fazenda_id}")
    _cache_del(f"fin:{fazenda_id}")

    def _fin(cat, desc, valor, animal=None, tipo_fin="despesa", data=None):
        """Salva lançamento financeiro com todos os campos que o app espera."""
        _coll(fazenda_id, "financeiro").add({
            "data":           data or hoje,
            # categoria: salvo nos dois campos que o app usa (cat legacy + categoria atual)
            "cat":            cat,
            "categoria":      cat,
            # descricao: salvo nos dois campos por compatibilidade
            "desc":           desc,
            "descricao":      desc,
            "valor":          float(valor or 0),
            # tipo: "receita" ou "despesa" — padrão é despesa
            "tipo":           tipo_fin,
            "animal":         animal,
            "origem":         "whatsapp",
            "registrado_por": registrado_por,
        })

    def _estoque_entrada(item, qtd, un, valor_total):
        qtd = float(qtd or 1)
        # BUG1/12: usa busca case-insensitive para evitar duplicatas (ex: "milho" vs "Milho")
        existente = _buscar_no_estoque(fazenda_id, item)
        if existente:
            did   = existente["doc_id"]
            d_qtd = existente.get("qtd", 0)
            vant  = d_qtd * existente.get("custo_medio", 0)
            nqtd  = d_qtd + qtd
            nmed  = (vant + float(valor_total or 0)) / nqtd if nqtd else 0
            _coll(fazenda_id, "estoque").document(did).update(
                {"qtd": nqtd, "custo_medio": nmed, "un": un or existente.get("un", "un")}
            )
        else:
            cu = float(valor_total or 0) / qtd if qtd else 0
            _coll(fazenda_id, "estoque").add(
                {"item": item, "qtd": qtd, "un": un or "un", "custo_medio": cu}
            )

    def _estoque_baixa(item, qtd):
        qtd = float(qtd or 0)
        # BUG6: usa busca case-insensitive para não falhar silenciosamente
        existente = _buscar_no_estoque(fazenda_id, item)
        if existente:
            nova = max(existente.get("qtd", 0) - qtd, 0)
            _coll(fazenda_id, "estoque").document(existente["doc_id"]).update({"qtd": nova})

    # ── VENDA_ANIMAL ─────────────────────────
    if tipo == "VENDA_ANIMAL":
        animal_raw = dados.get("animal") or dados.get("nome") or "Animal"
        animal, _  = _resolver_animal(fazenda_id, animal_raw)
        val    = _parse_float(dados.get("valor"))
        obs    = dados.get("obs") or ""
        data_venda = dados.get("data") or hoje
        desc   = f"Venda {animal}" + (f" ({obs})" if obs else "")
        _fin("Venda de Animal", desc, val, animal=animal, tipo_fin="receita", data=data_venda)
        # Remove do rebanho
        ani_docs = list(_coll(fazenda_id, "animais").where(filter=FieldFilter("nome", "==", animal)).stream())
        for d in ani_docs:
            _coll(fazenda_id, "animais").document(d.id).update({"status": "Vendido"})
        return f"*Salvo!*\n{animal} vendido por R$ {val:.2f}. Removido do rebanho ativo."

    # ── COMPRA_ANIMAL ────────────────────────
    elif tipo == "COMPRA_ANIMAL":
        nome   = dados.get("nome") or dados.get("animal") or "Animal"
        val    = _parse_float(dados.get("valor"))
        sexo   = dados.get("sexo") or "Fêmea"
        status = dados.get("status_animal") or "Lactação"
        nasc   = dados.get("nasc") or hoje
        lote   = dados.get("lote") or "A"
        # BUG14: usa sufixo numérico para evitar colisão de IDs (Rainha vs Raimunda)
        base_id = nome[:4].upper()
        existing_ids = {d.to_dict().get("id","") for d in _coll(fazenda_id, "animais").stream()}
        ani_id = base_id
        suffix = 2
        while ani_id in existing_ids:
            ani_id = f"{base_id}{suffix}"
            suffix += 1
        _coll(fazenda_id, "animais").add({
            "nome": nome, "sexo": sexo, "status": status,
            "nasc": str(nasc), "lote": lote, "id": ani_id,
            "freq": 2 if status == "Lactação" else 0,
            "prenhez": False, "colostro": False,
            "dt_insem": None, "dt_parto": None, "mae_id": None,
        })
        data_compra_ani = dados.get("data") or hoje
        if val > 0:
            _fin("Compra de Animal", f"Compra {nome}", val, animal=nome, tipo_fin="despesa", data=data_compra_ani)
        return f"*Salvo!*\n{nome} ({status}) cadastrada. R$ {val:.2f} lançado no financeiro."

    # ── COMPRA_PRODUTO ────────────────────────
    elif tipo == "COMPRA_PRODUTO":
        prod  = dados.get("produto") or "Produto"
        qtd   = _parse_float(dados.get("qtd")) or 1.0
        un    = dados.get("unidade") or "un"
        val   = _parse_float(dados.get("valor"))
        forn  = dados.get("fornecedor") or ""
        data_compra = dados.get("data") or hoje

        # Categoria: usa o que a IA classificou; fallback por palavra-chave (4 categorias)
        import unicodedata
        def _sem_acento(s):
            return ''.join(c for c in unicodedata.normalize('NFD', s)
                           if unicodedata.category(c) != 'Mn')
        _p = _sem_acento(prod.lower())
        _CATS_VALIDAS = {"Ração / Nutrição", "Medicamento / Sanitário", "Infraestrutura", "Outros"}
        cat_ia = dados.get("categoria") or ""
        if cat_ia in _CATS_VALIDAS:
            cat = cat_ia
        elif any(k in _p for k in ["ocitocina","oxitocina","vacina","antibiotico","antibi",
                                    "hormonio","vermifugo","ivermec","penicilina","calmosil",
                                    "cortvet","oxytocin","prostagla","amoxicilina","enroflox",
                                    "brucelose","aftosa","raiva"]):
            cat = "Medicamento / Sanitário"
        elif any(k in _p for k in ["racao","milho","soja","silagem","sal mineral","farelo",
                                    "concentrado","capim","feno","minerali"]):
            cat = "Ração / Nutrição"
        elif any(k in _p for k in ["arame","madeira","cimento","tela","cano","bomba",
                                    "cerca","construcao","material","bomba"]):
            cat = "Infraestrutura"
        else:
            cat = "Outros"

        _estoque_entrada(prod, qtd, un, val)

        desc = f"Compra {prod} ({qtd:.1f} {un})"
        if forn:
            desc += f" — {forn}"
        _fin(cat, desc, val, data=data_compra)

        return (f"*Salvo!*\n"
                f"{prod} ({qtd:.1f} {un}) registrado no Armazém.\n"
                f"R$ {val:.2f} lancado em {cat}.")

    # ── GASTO_SANITARIO ───────────────────────
    elif tipo == "GASTO_SANITARIO":
        prod     = dados.get("produto") or "Produto"
        tipo_san = dados.get("tipo_sanitario") or "Outros"
        modo     = "Individual" if str(dados.get("modo","")).lower() == "individual" else "Rebanho Todo"
        animal   = dados.get("animal")
        custo    = _parse_float(dados.get("custo") or dados.get("valor"))
        qtd_u    = _parse_float(dados.get("qtd_usada"))

        data_san = dados.get("data") or hoje
        _coll(fazenda_id, "sanitario").add({
            "data": data_san, "tipo": tipo_san, "prod": prod,
            "modo": modo, "animal": animal,
            "custo": custo, "obs": "Registrado via WhatsApp",
        })

        if custo > 0:
            _fin("Medicamento / Sanitário", f"{tipo_san} — {prod}", custo,
                 animal=animal, tipo_fin="despesa", data=data_san)

        avisos = []
        if qtd_u > 0:
            item_est = _buscar_no_estoque(fazenda_id, prod)
            if item_est:
                _estoque_baixa(prod, qtd_u)
                avisos.append(f"{qtd_u:.1f} {item_est.get('un','un')} baixadas do estoque.")
            else:
                avisos.append(f"Produto '{prod}' nao encontrado no estoque — baixa nao realizada.")

        ani_txt = f" em {animal}" if animal else " no rebanho"
        fin_txt = f"\nR$ {custo:.2f} lancado no Financeiro." if custo > 0 else ""
        aviso_txt = "\n" + "\n".join(avisos) if avisos else ""
        return f"*Salvo!*\n{tipo_san} — {prod}{ani_txt}.{fin_txt}{aviso_txt}"

    # ── GASTO_GERAL ───────────────────────────
    elif tipo == "GASTO_GERAL":
        desc  = dados.get("descricao") or "Gasto geral"
        val   = _parse_float(dados.get("valor"))
        cat   = dados.get("categoria") or "Outros"
        data_geral = dados.get("data") or hoje
        _fin(cat, desc, val, data=data_geral)
        return f"*Salvo!*\n{desc} — R$ {val:.2f} ({cat})"

    # ── VENDA_LEITE ───────────────────────────
    elif tipo == "VENDA_LEITE":
        val      = _parse_float(dados.get("valor"))
        litros   = _parse_float(dados.get("litros"))
        laticinio = dados.get("laticinio") or "Laticínio"
        data_vl  = dados.get("data") or hoje
        desc     = f"Venda leite {laticinio} — {litros:.0f} L"
        _fin("Venda de Leite", desc, val, tipo_fin="receita", data=data_vl)
        preco = val / litros if litros > 0 else 0
        return f"*Salvo!*\n{litros:.0f} L vendidos por R$ {val:.2f} (R$ {preco:.2f}/L)"

    # ── PRODUCAO_LEITE ────────────────────────
    elif tipo == "PRODUCAO_LEITE":
        litros  = _parse_float(dados.get("litros"))
        data    = dados.get("data") or hoje
        # BUG4: Claude pode retornar "manha"/"tarde" em vez de 1/2 — conversão segura
        _turno_raw = dados.get("turno") or 1
        _turno_map = {"manha": 1, "manhã": 1, "tarde": 2, "noite": 3}
        try:
            turno = int(_turno_raw)
        except (ValueError, TypeError):
            turno = _turno_map.get(str(_turno_raw).lower().strip(), 1)
        animal  = dados.get("animal")

        if animal:
            nome_ani, id_ani = _resolver_animal(fazenda_id, animal)
        else:
            id_ani   = "geral"
            nome_ani = "Rebanho"

        _coll(fazenda_id, "producao").add({
            "data": str(data), "leite": litros, "turno": turno,
            "id_animal": id_ani, "nome_animal": nome_ani, "racao": 0,
        })
        turno_txt = {1: "Manhã", 2: "Tarde", 3: "Noite"}.get(turno, "")
        return f"*Salvo!*\n{litros:.0f} L registrados — {nome_ani} ({turno_txt or 'turno ' + str(turno)})"

    # ── NOVO_ANIMAL ───────────────────────────
    elif tipo == "NOVO_ANIMAL":
        nome   = dados.get("nome") or "Sem nome"
        sexo   = dados.get("sexo") or "Fêmea"
        status = dados.get("status_animal") or "Novilha"
        nasc   = dados.get("nasc") or hoje
        lote   = dados.get("lote") or "A"
        base_id2 = nome[:4].upper()
        existing_ids2 = {d.to_dict().get("id","") for d in _coll(fazenda_id, "animais").stream()}
        id_ani = dados.get("id_animal") or base_id2
        sfx = 2
        while id_ani in existing_ids2:
            id_ani = f"{base_id2}{sfx}"
            sfx += 1

        _coll(fazenda_id, "animais").add({
            "nome": nome, "sexo": sexo, "status": status,
            "nasc": str(nasc), "lote": lote, "id": id_ani,
            "freq": 2 if status == "Lactação" else 0,
            "prenhez": False, "colostro": False,
            "dt_insem": None, "dt_parto": None, "mae_id": None,
        })
        return f"*Salvo!*\n{nome} ({sexo}, {status}) cadastrada no rebanho."

    # ── REPRODUCAO ────────────────────────────
    elif tipo == "REPRODUCAO":
        animal, _ = _resolver_animal(fazenda_id, dados.get("animal") or "?")
        evento = dados.get("evento") or "Evento"
        data   = dados.get("data") or hoje
        obs    = dados.get("obs") or ""
        custo  = _parse_float(dados.get("custo"))

        _coll(fazenda_id, "sanitario").add({
            "data": str(data), "tipo": "Reprodução", "prod": evento,
            "modo": "Individual", "animal": animal,
            "custo": custo, "obs": obs or f"Registrado via WhatsApp",
        })

        # Atualiza campo no animal se possível
        ani_docs = list(_coll(fazenda_id, "animais")
                        .where(filter=FieldFilter("nome", "==", animal)).stream())
        if ani_docs:
            doc_id = ani_docs[0].id
            upd = {}
            if evento == "Inseminação":
                upd = {"dt_insem": str(data)}
            elif evento == "Prenhez Confirmada":
                upd = {"prenhez": True}
            elif evento == "Prenhez Negativa":
                upd = {"prenhez": False, "dt_insem": None}
            elif evento == "Parto":
                upd = {"dt_parto": str(data), "prenhez": False, "status": "Lactação"}
            elif evento == "Secagem":
                upd = {"status": "Seca", "freq": 0}
            if upd:
                _coll(fazenda_id, "animais").document(doc_id).update(upd)

        if custo > 0:
            _fin("Reprodução", f"{evento} — {animal}", custo, animal=animal, data=str(data))

        return f"*Salvo!*\n{evento} registrado para {animal} em {data}."

    # ── PRODUCAO_MULTIPLA ─────────────────────
    elif tipo == "PRODUCAO_MULTIPLA":
        # itens pode vir dentro de dados["itens"] (quando montado pelo _processar)
        itens_prod = dados.get("itens") or []
        if not itens_prod:
            return "Nenhum item de produção encontrado."

        data_padrao = dados.get("data") or hoje   # fallback quando item não tem data
        _turno_map2 = {"manha": 1, "manhã": 1, "tarde": 2, "noite": 3}
        turno_padrao_raw = dados.get("turno") or 1
        try:
            turno_padrao = int(turno_padrao_raw)
        except (ValueError, TypeError):
            turno_padrao = _turno_map2.get(str(turno_padrao_raw).lower().strip(), 1)

        salvos = 0
        total  = 0.0
        animais_vistos: set = set()

        for item in itens_prod:
            # Litros: ignora entradas com "//" ou valor zero/inválido
            litros_raw = item.get("litros")
            if litros_raw is None or str(litros_raw).strip() in ("//", "—", "-", "", "null"):
                continue
            try:
                litros = float(str(litros_raw).replace(",", "."))
            except (ValueError, TypeError):
                continue
            if litros <= 0:
                continue

            # Data: cada item pode ter sua própria data (tabela dia-a-dia)
            data_item = item.get("data") or data_padrao
            try:
                # Normaliza para YYYY-MM-DD
                if "/" in str(data_item):
                    partes = str(data_item).split("/")
                    if len(partes) == 3:
                        d, m, a = partes
                        data_item = f"{a}-{m.zfill(2)}-{d.zfill(2)}"
            except Exception:
                data_item = data_padrao

            # Turno por item ou padrão
            turno_item_raw = item.get("turno") or turno_padrao
            try:
                turno_item = int(turno_item_raw)
            except (ValueError, TypeError):
                turno_item = _turno_map2.get(str(turno_item_raw).lower().strip(), turno_padrao)

            # Animal: um único animal pode estar no dado geral (tabela de 1 animal por mês)
            nome_raw = item.get("animal") or dados.get("animal") or "Rebanho"
            nome_ani, id_ani = _resolver_animal(fazenda_id, nome_raw)
            animais_vistos.add(nome_ani)

            _coll(fazenda_id, "producao").add({
                "data":        str(data_item),
                "leite":       litros,
                "turno":       turno_item,
                "id_animal":   id_ani,
                "nome_animal": nome_ani,
                "racao":       0,
            })
            salvos += 1
            total  += litros

        if salvos == 0:
            return "Nenhum registro válido encontrado na tabela."

        animais_txt = ", ".join(sorted(animais_vistos))
        return (
            f"✅ *{salvos} registros salvos!*\n"
            f"Animal(is): {animais_txt}\n"
            f"Total: *{total:.0f} L*"
        )

    # ── CORRIGIR_PRODUCAO ─────────────────────
    elif tipo == "CORRIGIR_PRODUCAO":
        animal_raw    = dados.get("animal") or "?"
        animal, id_a  = _resolver_animal(fazenda_id, animal_raw)
        data_p        = dados.get("data") or hoje
        litros_novo   = _parse_float(dados.get("litros_correto") or dados.get("litros"))
        turno_raw     = dados.get("turno") or 1
        try:
            turno = int(turno_raw)
        except (ValueError, TypeError):
            turno = {"manha": 1, "manhã": 1, "tarde": 2, "noite": 3}.get(str(turno_raw).lower(), 1)

        # Busca registros existentes para esse animal+data
        docs_prod = list(_coll(fazenda_id, "producao")
                         .where(filter=FieldFilter("data", "==", data_p)).stream())
        antigos = [d for d in docs_prod
                   if d.to_dict().get("nome_animal") == animal or d.to_dict().get("id_animal") == id_a]
        if not antigos:
            return f"Não encontrei registro de {animal} em {data_p} para corrigir."
        # Apaga o(s) antigo(s) e salva o correto
        litros_antigo = sum(d.to_dict().get("leite", 0) for d in antigos)
        for d in antigos:
            _coll(fazenda_id, "producao").document(d.id).delete()
        _coll(fazenda_id, "producao").add({
            "data": data_p, "leite": litros_novo, "turno": turno,
            "id_animal": id_a, "nome_animal": animal, "racao": 0,
        })
        return (f"*Corrigido!*\n{animal} em {data_p}: "
                f"{litros_antigo:.0f} L → *{litros_novo:.0f} L*")

    # ── APAGAR_PRODUCAO ────────────────────────
    elif tipo == "APAGAR_PRODUCAO":
        animal_raw   = dados.get("animal") or "?"
        animal, id_a = _resolver_animal(fazenda_id, animal_raw)
        data_p       = dados.get("data") or hoje
        docs_prod    = list(_coll(fazenda_id, "producao")
                            .where(filter=FieldFilter("data", "==", data_p)).stream())
        antigos = [d for d in docs_prod
                   if d.to_dict().get("nome_animal") == animal or d.to_dict().get("id_animal") == id_a]
        if not antigos:
            return f"Não encontrei registro de {animal} em {data_p}."
        total_apagado = sum(d.to_dict().get("leite", 0) for d in antigos)
        for d in antigos:
            _coll(fazenda_id, "producao").document(d.id).delete()
        return f"*Apagado!*\nProdução de {animal} em {data_p} ({total_apagado:.0f} L) removida."

    # ── CORRIGIR_LANCAMENTO ───────────────────
    elif tipo == "CORRIGIR_LANCAMENTO":
        desc_busca = (dados.get("descricao") or "").lower()
        data_l     = dados.get("data") or hoje
        val_novo   = _parse_float(dados.get("valor_novo"))
        # Busca financeiro nessa data
        docs_fin = list(_coll(fazenda_id, "financeiro")
                        .where(filter=FieldFilter("data", "==", data_l)).stream())
        candidatos = [d for d in docs_fin
                      if desc_busca and desc_busca in (d.to_dict().get("desc", "") or
                                                        d.to_dict().get("descricao", "")).lower()]
        if not candidatos:
            return (f"Não encontrei lançamento com '{dados.get('descricao')}' em {data_l}. "
                    f"Verifique a data ou a descrição.")
        if len(candidatos) > 1:
            lista = "\n".join(f"- {d.to_dict().get('desc','')} R${d.to_dict().get('valor',0):.2f}"
                              for d in candidatos[:5])
            return f"Encontrei {len(candidatos)} lançamentos similares:\n{lista}\nSeja mais específico."
        doc = candidatos[0]
        val_antigo = doc.to_dict().get("valor", 0)
        _coll(fazenda_id, "financeiro").document(doc.id).update({"valor": val_novo})
        return (f"*Corrigido!*\n{doc.to_dict().get('desc','')} em {data_l}: "
                f"R${val_antigo:.2f} → *R${val_novo:.2f}*")

    # ── APAGAR_LANCAMENTO ─────────────────────
    elif tipo == "APAGAR_LANCAMENTO":
        desc_busca = (dados.get("descricao") or "").lower()
        data_l     = dados.get("data") or hoje
        val_hint   = _parse_float(dados.get("valor"))
        docs_fin   = list(_coll(fazenda_id, "financeiro")
                          .where(filter=FieldFilter("data", "==", data_l)).stream())
        candidatos = [d for d in docs_fin
                      if desc_busca and desc_busca in (d.to_dict().get("desc", "") or
                                                        d.to_dict().get("descricao", "")).lower()]
        if val_hint > 0:
            candidatos = [d for d in candidatos
                          if abs(d.to_dict().get("valor", 0) - val_hint) < 1]
        if not candidatos:
            return f"Não encontrei lançamento com '{dados.get('descricao')}' em {data_l}."
        if len(candidatos) > 1:
            lista = "\n".join(f"- {d.to_dict().get('desc','')} R${d.to_dict().get('valor',0):.2f}"
                              for d in candidatos[:5])
            return f"Encontrei {len(candidatos)} lançamentos:\n{lista}\nQual deles apagar? Informe o valor exato."
        doc = candidatos[0]
        d_dict = doc.to_dict()
        _coll(fazenda_id, "financeiro").document(doc.id).delete()
        return (f"*Apagado!*\n{d_dict.get('desc','')} — R${d_dict.get('valor',0):.2f} "
                f"({data_l}) removido do financeiro.")

    # ── AGENDAR_SANITARIO ─────────────────────
    elif tipo == "AGENDAR_SANITARIO":
        tipo_san  = dados.get("tipo_sanitario") or "Protocolo"
        protocolo = dados.get("protocolo") or dados.get("produto") or "Procedimento"
        animal    = dados.get("animal") or "Rebanho"
        data_ag   = dados.get("data") or hoje
        obs       = dados.get("obs") or ""
        custo_est = _parse_float(dados.get("custo"))
        _coll(fazenda_id, "sanitario").add({
            "data": data_ag, "tipo": tipo_san, "prod": protocolo,
            "protocolo": protocolo, "modo": "Individual" if animal != "Rebanho" else "Rebanho Todo",
            "animal": animal, "custo": custo_est,
            "executado": False, "obs": obs or "Agendado via WhatsApp",
        })
        ani_txt = f" para {animal}" if animal != "Rebanho" else " para o rebanho"
        return f"*Agendado!*\n{tipo_san} — {protocolo}{ani_txt} em {data_ag}."

    # ── ALTERAR_CONFIG ────────────────────────
    elif tipo == "ALTERAR_CONFIG":
        chave     = dados.get("chave") or ""
        val_novo  = dados.get("valor_novo") or dados.get("valor")
        _CHAVES_VALIDAS = {"preco_leite", "custo_por_litro", "meta_producao", "nome_fazenda"}
        if chave not in _CHAVES_VALIDAS:
            return f"Configuração '{chave}' não reconhecida. Opções: preço do leite, custo por litro, meta de produção."
        try:
            val_num = float(str(val_novo).replace(",", ".").replace("R$", "").strip())
        except (ValueError, TypeError):
            val_num = val_novo
        _coll(fazenda_id, "config").document(chave).set({"chave": chave, "valor": val_num})
        _cache_del(f"mem:{fazenda_id}")
        nomes = {"preco_leite": "Preço do leite", "custo_por_litro": "Custo por litro",
                 "meta_producao": "Meta de produção", "nome_fazenda": "Nome da fazenda"}
        return f"*Configuração atualizada!*\n{nomes.get(chave, chave)}: {val_num}"

    # ── ATUALIZAR_ANIMAL ──────────────────────
    elif tipo == "ATUALIZAR_ANIMAL":
        animal_raw   = dados.get("animal") or dados.get("nome") or "?"
        animal, id_a = _resolver_animal(fazenda_id, animal_raw)
        # Campos atualizáveis via chat
        _CAMPOS_ANI = {"raca", "obs", "lote", "nasc", "mae"}
        upd = {k: v for k, v in dados.items() if k in _CAMPOS_ANI and v is not None}
        if not upd:
            return "Nenhum campo para atualizar informado."
        ani_docs = list(_coll(fazenda_id, "animais")
                        .where(filter=FieldFilter("nome", "==", animal)).stream())
        if not ani_docs:
            return f"Animal '{animal}' não encontrado no rebanho."
        _coll(fazenda_id, "animais").document(ani_docs[0].id).update(upd)
        campos_txt = ", ".join(f"{k}={v}" for k, v in upd.items())
        return f"*Atualizado!*\n{animal}: {campos_txt}"

    # ── EXECUTAR_PROTOCOLO ────────────────────
    elif tipo == "EXECUTAR_PROTOCOLO":
        protocolo_busca = (dados.get("protocolo") or dados.get("produto") or "").lower()
        animal_busca    = (dados.get("animal") or "").lower()
        data_exec       = dados.get("data") or hoje
        custo_real      = _parse_float(dados.get("custo"))

        # Busca protocolo pendente (executado=False)
        docs_san = list(_coll(fazenda_id, "sanitario").stream())
        pendentes = [d for d in docs_san if not d.to_dict().get("executado", False)]

        # Filtra por protocolo e/ou animal
        candidatos = []
        for d in pendentes:
            dd = d.to_dict()
            nome_prot = (dd.get("protocolo") or dd.get("prod") or "").lower()
            nome_ani  = (dd.get("animal") or "").lower()
            match_prot = (not protocolo_busca) or (protocolo_busca in nome_prot)
            match_ani  = (not animal_busca) or (animal_busca in nome_ani) or ("rebanho" in animal_busca)
            if match_prot and match_ani:
                candidatos.append(d)

        if not candidatos:
            return (f"Não encontrei protocolo pendente com '{dados.get('protocolo','')}' "
                    f"para '{dados.get('animal','o rebanho')}'. Já foi executado antes?")
        if len(candidatos) > 1:
            lista = "\n".join(
                f"- {d.to_dict().get('prod','')} — {d.to_dict().get('animal','')} "
                f"({d.to_dict().get('data','')})"
                for d in candidatos[:5]
            )
            return f"Encontrei {len(candidatos)} protocolos pendentes:\n{lista}\nQual você executou?"

        doc    = candidatos[0]
        dd     = doc.to_dict()
        upd_ex = {"executado": True, "executado_em": data_exec}
        if custo_real > 0:
            upd_ex["custo"] = custo_real
        _coll(fazenda_id, "sanitario").document(doc.id).update(upd_ex)

        # Lança custo real no financeiro se informado
        custo_lancado = custo_real if custo_real > 0 else _parse_float(dd.get("custo"))
        if custo_lancado > 0:
            animal_fin = dd.get("animal") or "Rebanho"
            _fin("Medicamento / Sanitário",
                 f"{dd.get('tipo','')} — {dd.get('prod','')} (executado)",
                 custo_lancado, animal=animal_fin, data=data_exec)

        return (f"*Executado!*\n{dd.get('tipo','')} — {dd.get('prod','')} "
                f"({dd.get('animal','Rebanho')}) marcado como realizado em {data_exec}."
                + (f"\nR$ {custo_lancado:.2f} lançado no financeiro." if custo_lancado > 0 else ""))

    # ── APAGAR_ITEM_ESTOQUE ───────────────────
    elif tipo == "APAGAR_ITEM_ESTOQUE":
        prod      = dados.get("produto") or ""
        existente = _buscar_no_estoque(fazenda_id, prod)
        if not existente:
            return f"Produto '{prod}' não encontrado no estoque."
        _coll(fazenda_id, "estoque").document(existente["doc_id"]).delete()
        _cache_del(f"est:{fazenda_id}")
        qtd_txt = f"{existente.get('qtd', 0):.1f} {existente.get('un', 'un')}"
        return f"*Removido!*\n{existente.get('item', prod)} ({qtd_txt}) apagado do armazém."

    # ── AJUSTAR_ESTOQUE ───────────────────────
    elif tipo == "AJUSTAR_ESTOQUE":
        prod      = dados.get("produto") or ""
        qtd_nova  = _parse_float(dados.get("qtd"))
        operacao  = (dados.get("operacao") or "definir").lower()
        un        = dados.get("unidade") or "un"
        existente = _buscar_no_estoque(fazenda_id, prod)
        if existente:
            did     = existente["doc_id"]
            qtd_ant = existente.get("qtd", 0)
            if operacao in ("adicionar", "somar", "add"):
                qtd_final = qtd_ant + qtd_nova
            elif operacao in ("remover", "subtrair", "tirar"):
                qtd_final = max(qtd_ant - qtd_nova, 0)
            else:
                qtd_final = qtd_nova  # definir / setar
            _coll(fazenda_id, "estoque").document(did).update(
                {"qtd": qtd_final, "un": un or existente.get("un", "un")}
            )
            _cache_del(f"est:{fazenda_id}")
            return (f"*Estoque ajustado!*\n{prod}: {qtd_ant:.1f} → *{qtd_final:.1f} {un}*")
        else:
            # Item novo no estoque
            _coll(fazenda_id, "estoque").add(
                {"item": prod, "qtd": qtd_nova, "un": un, "custo_medio": 0}
            )
            _cache_del(f"est:{fazenda_id}")
            return f"*Adicionado ao estoque!*\n{prod}: {qtd_nova:.1f} {un}"

    return "Registro salvo!"


# ─────────────────────────────────────────────
# DOWNLOAD DE MÍDIA DO TWILIO
# ─────────────────────────────────────────────
async def _baixar_midia(url: str, sid: str, token: str) -> bytes:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, auth=(sid, token))
        return r.content


# ─────────────────────────────────────────────
# TRANSCRIÇÃO DE ÁUDIO (Groq Whisper — grátis)
# ─────────────────────────────────────────────
async def _transcrever(media_url: str, twilio_sid: str, twilio_token: str,
                       content_type: str = "audio/ogg") -> str:
    """Transcreve áudio usando Groq (grátis) ou OpenAI como fallback."""
    try:
        audio_bytes = await _baixar_midia(media_url, twilio_sid, twilio_token)
        ext = "ogg"
        if "mp4" in content_type or "mpeg" in content_type:
            ext = "mp3"
        elif "wav" in content_type:
            ext = "wav"

        groq_key = os.environ.get("GROQ_API_KEY", "")
        if groq_key:
            import httpx as _hx
            async with _hx.AsyncClient(timeout=30) as c:
                resp = await c.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {groq_key}"},
                    files={"file": (f"audio.{ext}", audio_bytes, content_type)},
                    data={"model": "whisper-large-v3-turbo", "language": "pt"},
                )
                txt = resp.json().get("text", "")
                if txt:
                    log.info(f"Groq transcricao: {txt[:80]}")
                    return txt

        # Fallback OpenAI
        openai_key = os.environ.get("OPENAI_API_KEY", "")
        if openai_key:
            import openai
            oai = openai.OpenAI(api_key=openai_key)
            tx  = oai.audio.transcriptions.create(
                model="whisper-1",
                file=(f"audio.{ext}", audio_bytes, content_type),
                language="pt",
            )
            log.info(f"OpenAI transcricao: {tx.text[:80]}")
            return tx.text

        log.warning("Nenhuma chave de transcricao configurada (GROQ_API_KEY ou OPENAI_API_KEY)")
        return ""
    except Exception as e:
        log.error(f"Transcricao error: {e}")
        return ""


# ─────────────────────────────────────────────
# LEITURA DE IMAGEM / NOTA FISCAL (Claude Vision)
# ─────────────────────────────────────────────
async def _ler_imagem(media_url: str, twilio_sid: str, twilio_token: str,
                      content_type: str = "image/jpeg") -> str:
    """Usa Claude Vision para extrair dados de foto de nota fiscal ou produto."""
    try:
        import base64
        from anthropic import Anthropic

        img_bytes = await _baixar_midia(media_url, twilio_sid, twilio_token)
        b64 = base64.standard_b64encode(img_bytes).decode()

        client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": content_type, "data": b64},
                    },
                    {
                        "type": "text",
                        "text": (
                            "Analise esta imagem de uma fazenda leiteira. Identifique qual dos tipos abaixo:\n\n"
                            "A) NOTA FISCAL / RECIBO / CUPOM: tem produtos, quantidades, valores, nome da loja.\n"
                            "B) TABELA MENSAL DE PRODUÇÃO: coluna de datas e coluna de litros, dia a dia. "
                            "O título/cabeçalho pode ser o nome do produtor ou da fazenda — NÃO é necessariamente o nome de uma vaca. "
                            "Se a tabela não identificar explicitamente um animal, use Animal: Rebanho.\n"
                            "C) LISTA DE VACAS DO DIA: lista com vários animais identificados pelo nome e seus litros "
                            "(ex: Rainha 18L, Moreninha 12L). Cada linha tem nome da vaca + litros.\n"
                            "D) OUTRO (descreva brevemente).\n\n"
                            "Se for A: responda exatamente assim:\n"
                            "[NOTA FISCAL]\nFornecedor: ...\nItens:\n- Produto: X, Qtd: N, Unidade: U, Valor: R$V\n\n"
                            "Se for B: responda exatamente assim:\n"
                            "[TABELA MENSAL]\nAnimal: (nome da vaca se identificado, senão 'Rebanho')\nMes: MM/AAAA\nRegistros:\n"
                            "- Data: DD/MM/AAAA, Litros: N\n"
                            "(use '//' para dias sem dado — ex: Litros: //)\n\n"
                            "Se for C: responda exatamente assim:\n"
                            "[PRODUCAO DO DIA]\nData: DD/MM/AAAA (se visível, senão 'hoje')\nAnimais:\n"
                            "- Animal: NomeVaca, Litros: N\n\n"
                            "Se for D: descreva o que vê em 1 linha.\n\n"
                            "Extraia TODOS os dados visíveis. Inclua todas as linhas da tabela. "
                            "Responda apenas com os dados extraídos, sem explicação extra."
                        ),
                    },
                ],
            }],
        )
        texto = resp.content[0].text.strip()
        log.info(f"Vision extraiu: {texto[:200]}")
        # Detecta tipo para prefixar adequadamente ao passar para o bot
        if "[TABELA MENSAL]" in texto:
            return f"[Foto tabela mensal de producao] {texto}"
        if "[PRODUCAO DO DIA]" in texto:
            return f"[Foto producao do dia] {texto}"
        if "[NOTA FISCAL]" in texto:
            return f"[Nota fiscal] {texto}"
        return f"[Foto] {texto}"
    except Exception as e:
        log.error(f"Vision error: {e}")
        return ""


# ─────────────────────────────────────────────
# ENVIO ATIVO — cascata: Evolution API (grátis) → Z-API → Twilio (pago)
# ─────────────────────────────────────────────
def _enviar_evolution(para: str, mensagem: str) -> bool:
    """Evolution API — self-hosted, completamente grátis.
    Configura: EVOLUTION_URL=http://seu-servidor:8080
               EVOLUTION_KEY=sua-api-key
               EVOLUTION_INSTANCE=nome-da-instancia
    Suporta Evolution v1 e v2 (tenta ambos os formatos).
    """
    url      = os.environ.get("EVOLUTION_URL", "")
    api_key  = os.environ.get("EVOLUTION_KEY", "")
    instance = os.environ.get("EVOLUTION_INSTANCE", "milkshow")
    if not url or not api_key:
        return False
    try:
        import httpx as _hx
        base = url.rstrip("/")
        hdrs = {"apikey": api_key, "Content-Type": "application/json"}

        # Monta lista de candidatos: JID original (@lid ou @s.whatsapp.net) + número limpo
        jid_original = _JID_CACHE.get(para, "")
        num = re.sub(r'\D', '', para)
        if not num.startswith('55'):
            num = '55' + num

        candidatos = []
        # Prioridade 1: JID original completo (inclui @lid para iPhones)
        if jid_original:
            candidatos.append(jid_original)
        # Prioridade 2: número limpo
        candidatos.append(num)
        # Prioridade 3: variante sem nono dígito (ex: 5577981258479)
        if len(num) == 13:
            candidatos.append(num[:4] + num[5:])

        endpoint = f"{base}/message/sendText/{instance}"
        for candidato in candidatos:
            # Tenta formato Evolution v2: {"number": ..., "text": ...}
            for payload in [
                {"number": candidato, "text": mensagem, "delay": 300},
                {"number": candidato, "options": {"delay": 300}, "textMessage": {"text": mensagem}},
            ]:
                r = _hx.post(endpoint, headers=hdrs, json=payload, timeout=15)
                if r.status_code in (200, 201):
                    log.info(f"Evolution → {para}: OK (via {candidato})")
                    return True
                if r.status_code not in (400, 404, 422):
                    # Erro inesperado — não tenta mais variantes de payload
                    break
        log.info(f"Evolution → {para}: FALHOU (último status {r.status_code})")
        return False
    except Exception as e:
        log.warning(f"Evolution falhou: {e}")
        return False


def _enviar_zapi(para: str, mensagem: str) -> bool:
    """Z-API — plano flat ~R$97/mês, sem custo por mensagem.
    Configura: ZAPI_INSTANCE=id-da-instancia
               ZAPI_TOKEN=seu-token
               ZAPI_CLIENT_TOKEN=seu-client-token
    """
    instance     = os.environ.get("ZAPI_INSTANCE", "")
    token        = os.environ.get("ZAPI_TOKEN", "")
    client_token = os.environ.get("ZAPI_CLIENT_TOKEN", "")
    if not instance or not token:
        return False
    try:
        import httpx as _hx
        num = re.sub(r'\D', '', para)
        if not num.startswith('55'):
            num = '55' + num
        r = _hx.post(
            f"https://api.z-api.io/instances/{instance}/token/{token}/send-text",
            headers={"Client-Token": client_token, "Content-Type": "application/json"},
            json={"phone": num, "message": mensagem},
            timeout=15,
        )
        ok = r.status_code in (200, 201)
        log.info(f"Z-API → {para}: {'OK' if ok else f'FALHOU {r.status_code}'}")
        return ok
    except Exception as e:
        log.warning(f"Z-API falhou: {e}")
        return False


def _enviar_twilio(para: str, mensagem: str) -> bool:
    """Twilio — último recurso, cobrado por mensagem."""
    sid   = os.environ.get("TWILIO_ACCOUNT_SID", "")
    token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    de    = os.environ.get("TWILIO_FROM", "whatsapp:+14155238886")
    if not sid or not token:
        return False
    try:
        import urllib.request, urllib.parse, base64 as _b64
        para_fmt = f"whatsapp:{para}" if not para.startswith("whatsapp:") else para
        payload  = urllib.parse.urlencode({"From": de, "To": para_fmt, "Body": mensagem}).encode()
        req = urllib.request.Request(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
            data=payload, method="POST",
        )
        cred = _b64.b64encode(f"{sid}:{token}".encode()).decode()
        req.add_header("Authorization", f"Basic {cred}")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urllib.request.urlopen(req, timeout=10) as r:
            ok = r.status in (200, 201)
            log.info(f"Twilio → {para}: {'OK' if ok else f'FALHOU {r.status}'}")
            return ok
    except Exception as e:
        log.warning(f"Twilio falhou: {e}")
        return False


def _enviar_whatsapp(para: str, mensagem: str) -> bool:
    """Envia mensagem em cascata: Evolution (grátis) → Z-API (flat) → Twilio (por mensagem)."""
    log.info(f"[{para}] enviando: '{mensagem[:60].replace(chr(10),' ')}'")
    for fn in (_enviar_evolution, _enviar_zapi, _enviar_twilio):
        if fn(para, mensagem):
            return True
    log.error(f"Todos os provedores WhatsApp falharam para {para}")
    return False


def _enviar_typing(para: str, duracao_ms: int = 4000):
    """Mostra indicador 'digitando...' — feedback imediato ao produtor."""
    url  = os.environ.get("EVOLUTION_URL", "").rstrip("/")
    key  = os.environ.get("EVOLUTION_KEY", "")
    inst = os.environ.get("EVOLUTION_INSTANCE", "milkshow")
    if not url or not key:
        return
    jid = _JID_CACHE.get(para, para)
    try:
        import httpx as _hx
        _hx.post(
            f"{url}/chat/sendPresence/{inst}",
            headers={"apikey": key, "Content-Type": "application/json"},
            json={"number": jid, "options": {"presence": "composing", "delay": duracao_ms}},
            timeout=4,
        )
    except Exception:
        pass


def _enviar_botoes(para: str, texto: str, opcoes: list[tuple[str, str]]):
    """Envia mensagem com botões interativos via Evolution API.
    opcoes = [("id", "texto"), ...]  — máx 3 botões.
    Cai em texto simples se Evolution não suportar.
    """
    url  = os.environ.get("EVOLUTION_URL", "").rstrip("/")
    key  = os.environ.get("EVOLUTION_KEY", "")
    inst = os.environ.get("EVOLUTION_INSTANCE", "milkshow")
    jid  = _JID_CACHE.get(para, para)
    if not url or not key:
        _enviar_whatsapp(para, texto)
        return
    try:
        import httpx as _hx
        botoes = [{"buttonId": bid, "buttonText": {"displayText": btxt}, "type": 0}
                  for bid, btxt in opcoes[:3]]
        r = _hx.post(
            f"{url}/message/sendButtons/{inst}",
            headers={"apikey": key, "Content-Type": "application/json"},
            json={"number": jid, "title": "MilkShow", "description": texto,
                  "footer": "", "buttons": botoes, "delay": 300},
            timeout=10,
        )
        if r.status_code not in (200, 201):
            raise ValueError(f"status {r.status_code}")
        log.info(f"Botões → {para}: OK")
    except Exception as e:
        log.warning(f"Botões falhou ({e}), enviando texto simples")
        _enviar_whatsapp(para, texto)


def _todos_telefones() -> list:
    """Retorna lista de {tel, fazenda_id} de todos os números ativos."""
    try:
        docs = _db().collection("registros_tel").stream()
        return [
            {"tel": d.id, "fazenda_id": d.to_dict().get("fazenda_id", "default")}
            for d in docs
            if d.to_dict().get("ativo", True)
        ]
    except Exception:
        return []


# ─────────────────────────────────────────────
# RELATÓRIO SEMANAL
# ─────────────────────────────────────────────
def _gerar_relatorio_semanal(fazenda_id: str) -> str:
    """Gera texto do relatório semanal da fazenda."""
    hoje     = datetime.date.today()
    ini_sem  = hoje - datetime.timedelta(days=7)
    ini_mes  = hoje.replace(day=1)

    linhas = [f"*Relatório Semanal MilkShow*\n{ini_sem.strftime('%d/%m')} a {hoje.strftime('%d/%m/%Y')}\n"]

    try:
        # Produção
        prod = list(_coll(fazenda_id, "producao")
                    .where(filter=FieldFilter("data", ">=", ini_sem.isoformat())).stream())
        total_l = sum(d.to_dict().get("leite", 0) for d in prod)
        por_ani = {}
        for d in prod:
            dd = d.to_dict()
            n = dd.get("nome_animal", "?")
            por_ani[n] = por_ani.get(n, 0) + dd.get("leite", 0)
        media_dia = total_l / 7
        top = sorted(por_ani.items(), key=lambda x: x[1], reverse=True)[:3]
        linhas.append(f"*Produção:* {total_l:.0f} L ({media_dia:.0f} L/dia)")
        if top:
            linhas.append("Top vacas: " + ", ".join(f"{n} {v:.0f}L" for n, v in top))
    except Exception:
        pass

    try:
        # Financeiro do mês
        fin = list(_coll(fazenda_id, "financeiro")
                   .where(filter=FieldFilter("data", ">=", ini_mes.isoformat())).stream())
        rec = sum(d.to_dict().get("valor", 0) for d in fin
                  if "Venda" in d.to_dict().get("cat", ""))
        des = sum(d.to_dict().get("valor", 0) for d in fin
                  if "Venda" not in d.to_dict().get("cat", ""))
        sinal = "+" if rec - des >= 0 else ""
        linhas.append(f"\n*Financeiro (mês):* Receitas R${rec:.0f} / Despesas R${des:.0f} / Saldo {sinal}R${rec-des:.0f}")
    except Exception:
        pass

    try:
        # Alertas / tarefas pendentes
        ctx = _ctx_dados_fazenda(fazenda_id)
        if "AGENDA:" in ctx:
            agenda_part = ctx.split("AGENDA:")[1].split("\nRENTABILIDADE")[0].strip()
            pendentes = [l.strip().lstrip("- ") for l in agenda_part.splitlines()
                         if l.strip().startswith("-")]
            if pendentes:
                linhas.append(f"\n*Pendências ({len(pendentes)}):*")
                for p in pendentes[:6]:
                    linhas.append(f"• {p}")
    except Exception:
        pass

    try:
        # Estoque crítico (menos de 20% da qtd original estimada)
        est = [d.to_dict() for d in _coll(fazenda_id, "estoque").stream()]
        criticos = [e for e in est if float(e.get("qtd", 1)) <= 2 and e.get("qtd") is not None]
        if criticos:
            linhas.append(f"\n*Estoque baixo:*")
            for e in criticos[:4]:
                linhas.append(f"• {e.get('item','?')}: {e.get('qtd',0):.1f} {e.get('un','')}")
    except Exception:
        pass

    linhas.append("\nBoa semana! 🌾")
    return "\n".join(linhas)


# ─────────────────────────────────────────────
# ALERTAS PROATIVOS
# ─────────────────────────────────────────────
def _gerar_alertas_proativos(fazenda_id: str) -> list:
    """Retorna lista de alertas críticos que precisam ser enviados hoje."""
    hoje     = datetime.date.today()
    hoje_iso = hoje.isoformat()
    alertas  = []

    GESTACAO   = 283
    DIAS_SECAR = 60
    DIAS_DIAGN = 30
    DIAS_PVE   = 45

    try:
        animais = [d.to_dict() for d in _coll(fazenda_id, "animais").stream()]
        for a in animais:
            nome   = a.get("nome", "?")
            status = a.get("status", "")

            def _pd(s):
                try:
                    return datetime.datetime.strptime(str(s)[:10], "%Y-%m-%d").date() if s else None
                except Exception:
                    return None

            d_insem = _pd(a.get("dt_insem"))
            d_parto = _pd(a.get("dt_parto"))

            if status == "Lactação":
                if d_insem and not a.get("prenhez"):
                    dias = (hoje - d_insem).days
                    if dias == DIAS_DIAGN:
                        alertas.append(f"Diagnóstico de prenhez: {nome} foi inseminada há {dias} dias — verifique hoje!")

                if not a.get("prenhez") and not d_insem and d_parto:
                    dias_v = (hoje - d_parto).days
                    if dias_v == DIAS_PVE + 1:
                        alertas.append(f"Inseminar: {nome} está vazia há {dias_v} dias — está atrasada!")

                if a.get("prenhez") and d_insem:
                    prev  = d_insem + datetime.timedelta(days=GESTACAO)
                    d_sec = prev - datetime.timedelta(days=DIAS_SECAR)
                    dias_sec = (d_sec - hoje).days
                    if dias_sec == 0:
                        alertas.append(f"SECAR HOJE: {nome} — parto previsto em {DIAS_SECAR} dias ({prev.isoformat()})")
                    if (prev - hoje).days in (7, 3, 1):
                        alertas.append(f"Parto próximo: {nome} previsto em {(prev-hoje).days} dia(s) ({prev.isoformat()}) — prepare o local!")
    except Exception:
        pass

    try:
        # Estoque zerado
        est = [d.to_dict() for d in _coll(fazenda_id, "estoque").stream()]
        for e in est:
            if float(e.get("qtd", 1)) <= 0:
                alertas.append(f"Estoque ZERADO: {e.get('item','?')} — reponha o quanto antes.")
    except Exception:
        pass

    try:
        # Protocolo sanitário — verificar se há execuções pendentes hoje
        protos = list(_coll(fazenda_id, "protocolos_sanitarios")
                      .where(filter=FieldFilter("ativo", "==", True)).stream())
        for p in protos:
            pd_  = p.to_dict()
            prox = _pd(pd_.get("proxima_data"))
            if prox and prox <= hoje:
                alertas.append(f"Protocolo sanitário: {pd_.get('nome','?')} está vencido — aplique hoje!")
    except Exception:
        pass

    return alertas


# ─────────────────────────────────────────────
# ONBOARDING VIA WHATSAPP
# ─────────────────────────────────────────────
_ONBOARDING: dict = {}   # tel → {"step": str, "nome_pessoa": str, "nome_fazenda": str}

def _processar_onboarding(tel: str, texto: str):
    """Fluxo de cadastro: número desconhecido → cria fazenda pelo WhatsApp."""
    state = _ONBOARDING.get(tel, {})
    step  = state.get("step", "inicio")
    texto = texto.strip()

    if step == "inicio" or not state:
        _ONBOARDING[tel] = {"step": "aguarda_nome_pessoa"}
        _enviar_whatsapp(tel,
            "👋 Olá! Bem-vindo ao *MilkShow*!\n\n"
            "Seu número não está cadastrado ainda.\n"
            "Vamos criar seu cadastro rapidinho!\n\n"
            "Qual é o seu *nome*?"
        )
        return

    if step == "aguarda_nome_pessoa":
        if len(texto) < 2:
            _enviar_whatsapp(tel, "Por favor, informe seu nome:")
            return
        _ONBOARDING[tel] = {"step": "aguarda_nome_fazenda", "nome_pessoa": texto}
        _enviar_whatsapp(tel,
            f"Prazer, *{texto}*! 😊\n\n"
            "Qual é o *nome da sua fazenda*?"
        )
        return

    if step == "aguarda_nome_fazenda":
        if len(texto) < 2:
            _enviar_whatsapp(tel, "Por favor, informe o nome da fazenda:")
            return
        _ONBOARDING[tel] = {**state, "step": "aguarda_email", "nome_fazenda": texto}
        _enviar_whatsapp(tel,
            f"Ótimo! *{texto}* 🐄\n\n"
            "Agora informe seu *e-mail* para acessar o painel web:"
        )
        return

    if step == "aguarda_email":
        email = texto.lower()
        if "@" not in email or "." not in email:
            _enviar_whatsapp(tel, "E-mail inválido. Tente novamente:")
            return
        nome_fazenda = state.get("nome_fazenda", "Minha Fazenda")
        nome_pessoa  = state.get("nome_pessoa", "")
        try:
            _criar_fazenda_whatsapp(tel, email, nome_fazenda, nome_pessoa)
            del _ONBOARDING[tel]
            _enviar_whatsapp(tel,
                f"✅ *Cadastro criado com sucesso!*\n\n"
                f"👤 {nome_pessoa}\n"
                f"🏡 {nome_fazenda}\n"
                f"📧 {email}\n\n"
                f"Você já pode usar o bot! Exemplos:\n"
                f"• \"450 litros\" — produção do dia\n"
                f"• \"comprei ração 300 reais\" — financeiro\n"
                f"• \"ajuda\" — ver todos os comandos\n\n"
                f"Acesse o painel em: http://178.104.252.193"
            )
        except Exception as e:
            log.error(f"Onboarding erro: {e}")
            _enviar_whatsapp(tel, f"Erro ao criar cadastro: {str(e)[:80]}\nTente novamente ou acesse o app.")
        return

    # Step desconhecido — reinicia
    _ONBOARDING.pop(tel, None)
    _enviar_whatsapp(tel, "Vamos recomeçar. Qual é o seu *nome*?")
    _ONBOARDING[tel] = {"step": "aguarda_nome_pessoa"}


def _criar_fazenda_whatsapp(tel: str, email: str, nome_fazenda: str, nome_pessoa: str = ""):
    """Cria documentos Firestore para nova fazenda cadastrada pelo WhatsApp."""
    import uuid
    fazenda_id = str(uuid.uuid4())[:12].replace("-", "")
    db = _db()
    db.collection("fazendas").document(fazenda_id).set({
        "nome":        nome_fazenda,
        "owner_email": email,
        "owner_tel":   tel,
        "owner_nome":  nome_pessoa,
        "created_at":  datetime.datetime.now().isoformat(),
        "plano":       "trial",
    })
    db.collection("users").document(fazenda_id).set({
        "email":      email,
        "fazenda_id": fazenda_id,
        "nome":       nome_pessoa or nome_fazenda,
        "created_at": datetime.datetime.now().isoformat(),
    })
    db.collection("registros_tel").document(tel).set({
        "fazenda_id": fazenda_id,
        "nome":       nome_pessoa or "Proprietário",
        "permissoes": ["admin"],
        "ativo":      True,
        "email":      email,
        "created_at": datetime.datetime.now().isoformat(),
    })
    # Invalida cache para que próxima mensagem já reconheça o número
    _cache_del(f"usr:{tel}")


# ─────────────────────────────────────────────
# RELATÓRIO MATINAL (briefing diário às 6h)
# ─────────────────────────────────────────────
def _relatorio_manha(fazenda_id: str) -> str:
    """Resumo da manhã: produção de ontem, agenda de hoje, saldo do mês."""
    hoje      = datetime.date.today()
    ontem     = hoje - datetime.timedelta(days=1)
    ini_mes   = hoje.replace(day=1).isoformat()

    linhas = [f"🌅 *Bom dia! Resumo de {hoje.strftime('%d/%m/%Y')}*\n"]

    try:
        prod_ontem = _cached_producao(fazenda_id, ontem.isoformat(), ontem.isoformat())
        total_ontem = sum(p.get("leite", 0) for p in prod_ontem)
        if total_ontem > 0:
            linhas.append(f"🥛 Produção de ontem: *{total_ontem:.0f} L*")
        else:
            linhas.append("🥛 Nenhuma produção registrada ontem.")
    except Exception:
        pass

    try:
        fin_mes = _cached_financeiro(fazenda_id, ini_mes)
        rec  = sum(f.get("valor", 0) for f in fin_mes if "Venda" in f.get("cat", ""))
        desp = sum(f.get("valor", 0) for f in fin_mes if "Venda" not in f.get("cat", ""))
        saldo = rec - desp
        emoji = "📈" if saldo >= 0 else "📉"
        linhas.append(f"{emoji} Saldo do mês: *R$ {saldo:,.0f}*")
    except Exception:
        pass

    try:
        animais = _cached_animais(fazenda_id)
        tarefas = []
        DIAS_SECAR = 60; DIAS_DIAGN = 30; DIAS_PVE = 45; GESTACAO = 283

        def _pd(s):
            try: return datetime.datetime.strptime(str(s)[:10], "%Y-%m-%d").date() if s else None
            except: return None

        for a in animais:
            nome, status = a.get("nome","?"), a.get("status","")
            d_insem = _pd(a.get("dt_insem"))
            d_parto = _pd(a.get("dt_parto"))
            if status == "Lactação":
                if d_insem and not a.get("prenhez"):
                    if (hoje - d_insem).days == DIAS_DIAGN:
                        tarefas.append(f"🔬 Diagnóstico prenhez: *{nome}*")
                if not d_insem and d_parto and (hoje - d_parto).days > DIAS_PVE:
                    tarefas.append(f"💉 Inseminar (atrasada): *{nome}*")
                if a.get("prenhez") and d_insem:
                    prev  = d_insem + datetime.timedelta(days=GESTACAO)
                    secar = prev - datetime.timedelta(days=DIAS_SECAR)
                    if secar == hoje:
                        tarefas.append(f"🛑 Secar hoje: *{nome}*")
                    if 1 <= (prev - hoje).days <= 7:
                        tarefas.append(f"🐄 Parto em {(prev-hoje).days}d: *{nome}*")

        if tarefas:
            linhas.append("\n📋 *Agenda de hoje:*")
            linhas.extend(tarefas[:5])
        else:
            linhas.append("📋 Nenhuma tarefa urgente hoje.")
    except Exception:
        pass

    linhas.append("\nBom trabalho! 💪")
    return "\n".join(linhas)


# ─────────────────────────────────────────────
# BACKUP SEMANAL (Firestore → JSON local)
# ─────────────────────────────────────────────
def _backup_fazenda(fazenda_id: str) -> bool:
    """Exporta dados principais da fazenda para JSON local."""
    try:
        import json as _json
        backup_dir = os.path.join(os.path.dirname(__file__), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        data     = {}
        colecoes = ["animais", "producao", "financeiro", "estoque", "sanitario", "config"]
        for col in colecoes:
            docs = [d.to_dict() for d in _coll(fazenda_id, col).stream()]
            data[col] = docs
        ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        path = os.path.join(backup_dir, f"backup_{fazenda_id[:8]}_{ts}.json")
        with open(path, "w", encoding="utf-8") as f:
            _json.dump(data, f, ensure_ascii=False, default=str, indent=2)
        # Remove backups com mais de 4 semanas
        for arq in os.listdir(backup_dir):
            full = os.path.join(backup_dir, arq)
            if os.path.isfile(full):
                age = (datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(full))).days
                if age > 28:
                    os.remove(full)
        log.info(f"Backup {fazenda_id[:8]}: {path}")
        return True
    except Exception as e:
        log.error(f"Backup erro {fazenda_id}: {e}")
        return False


# ─────────────────────────────────────────────
# TWIML HELPER
# ─────────────────────────────────────────────
def _twiml(msg: str) -> Response:
    # Escapa caracteres especiais XML
    msg = msg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<Response><Message>{msg}</Message></Response>'
    )
    return Response(content=xml.encode("utf-8"), media_type="application/xml; charset=utf-8")


# ─────────────────────────────────────────────
# AGENDADOR INTERNO (alertas diários + relatório semanal)
# ─────────────────────────────────────────────
import asyncio as _asyncio

async def _loop_agendador():
    """Roda em background:
    - 6h todo dia: relatório matinal + alertas críticos
    - 7h toda segunda: relatório semanal
    - Domingo às 2h: backup de todas as fazendas
    """
    while True:
        try:
            agora = datetime.datetime.now()

            # Calcula próximo disparo (6h ou 2h domingo, o que vier primeiro)
            prox_6h = agora.replace(hour=6, minute=0, second=0, microsecond=0)
            if agora >= prox_6h:
                prox_6h += datetime.timedelta(days=1)

            prox_backup = agora.replace(hour=2, minute=0, second=0, microsecond=0)
            while prox_backup.weekday() != 6:  # domingo
                prox_backup += datetime.timedelta(days=1)
            if agora >= prox_backup:
                prox_backup += datetime.timedelta(days=7)

            prox   = min(prox_6h, prox_backup)
            espera = (prox - agora).total_seconds()
            await _asyncio.sleep(espera)

            agora    = datetime.datetime.now()
            hoje     = datetime.date.today()
            segunda  = hoje.weekday() == 0
            domingo  = hoje.weekday() == 6
            eh_6h    = agora.hour == 6
            registros = _todos_telefones()

            # ── Backup semanal (domingo às 2h) ────
            if domingo and agora.hour == 2:
                fazendas_vistas = set()
                for reg in registros:
                    fid = reg["fazenda_id"]
                    if fid not in fazendas_vistas:
                        fazendas_vistas.add(fid)
                        await _asyncio.to_thread(_backup_fazenda, fid)
                continue  # só backup neste ciclo

            for reg in registros:
                tel        = reg["tel"]
                fazenda_id = reg["fazenda_id"]
                try:
                    # Relatório matinal diário às 6h
                    if eh_6h:
                        manha = await _asyncio.to_thread(_relatorio_manha, fazenda_id)
                        _enviar_whatsapp(tel, manha)

                    # Alertas proativos críticos
                    alertas = _gerar_alertas_proativos(fazenda_id)
                    if alertas:
                        msg = "*⚠️ Alertas MilkShow:*\n" + "\n".join(f"• {a}" for a in alertas)
                        _enviar_whatsapp(tel, msg)

                    # Relatório semanal toda segunda-feira
                    if segunda and eh_6h:
                        rel = _gerar_relatorio_semanal(fazenda_id)
                        _enviar_whatsapp(tel, rel)

                except Exception as e:
                    log.error(f"Agendador erro para {tel}: {e}")

        except Exception as e:
            log.error(f"Agendador loop error: {e}")
            await _asyncio.sleep(3600)


@app.on_event("startup")
async def _iniciar_agendador():
    _asyncio.create_task(_loop_agendador())


# ─────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────
@app.get("/")
def raiz():
    return {"status": "MilkShow Bot online", "version": "2.1"}


class BotTestRequest(BaseModel):
    tel: str = "5511999990000"
    mensagem: str
    fazenda_id: str = "default"
    reset: bool = False  # limpa conversa antes de enviar


@app.post("/bot/testar")
def bot_testar(body: BotTestRequest, authorization: str = Header(default="")):
    """Endpoint de teste do bot — simula recebimento de mensagem WhatsApp.
    Requer token admin. Retorna resposta bruta do bot e dados da conversa.
    """
    _verificar_admin(authorization)
    if body.reset:
        _clear_conv(body.tel)
    resposta = _processar(body.tel, body.mensagem, body.fazenda_id)
    conv = _get_conv(body.tel)
    return {
        "resposta":  resposta,
        "estado":    conv.get("estado"),
        "tipo":      conv.get("tipo"),
        "dados":     conv.get("dados", {}),
    }


@app.get("/status")
def status(authorization: str = Header(default="")):
    """Status do bot — requer token admin."""
    _verificar_admin(authorization)
    try:
        _db()
        firebase_ok = True
    except Exception:
        firebase_ok = False
    return {
        "firebase":  firebase_ok,
        "anthropic": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "groq":      bool(os.environ.get("GROQ_API_KEY")),
        "twilio":    bool(os.environ.get("TWILIO_ACCOUNT_SID")),
    }


@app.post("/disparar_alertas")
def disparar_alertas(authorization: str = Header(default="")):
    """Dispara alertas proativos imediatamente para todos os números cadastrados."""
    _verificar_admin(authorization)
    registros = _todos_telefones()
    resultado = []
    for reg in registros:
        tel, fazenda_id = reg["tel"], reg["fazenda_id"]
        alertas = _gerar_alertas_proativos(fazenda_id)
        if alertas:
            msg = "*Alertas MilkShow:*\n" + "\n".join(f"• {a}" for a in alertas)
            ok  = _enviar_whatsapp(tel, msg)
            resultado.append({"tel": tel, "alertas": len(alertas), "enviado": ok})
        else:
            resultado.append({"tel": tel, "alertas": 0, "enviado": False})
    return {"disparados": resultado}


@app.post("/relatorio_semanal")
def relatorio_semanal(authorization: str = Header(default="")):
    """Dispara relatório semanal imediatamente para todos os números cadastrados."""
    _verificar_admin(authorization)
    registros = _todos_telefones()
    resultado = []
    for reg in registros:
        tel, fazenda_id = reg["tel"], reg["fazenda_id"]
        rel = _gerar_relatorio_semanal(fazenda_id)
        ok  = _enviar_whatsapp(tel, rel)
        resultado.append({"tel": tel, "enviado": ok})
    return {"disparados": resultado}


@app.post("/webhook/evolution")
async def webhook_evolution(request: Request):
    """Webhook da Evolution API (self-hosted, grátis).
    Configure no painel Evolution: POST https://seu-dominio/webhook/evolution
    """
    # Valida apikey enviada pela Evolution no header (usa EVOLUTION_WEBHOOK_KEY se definida)
    ev_key = os.environ.get("EVOLUTION_WEBHOOK_KEY", "")
    if ev_key:
        apikey_header = request.headers.get("apikey", "")
        if apikey_header != ev_key:
            log.warning("webhook/evolution: apikey inválida — requisição bloqueada")
            return {"ok": True}  # retorna 200 para não revelar que foi bloqueado

    try:
        body = await request.json()
    except Exception:
        return {"ok": True}

    # Evolution envia vários tipos de evento; só processa mensagens recebidas
    evento = body.get("event", "")
    if evento not in ("messages.upsert", "message"):
        return {"ok": True}

    # Evolution v2: body["data"] pode ser lista ou objeto direto
    raw_data = body.get("data", {})
    if isinstance(raw_data, list):
        if not raw_data:
            return {"ok": True}
        data = raw_data[0]          # pega o primeiro item da lista
    else:
        data = raw_data

    key  = data.get("key", {})

    # Ignora mensagens enviadas pelo próprio bot
    if key.get("fromMe"):
        return {"ok": True}

    # Ignora grupos (remoteJid termina com @g.us)
    remote = key.get("remoteJid", "")       # ex: "5577981258479@s.whatsapp.net"
    if remote.endswith("@g.us"):
        return {"ok": True}

    # Extrai número — para LIDs usa o JID completo (Evolution v1 tenta enviar assim)
    tel_raw   = remote.split("@")[0]
    tel_limpo = _normalizar_tel(tel_raw)
    # Guarda o JID original para usar no envio
    _JID_CACHE[tel_limpo] = remote

    # Extrai texto (suporta conversation e extendedTextMessage)
    msg = data.get("message", {})
    texto = (
        msg.get("conversation") or
        msg.get("extendedTextMessage", {}).get("text") or
        ""
    ).strip()

    # Áudio (audioMessage)
    if not texto and "audioMessage" in msg:
        try:
            # Evolution serve a mídia via URL própria
            ev_url  = os.environ.get("EVOLUTION_URL", "").rstrip("/")
            ev_key  = os.environ.get("EVOLUTION_KEY", "")
            ev_inst = os.environ.get("EVOLUTION_INSTANCE", "milkshow")
            msg_id  = key.get("id", "")
            media_url = f"{ev_url}/chat/getBase64FromMediaMessage/{ev_inst}"
            async with httpx.AsyncClient(timeout=20) as c:
                r = await c.post(
                    media_url,
                    headers={"apikey": ev_key},
                    json={"message": data},
                )
                b64_data = r.json().get("base64", "")
            if b64_data:
                import base64 as _b64
                audio_bytes = _b64.b64decode(b64_data)
                # Transcreve via Groq
                groq_key = os.environ.get("GROQ_API_KEY", "")
                if groq_key:
                    async with httpx.AsyncClient(timeout=30) as c:
                        resp = await c.post(
                            "https://api.groq.com/openai/v1/audio/transcriptions",
                            headers={"Authorization": f"Bearer {groq_key}"},
                            files={"file": ("audio.ogg", audio_bytes, "audio/ogg")},
                            data={"model": "whisper-large-v3-turbo", "language": "pt"},
                        )
                        texto = resp.json().get("text", "")
        except Exception as e:
            log.error(f"Evolution audio error: {e}")

    # Imagem
    if not texto and "imageMessage" in msg:
        try:
            ev_url  = os.environ.get("EVOLUTION_URL", "").rstrip("/")
            ev_key  = os.environ.get("EVOLUTION_KEY", "")
            ev_inst = os.environ.get("EVOLUTION_INSTANCE", "milkshow")
            async with httpx.AsyncClient(timeout=20) as c:
                r = await c.post(
                    f"{ev_url}/chat/getBase64FromMediaMessage/{ev_inst}",
                    headers={"apikey": ev_key},
                    json={"message": data},
                )
                b64_data = r.json().get("base64", "")
            if b64_data:
                import base64 as _b64
                img_bytes = _b64.b64decode(b64_data)
                b64_str = _b64.standard_b64encode(img_bytes).decode()
                _VISION_PROMPT = (
                    "Analise esta imagem de uma fazenda leiteira. Identifique qual dos tipos:\n\n"
                    "A) NOTA FISCAL / RECIBO / CUPOM: tem produtos, quantidades, valores, nome da loja.\n"
                    "B) TABELA MENSAL DE PRODUÇÃO: coluna de datas e coluna de litros, dia a dia. "
                    "Pode ser manuscrita em papel ou lousa. "
                    "O título/cabeçalho pode ser o nome do produtor ou da fazenda — NÃO é necessariamente o nome de uma vaca. "
                    "Se a tabela não identificar explicitamente um animal, use Animal: Rebanho.\n"
                    "C) LISTA DE VACAS DO DIA: lista com vários animais identificados pelo nome e seus litros. "
                    "Cada linha tem nome da vaca + litros (ex: Rainha 18L). Pode ser manuscrita.\n"
                    "D) OUTRO\n\n"
                    "Se A: responda exatamente:\n"
                    "[NOTA FISCAL]\nFornecedor: ...\nItens:\n- Produto: X, Qtd: N, Unidade: U, Valor: R$V\n\n"
                    "Se B: responda exatamente (leia com cuidado a escrita manual):\n"
                    "[TABELA MENSAL]\nAnimal: (nome da vaca se identificado, senão 'Rebanho')\nMes: MM/AAAA\nRegistros:\n"
                    "- Data: DD/MM/AAAA, Litros: N\n"
                    "(use '//' para dias sem dado — ex: Litros: //)\n\n"
                    "Se C: responda exatamente:\n"
                    "[PRODUCAO DO DIA]\nData: DD/MM/AAAA (se visível, senão 'hoje')\nAnimais:\n"
                    "- Animal: NomeVaca, Litros: N\n\n"
                    "Se D: descreva brevemente.\n"
                    "Extraia TODOS os dados visíveis. Inclua todas as linhas. "
                    "Ignore rasuras. Responda somente os dados."
                )
                texto_img = ""
                # Tenta Gemini Vision via REST direto
                google_key = os.environ.get("GOOGLE_API_KEY", "")
                if google_key:
                    _candidates = [
                        ("v1",     "gemini-2.0-flash"),
                        ("v1beta", "gemini-1.5-flash"),
                        ("v1beta", "gemini-2.0-flash"),
                    ]
                    for _api_ver, _gmodel in _candidates:
                        try:
                            async with httpx.AsyncClient(timeout=30) as gc:
                                gr = await gc.post(
                                    f"https://generativelanguage.googleapis.com/{_api_ver}/models/{_gmodel}:generateContent",
                                    params={"key": google_key},
                                    json={"contents": [{"parts": [
                                        {"inline_data": {"mime_type": "image/jpeg", "data": b64_str}},
                                        {"text": _VISION_PROMPT},
                                    ]}]},
                                )
                            if gr.status_code == 429:
                                log.warning(f"Gemini Vision ({_gmodel}) rate limit (429) — tentando próximo")
                                continue
                            if gr.status_code not in (200, 201):
                                log.warning(f"Gemini Vision ({_gmodel}) HTTP {gr.status_code} — tentando próximo")
                                continue
                            gdata = gr.json()
                            texto_img = gdata["candidates"][0]["content"]["parts"][0]["text"].strip()
                            log.info(f"[Evolution] Gemini Vision ({_api_ver}/{_gmodel}) extraiu: {texto_img[:200]}")
                            break
                        except Exception as eg:
                            log.warning(f"Gemini Vision ({_gmodel}) falhou: {eg}")
                # Fallback Claude Vision
                if not texto_img:
                    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
                    if anthropic_key:
                        try:
                            from anthropic import Anthropic
                            client = Anthropic(api_key=anthropic_key)
                            cresp = client.messages.create(
                                model="claude-haiku-4-5-20251001", max_tokens=600,
                                messages=[{"role": "user", "content": [
                                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64_str}},
                                    {"type": "text", "text": _VISION_PROMPT},
                                ]}],
                            )
                            texto_img = cresp.content[0].text.strip()
                            log.info(f"[Evolution] Claude Vision extraiu: {texto_img[:200]}")
                        except Exception as ec:
                            log.warning(f"Claude Vision falhou: {ec}")
                log.info(f"[Evolution] Vision extraiu: {texto_img[:200]}")
                if "[TABELA MENSAL]" in texto_img:
                    texto = f"[Foto tabela mensal de producao] {texto_img}"
                elif "[PRODUCAO DO DIA]" in texto_img:
                    texto = f"[Foto producao do dia] {texto_img}"
                elif "[NOTA FISCAL]" in texto_img:
                    texto = f"[Nota fiscal] {texto_img}"
                else:
                    texto = f"[Foto] {texto_img}"
        except Exception as e:
            log.error(f"Evolution imagem error: {e}")

    log.info(f"[Evolution][{tel_limpo}] mensagem: '{texto[:80]}'")

    if not texto:
        return {"ok": True}

    user_info = _find_user_info(tel_limpo)
    if user_info is None:
        # Inicia/continua onboarding em vez de rejeitar
        _asyncio_fila.create_task(
            _asyncio_fila.to_thread(_processar_onboarding, tel_limpo, texto)
        )
        return {"ok": True}

    fazenda_id = user_info["fazenda_id"]
    permissoes = user_info["permissoes"]

    # Saudação simples: "oi", "olá", "bom dia" etc → responde direto sem IA
    _SAUDACOES = {"oi", "olá", "ola", "oii", "oiii", "hey", "ei",
                  "bom dia", "boa tarde", "boa noite", "bom dia!", "boa tarde!", "boa noite!"}
    if texto.strip().lower().rstrip("!").strip() in _SAUDACOES or texto.strip().lower() in _SAUDACOES:
        nome = user_info.get("nome", "").split()[0] if user_info.get("nome") else ""
        saudacao = f"Oi, {nome}! " if nome else "Oi! "
        _enviar_whatsapp(tel_limpo, saudacao + "Como posso ajudar? 😊")
        return {"ok": True}

    # Anti-flood: se chegaram várias mensagens juntas (offline), agrupa antes de processar
    with _FILA_LOCK:
        tem_fila = tel_limpo in _FILA
    if tem_fila:
        with _FILA_LOCK:
            _FILA[tel_limpo].append({"texto": texto, "ts": datetime.datetime.now()})
        log.info(f"[{tel_limpo}] mensagem adicionada à fila ({len(_FILA[tel_limpo])} total)")
        return {"ok": True}

    _iniciar_fila(tel_limpo, texto)

    async def _processar_e_enviar():
        await _asyncio_fila.sleep(_FILA_JANELA)
        with _FILA_LOCK:
            msgs = _FILA.pop(tel_limpo, [])
        if not msgs:
            return
        if len(msgs) == 1:
            texto_final = msgs[0]["texto"]
        else:
            texto_final = " | ".join(m["texto"] for m in msgs)
            log.info(f"[{tel_limpo}] {len(msgs)} msgs agrupadas offline: '{texto_final[:80]}'")
        import asyncio as _aio
        # Mostra "digitando..." imediatamente enquanto processa
        _aio.create_task(_aio.to_thread(_enviar_typing, tel_limpo, 6000))
        # Roda em thread para não bloquear o event loop (Firestore + httpx síncronos)
        resposta = await _aio.to_thread(_processar, tel_limpo, texto_final, fazenda_id, permissoes)
        if resposta != "__botoes_enviados__":
            await _aio.to_thread(_enviar_whatsapp, tel_limpo, resposta)

    _asyncio_fila.create_task(_processar_e_enviar())
    return {"ok": True}  # retorna imediatamente — processa em background


@app.post("/webhook/whatsapp")
@app.post("/webhook")
async def webhook(
    request:   Request,
    From:      str = Form(...),
    Body:      str = Form(default=""),
    NumMedia:  str = Form(default="0"),
    MediaUrl0: str = Form(default=""),
    MediaContentType0: str = Form(default=""),
    AccountSid: str = Form(default=""),
):
    tel_limpo = _normalizar_tel(From)
    texto     = (Body or "").strip()
    log.info(f"[{tel_limpo}] mensagem: '{texto[:80]}' | media: {NumMedia}")

    # ── Identifica a fazenda pelo número ─────
    user_info = _find_user_info(tel_limpo)
    if user_info is None:
        log.warning(f"[{tel_limpo}] numero nao cadastrado")
        return _twiml(
            "Numero nao cadastrado no MilkShow.\n"
            "Acesse o app, va em Configuracoes > Bot IA e informe este numero."
        )

    fazenda_id = user_info["fazenda_id"]
    permissoes = user_info["permissoes"]
    log.info(f"[{tel_limpo}] fazenda: {fazenda_id}")

    twilio_token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    num_media    = int(NumMedia or 0)
    ctype        = (MediaContentType0 or "").lower()

    # ── Áudio ────────────────────────────────
    if num_media > 0 and "audio" in ctype:
        transcrito = await _transcrever(MediaUrl0, AccountSid, twilio_token, ctype)
        if transcrito:
            texto = transcrito
            log.info(f"[{tel_limpo}] audio transcrito: '{texto[:80]}'")
        else:
            return _twiml("Nao consegui transcrever o audio. Tente enviar em texto.")

    # ── Imagem / Nota Fiscal ─────────────────
    elif num_media > 0 and ("image" in ctype or "pdf" in ctype):
        extraido = await _ler_imagem(MediaUrl0, AccountSid, twilio_token, ctype or "image/jpeg")
        if extraido:
            texto = extraido
            log.info(f"[{tel_limpo}] imagem processada: '{texto[:80]}'")
        else:
            return _twiml("Nao consegui ler a imagem. Envie os dados em texto.")

    if not texto:
        return _twiml(
            "Ola! Envie mensagem, audio ou foto de nota fiscal.\n"
            "Digite ajuda para ver exemplos."
        )

    # Anti-flood: agrupa mensagens que chegam juntas (produtor ficou offline)
    with _FILA_LOCK:
        tem_fila = tel_limpo in _FILA
    if tem_fila:
        with _FILA_LOCK:
            _FILA[tel_limpo].append({"texto": texto, "ts": datetime.datetime.now()})
        log.info(f"[{tel_limpo}] mensagem adicionada à fila ({len(_FILA[tel_limpo])} total)")
        return _twiml("")   # Twilio ignora resposta vazia

    _iniciar_fila(tel_limpo, texto)
    await _asyncio_fila.sleep(_FILA_JANELA)

    with _FILA_LOCK:
        msgs = _FILA.pop(tel_limpo, [])

    if not msgs:
        return _twiml("")

    if len(msgs) == 1:
        texto_final = msgs[0]["texto"]
    else:
        texto_final = " | ".join(m["texto"] for m in msgs)
        log.info(f"[{tel_limpo}] {len(msgs)} msgs agrupadas offline: '{texto_final[:80]}'")

    resposta = _processar(tel_limpo, texto_final, fazenda_id, permissoes)
    return _twiml(resposta)


# ─────────────────────────────────────────────
# STARTUP — túnel ngrok automático
# ─────────────────────────────────────────────
@app.on_event("startup")
async def _abrir_tunel():
    ngrok_token = os.environ.get("NGROK_AUTHTOKEN", "")
    if not ngrok_token:
        return  # produção usa nginx — ngrok não necessário
    try:
        import ngrok as ngrok_sdk
        listener = await ngrok_sdk.forward(8000, authtoken=ngrok_token)
        url = listener.url()
        log.info("=" * 60)
        log.info(f"URL PUBLICA DO BOT: {url}/webhook/whatsapp")
        log.info("Cole essa URL no Twilio Console como webhook do WhatsApp.")
        log.info("=" * 60)
        # Persiste a URL no Firebase para exibir no Streamlit
        try:
            _db().collection("config").document("ngrok_url").set({
                "url": url + "/webhook/whatsapp",
                "ts":  datetime.datetime.now().isoformat(),
            })
        except Exception:
            pass
    except Exception as e:
        log.warning(f"Falha ao abrir tunel ngrok: {e}")

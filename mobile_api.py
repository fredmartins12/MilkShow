"""
mobile_api.py — MilkShow REST API para o App Mobile
====================================================
Endpoints consumidos pelo app React PWA.
Autenticação via token JWT simples (sem dependência externa pesada).
Inclua no whatsapp_bot.py:
    from mobile_api import mobile_router
    app.include_router(mobile_router)
"""

import os
import re
import hmac
import hashlib
import json
import asyncio
import datetime
import time
import base64
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Header, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

# Inicializa Firebase Admin uma única vez no carregamento do módulo
if not firebase_admin._apps:
    _fb_key = os.path.join(os.path.dirname(__file__), "firebase_key.json")
    firebase_admin.initialize_app(credentials.Certificate(_fb_key))

mobile_router = APIRouter(prefix="/api/v1", tags=["mobile"])

# ─────────────────────────────────────────────
# RATE LIMITER (in-memory, funciona com --workers 1)
# ─────────────────────────────────────────────
_RATE_WINDOW   = 15 * 60   # 15 minutos
_RATE_MAX_FAIL = 5          # máximo de falhas por janela
_rate_data: dict = {}       # {ip: {"count": int, "until": float, "ts": float}}

def _check_rate_limit(ip: str):
    """Bloqueia IP após 5 falhas em 15 min. Levanta 429 se bloqueado."""
    now = time.time()
    entry = _rate_data.get(ip, {"count": 0, "until": 0.0, "ts": now})
    if now < entry["until"]:
        restante = int(entry["until"] - now)
        raise HTTPException(
            status_code=429,
            detail=f"Muitas tentativas. Tente novamente em {restante}s."
        )
    if now - entry["ts"] > _RATE_WINDOW:
        entry = {"count": 0, "until": 0.0, "ts": now}
    _rate_data[ip] = entry

def _registrar_falha(ip: str):
    """Incrementa contador de falhas. Bloqueia IP ao atingir limite."""
    now = time.time()
    entry = _rate_data.get(ip, {"count": 0, "until": 0.0, "ts": now})
    entry["count"] += 1
    if entry["count"] >= _RATE_MAX_FAIL:
        entry["until"] = now + _RATE_WINDOW
        entry["count"] = 0
        entry["ts"] = now
    _rate_data[ip] = entry

def _limpar_rate(ip: str):
    """Remove registro após login bem-sucedido."""
    _rate_data.pop(ip, None)

# Limpeza periódica de entradas antigas
def _rate_gc():
    now = time.time()
    for ip in list(_rate_data):
        e = _rate_data[ip]
        if now - e["ts"] > _RATE_WINDOW * 2 and now > e.get("until", 0):
            del _rate_data[ip]

# ─────────────────────────────────────────────
# NOTIFICAÇÕES EM TEMPO REAL (SSE)
# ─────────────────────────────────────────────
# Dicionário: fazenda_id → {"colecao": str, "ts": float}
# Atualizado pelo bot após cada escrita — clientes SSE detectam a mudança
_UPDATE_TS: dict = {}


def notify_update(fazenda_id: str, colecao: str = "all"):
    """Chamado pelo bot após salvar dados — acorda clientes SSE daquela fazenda."""
    _UPDATE_TS[fazenda_id] = {"colecao": colecao, "ts": time.time()}

# ─────────────────────────────────────────────
# JWT simples (sem dependência extra)
# ─────────────────────────────────────────────
_SECRET = os.environ.get("BOT_ADMIN_TOKEN")
if not _SECRET:
    import secrets as _secrets_mod
    _SECRET = _secrets_mod.token_hex(32)
    logger.warning(
        "BOT_ADMIN_TOKEN não definido — usando secret temporário. "
        "Tokens não persistem entre restarts."
    )

def _jwt_encode(payload: dict) -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b'=').decode()
    body   = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b'=').decode()
    sig    = hmac.new(_SECRET.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b'=').decode()
    return f"{header}.{body}.{sig_b64}"

def _jwt_decode(token: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header, body, sig = parts
        expected = hmac.new(_SECRET.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest()
        expected_b64 = base64.urlsafe_b64encode(expected).rstrip(b'=').decode()
        if not hmac.compare_digest(sig, expected_b64):
            return None
        padding = 4 - len(body) % 4
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * padding))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


# ─────────────────────────────────────────────
# Firebase helper
# ─────────────────────────────────────────────
def _db():
    return firestore.client()

def _coll(fazenda_id: str, nome: str):
    db = _db()
    if fazenda_id == "default":
        return db.collection(nome)
    return db.collection("fazendas").document(fazenda_id).collection(nome)


def _custo_racao_kg_real(fazenda_id: str) -> float:
    """Retorna o custo real da ração/kg baseado no estoque. Fallback: 1.20."""
    try:
        for e in _coll(fazenda_id, "estoque").stream():
            ed = e.to_dict()
            item = (ed.get("item") or "").lower()
            if any(k in item for k in ("ração", "racao", "concentrado", "milho")):
                qtd = float(ed.get("qtd") or 0)
                val = float(ed.get("custo_unit") or 0)
                if val > 0:
                    return round(val, 4)
                # Calcula por valor_total / qtd se disponível
                val_tot = float(ed.get("valor_total") or 0)
                if qtd > 0 and val_tot > 0:
                    return round(val_tot / qtd, 4)
    except Exception:
        pass
    return 1.20

def _normalizar_tel(raw: str) -> str:
    digits = re.sub(r'\D', '', raw.strip())
    if not digits.startswith('55'):
        digits = '55' + digits
    return digits

def _variantes_tel(tel: str):
    variantes = [tel]
    sem_55 = tel[2:] if tel.startswith('55') else tel
    variantes.append(sem_55)
    if tel.startswith('55'):
        resto = tel[2:]
        if len(resto) == 10:
            variantes.append('55' + resto[:2] + '9' + resto[2:])
        elif len(resto) == 11 and resto[2] == '9':
            variantes.append('55' + resto[:2] + resto[3:])
    return list(dict.fromkeys(variantes))


# ─────────────────────────────────────────────
# Auth dependency
# ─────────────────────────────────────────────
def _get_user_from_token(token: str) -> Optional[dict]:
    """Extrai e valida payload JWT de um token string."""
    payload = _jwt_decode(token.strip())
    return payload  # None se inválido


def _get_user(authorization: str = Header(default="")):
    token = authorization.replace("Bearer ", "").strip()
    payload = _jwt_decode(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")
    return payload  # {tel, fazenda_id, nome, permissoes}


# ─────────────────────────────────────────────
# MODELOS
# ─────────────────────────────────────────────
class LoginRequest(BaseModel):
    tel: str
    pin: str

    @field_validator("tel")
    @classmethod
    def tel_nao_vazio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Telefone obrigatório")
        return v

    @field_validator("pin")
    @classmethod
    def pin_nao_vazio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("PIN obrigatório")
        return v

class ProducaoInput(BaseModel):
    data: str
    id_animal: str
    nome_animal: str
    leite: float
    racao: float = 0.0
    turno: str = "manhã"
    obs: str = ""

    @field_validator("data")
    @classmethod
    def data_formato(cls, v: str) -> str:
        try:
            datetime.date.fromisoformat(v)
        except (ValueError, TypeError):
            raise ValueError("Campo 'data' deve estar no formato YYYY-MM-DD")
        return v

    @field_validator("leite")
    @classmethod
    def leite_positivo(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Produção de leite não pode ser negativa")
        return v

    @field_validator("racao")
    @classmethod
    def racao_nao_negativa(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Quantidade de ração não pode ser negativa")
        return v

    @field_validator("nome_animal", "id_animal")
    @classmethod
    def campo_nao_vazio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Campo obrigatório não pode ser vazio")
        return v

_TIPOS_FINANCEIRO = {"receita", "despesa"}

class FinanceiroInput(BaseModel):
    data: str
    descricao: str = ""
    categoria: str = "Outros"
    cat: str = ""          # alias legacy
    valor: float
    tipo: str              # "receita" | "despesa"
    obs: str = ""

    @field_validator("data")
    @classmethod
    def data_formato(cls, v: str) -> str:
        try:
            datetime.date.fromisoformat(v)
        except (ValueError, TypeError):
            raise ValueError("Campo 'data' deve estar no formato YYYY-MM-DD")
        return v

    @field_validator("tipo")
    @classmethod
    def tipo_valido(cls, v: str) -> str:
        if v not in _TIPOS_FINANCEIRO:
            raise ValueError(f"tipo deve ser: {', '.join(_TIPOS_FINANCEIRO)}")
        return v

    @field_validator("valor")
    @classmethod
    def valor_positivo(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Valor não pode ser negativo")
        return v

class EstoqueInput(BaseModel):
    item: str
    qtd: float
    un: str
    custo_unit: float = 0.0
    categoria: str = "Outros"
    min_alerta: Optional[float] = None

    @field_validator("item")
    @classmethod
    def item_nao_vazio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Nome do item obrigatório")
        return v

    @field_validator("qtd")
    @classmethod
    def qtd_nao_negativa(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Quantidade não pode ser negativa")
        return v

    @field_validator("custo_unit")
    @classmethod
    def custo_nao_negativo(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Custo unitário não pode ser negativo")
        return v

class UsuarioWppInput(BaseModel):
    tel: str          # aceita (83) 99999-0000 ou 5583999990000
    nome: str
    perfil: str       # 'admin' | 'operador' | 'vet' | 'visualizador'

    @field_validator("nome")
    @classmethod
    def nome_nao_vazio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Nome obrigatório")
        return v

class ChatInput(BaseModel):
    mensagem: str


# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────
@mobile_router.post("/auth/login")
def login(body: LoginRequest, request: Request):
    ip = request.headers.get("X-Real-IP") or request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or (request.client.host if request.client else "unknown")
    _rate_gc()
    _check_rate_limit(ip)

    tel = _normalizar_tel(body.tel)
    db  = _db()

    user_doc = None
    for variante in _variantes_tel(tel):
        doc = db.collection("registros_tel").document(variante).get()
        if doc.exists and doc.to_dict().get("ativo", True):
            user_doc = doc.to_dict()
            break

    if not user_doc:
        _registrar_falha(ip)
        raise HTTPException(status_code=404, detail="Número não cadastrado no MilkShow")

    pin_salvo = user_doc.get("pin_hash", "")

    if not pin_salvo:
        # Primeiro acesso: define o PIN como bcrypt
        import bcrypt as _bcrypt
        novo_hash = _bcrypt.hashpw(body.pin.encode(), _bcrypt.gensalt()).decode()
        db.collection("registros_tel").document(tel).set({"pin_hash": novo_hash}, merge=True)
    elif pin_salvo.startswith("$2b$") or pin_salvo.startswith("$2a$"):
        # bcrypt
        import bcrypt as _bcrypt
        if not _bcrypt.checkpw(body.pin.encode(), pin_salvo.encode()):
            _registrar_falha(ip)
            raise HTTPException(status_code=401, detail="PIN incorreto")
    else:
        # Legacy SHA256 — valida e migra para bcrypt
        pin_hash_legacy = hashlib.sha256(body.pin.encode()).hexdigest()
        if not hmac.compare_digest(pin_hash_legacy, pin_salvo):
            _registrar_falha(ip)
            raise HTTPException(status_code=401, detail="PIN incorreto")
        import bcrypt as _bcrypt
        novo_hash = _bcrypt.hashpw(body.pin.encode(), _bcrypt.gensalt()).decode()
        db.collection("registros_tel").document(tel).set({"pin_hash": novo_hash}, merge=True)

    _limpar_rate(ip)
    exp = datetime.datetime.utcnow() + datetime.timedelta(days=30)
    token = _jwt_encode({
        "tel":        tel,
        "fazenda_id": user_doc.get("fazenda_id", "default"),
        "nome":       user_doc.get("nome", ""),
        "permissoes": user_doc.get("permissoes", ["admin"]),
        "exp":        exp.timestamp(),
    })
    return {"token": token, "nome": user_doc.get("nome", ""), "fazenda_id": user_doc.get("fazenda_id", "default")}


class GoogleLoginRequest(BaseModel):
    id_token: str

@mobile_router.post("/auth/google")
def google_login(body: GoogleLoginRequest):
    """Login via Google (Firebase ID token). Cria fazenda se for primeiro acesso."""
    from firebase_admin import auth as fb_auth
    try:
        decoded = fb_auth.verify_id_token(body.id_token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token Google inválido: {e}")

    uid   = decoded['uid']
    email = decoded.get('email', '')
    name  = decoded.get('name', '')
    db    = _db()

    user_doc = db.collection('users').document(uid).get()
    if user_doc.exists:
        ud         = user_doc.to_dict()
        fazenda_id = ud.get('fazenda_id', uid)
        nome       = ud.get('nome', name)
        permissoes = ud.get('permissoes', ['admin'])
    else:
        nome       = name or (email.split('@')[0] if email else uid)
        fazenda_id = uid
        permissoes = ['admin']
        db.collection('fazendas').document(uid).set({
            'nome': nome, 'owner_uid': uid, 'owner_email': email,
            'created_at': datetime.datetime.now().isoformat(), 'plano': 'trial',
        })
        db.collection('users').document(uid).set({
            'email': email, 'fazenda_id': uid, 'nome': nome,
            'created_at': datetime.datetime.now().isoformat(),
            'permissoes': permissoes,
        })

    exp   = datetime.datetime.utcnow() + datetime.timedelta(days=30)
    token = _jwt_encode({
        'uid':        uid,
        'email':      email,
        'fazenda_id': fazenda_id,
        'nome':       nome,
        'permissoes': permissoes,
        'exp':        exp.timestamp(),
    })
    return {'token': token, 'nome': nome, 'email': email, 'fazenda_id': fazenda_id}


@mobile_router.post("/auth/set-pin")
def set_pin(body: LoginRequest, user=Depends(_get_user)):
    """Troca o PIN do usuário logado."""
    import bcrypt as _bcrypt
    tel = user["tel"]
    novo_hash = _bcrypt.hashpw(body.pin.encode(), _bcrypt.gensalt()).decode()
    _db().collection("registros_tel").document(tel).set({"pin_hash": novo_hash}, merge=True)
    return {"ok": True}


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────
@mobile_router.get("/dashboard")
def dashboard(user=Depends(_get_user)):
    fid    = user["fazenda_id"]
    hoje   = datetime.date.today()
    ontem  = hoje - datetime.timedelta(days=1)
    ini_7  = hoje - datetime.timedelta(days=7)
    ini_14 = hoje - datetime.timedelta(days=14)
    ini_m  = hoje.replace(day=1)
    # Mês anterior
    primeiro_dia_mes = hoje.replace(day=1)
    ultimo_dia_mes_ant = primeiro_dia_mes - datetime.timedelta(days=1)
    ini_mes_ant = ultimo_dia_mes_ant.replace(day=1)

    # Produção: busca desde o início do mês (cobre 14 dias e litros_mes ao mesmo tempo)
    ini_query = min(ini_14, ini_m)
    prod_14d = [d.to_dict() for d in
                _coll(fid, "producao")
                .where(filter=FieldFilter("data", ">=", ini_query.isoformat())).stream()]

    litros_hoje      = sum(p.get("leite", 0) for p in prod_14d if p.get("data") == hoje.isoformat())
    litros_ontem     = sum(p.get("leite", 0) for p in prod_14d if p.get("data") == ontem.isoformat())
    litros_7d        = sum(p.get("leite", 0) for p in prod_14d if p.get("data", "") >= ini_7.isoformat())
    litros_semana_ant= sum(p.get("leite", 0) for p in prod_14d
                           if ini_14.isoformat() <= p.get("data", "") < ini_7.isoformat())
    litros_mes       = sum(p.get("leite", 0) for p in prod_14d if p.get("data", "") >= ini_m.isoformat())

    prod_hoje_docs   = [p for p in prod_14d if p.get("data") == hoje.isoformat()]
    ordenhadas_hoje  = len({p.get("id_animal") for p in prod_hoje_docs})

    # Financeiro mês atual
    fin_mes = [d.to_dict() for d in
               _coll(fid, "financeiro").where(filter=FieldFilter("data", ">=", ini_m.isoformat())).stream()]
    def _cat(f): return f.get("categoria") or f.get("cat", "")
    receitas = sum(f.get("valor", 0) for f in fin_mes if f.get("tipo") == "receita" or "Venda" in _cat(f))
    despesas = sum(f.get("valor", 0) for f in fin_mes if f.get("tipo") == "despesa" and "Venda" not in _cat(f))

    # Financeiro mês anterior
    fin_mes_ant = [d.to_dict() for d in
                   _coll(fid, "financeiro")
                   .where(filter=FieldFilter("data", ">=", ini_mes_ant.isoformat()))
                   .where(filter=FieldFilter("data", "<=", ultimo_dia_mes_ant.isoformat())).stream()]
    receitas_ant = sum(f.get("valor", 0) for f in fin_mes_ant if f.get("tipo") == "receita" or "Venda" in _cat(f))
    despesas_ant = sum(f.get("valor", 0) for f in fin_mes_ant if f.get("tipo") == "despesa" and "Venda" not in _cat(f))

    # Animais
    animais = [d.to_dict() for d in _coll(fid, "animais").stream()]
    em_lactacao = [a for a in animais if a.get("status") == "Lactação"]

    # Config
    config = {}
    for d in _coll(fid, "config").stream():
        c = d.to_dict()
        config[c.get("chave", d.id)] = c.get("valor")
    preco_leite     = float(config.get("preco_leite", 2.50))
    custo_por_litro = float(config.get("custo_por_litro", 1.18))
    meta_producao   = float(config.get("meta_producao", 0))
    custo_racao_kg  = _custo_racao_kg_real(fid)

    def _delta(atual, anterior):
        if anterior and anterior > 0:
            return round(((atual - anterior) / anterior) * 100, 1)
        return None

    return {
        "hoje": {
            "data":              hoje.isoformat(),
            "litros":            round(litros_hoje, 1),
            "litros_ontem":      round(litros_ontem, 1),
            "delta_producao":    _delta(litros_hoje, litros_ontem),
            "receita_est":       round(litros_hoje * preco_leite, 2),
            "vacas_lact":        len(em_lactacao),
            "vacas_ordenhadas":  ordenhadas_hoje,
        },
        "semana": {
            "litros_7d":         round(litros_7d, 1),
            "litros_semana_ant": round(litros_semana_ant, 1),
            "delta_semana":      _delta(litros_7d, litros_semana_ant),
            "media_dia":         round(litros_7d / 7, 1),
        },
        "mes": {
            "litros_mes":        round(litros_mes, 1),
            "receitas":          round(receitas, 2),
            "despesas":          round(despesas, 2),
            "saldo":             round(receitas - despesas, 2),
            "receitas_ant":      round(receitas_ant, 2),
            "despesas_ant":      round(despesas_ant, 2),
            "delta_receitas":    _delta(receitas, receitas_ant),
            "delta_saldo":       _delta(receitas - despesas, receitas_ant - despesas_ant),
        },
        "preco_leite":     preco_leite,
        "custo_por_litro": custo_por_litro,
        "custo_racao_kg":  custo_racao_kg,
        "meta_producao":   meta_producao,
    }


# ─────────────────────────────────────────────
# ANIMAIS
# ─────────────────────────────────────────────
@mobile_router.get("/animais")
def listar_animais(user=Depends(_get_user)):
    fid = user["fazenda_id"]
    docs = []
    for doc in _coll(fid, "animais").stream():
        row = doc.to_dict()
        row["id"] = doc.id          # sempre inclui o doc ID para DELETE funcionar
        docs.append(row)
    ativos = [a for a in docs if a.get("status") != "Vendido"]
    return sorted(ativos, key=lambda a: a.get("nome", ""))


# ─────────────────────────────────────────────
# PRODUÇÃO
# ─────────────────────────────────────────────
@mobile_router.get("/producao")
def listar_producao(data: Optional[str] = None, dias: int = 7, user=Depends(_get_user)):
    fid = user["fazenda_id"]
    if data:
        ini = data
    else:
        ini = (datetime.date.today() - datetime.timedelta(days=dias)).isoformat()
    docs = []
    for d in (_coll(fid, "producao").where(filter=FieldFilter("data", ">=", ini))
              .order_by("data", direction=firestore.Query.DESCENDING).limit(200).stream()):
        row = d.to_dict()
        row["id"] = d.id
        docs.append(row)
    return docs

@mobile_router.post("/producao")
def registrar_producao(body: ProducaoInput, user=Depends(_get_user)):
    fid = user["fazenda_id"]
    doc = body.model_dump()
    doc["registrado_por"] = user.get("nome") or user.get("email") or user.get("tel", "")
    doc["ts"] = datetime.datetime.now().isoformat()
    _, ref = _coll(fid, "producao").add(doc)
    notify_update(fid, "producao")
    return {"ok": True, "id": ref.id}

@mobile_router.delete("/producao/{pid}")
def remover_producao(pid: str, user=Depends(_get_user)):
    fid = user["fazenda_id"]
    _coll(fid, "producao").document(pid).delete()
    notify_update(fid, "producao")
    return {"ok": True}


# ─────────────────────────────────────────────
# FINANCEIRO
# ─────────────────────────────────────────────
@mobile_router.get("/financeiro")
def listar_financeiro(dias: int = 30, user=Depends(_get_user)):
    fid = user["fazenda_id"]
    ini = (datetime.date.today() - datetime.timedelta(days=dias)).isoformat()
    docs = []
    for d in (_coll(fid, "financeiro").where(filter=FieldFilter("data", ">=", ini))
              .order_by("data", direction=firestore.Query.DESCENDING).limit(200).stream()):
        row = d.to_dict()
        row["id"] = d.id
        docs.append(row)
    return docs

@mobile_router.post("/financeiro")
def registrar_financeiro(body: FinanceiroInput, user=Depends(_get_user)):
    fid = user["fazenda_id"]
    doc = body.model_dump()
    if not doc.get("categoria") and doc.get("cat"):
        doc["categoria"] = doc["cat"]
    if not doc.get("cat") and doc.get("categoria"):
        doc["cat"] = doc["categoria"]
    doc["registrado_por"] = user.get("nome", user.get("email", ""))
    doc["ts"] = datetime.datetime.now().isoformat()
    _, ref = _coll(fid, "financeiro").add(doc)
    notify_update(fid, "financeiro")
    return {"ok": True, "id": ref.id}

@mobile_router.delete("/financeiro/{fid_doc}")
def remover_financeiro(fid_doc: str, user=Depends(_get_user)):
    fid = user["fazenda_id"]
    _coll(fid, "financeiro").document(fid_doc).delete()
    notify_update(fid, "financeiro")
    return {"ok": True}

@mobile_router.patch("/financeiro/{fid_doc}")
def atualizar_financeiro(fid_doc: str, body: FinanceiroInput, user=Depends(_get_user)):
    fid = user["fazenda_id"]
    doc = body.model_dump()
    if not doc.get("categoria") and doc.get("cat"):
        doc["categoria"] = doc["cat"]
    if not doc.get("cat") and doc.get("categoria"):
        doc["cat"] = doc["categoria"]
    doc["atualizado_em"] = datetime.datetime.now().isoformat()
    _coll(fid, "financeiro").document(fid_doc).set(doc, merge=True)
    notify_update(fid, "financeiro")
    return {"ok": True}


# ─────────────────────────────────────────────
# ESTOQUE
# ─────────────────────────────────────────────
@mobile_router.get("/estoque")
def listar_estoque(user=Depends(_get_user)):
    fid = user["fazenda_id"]
    docs = _coll(fid, "estoque").stream()
    result = []
    for d in docs:
        row = d.to_dict()
        row["id"] = d.id
        result.append(row)
    return result

@mobile_router.post("/estoque")
def registrar_estoque(body: EstoqueInput, user=Depends(_get_user)):
    fid = user["fazenda_id"]
    doc = body.model_dump()
    doc["atualizado_em"] = datetime.datetime.now().isoformat()
    _, ref = _coll(fid, "estoque").add(doc)
    notify_update(fid, "estoque")
    return {"id": ref.id, **doc}

@mobile_router.delete("/estoque/{item_id}")
def remover_estoque(item_id: str, user=Depends(_get_user)):
    fid = user["fazenda_id"]
    _coll(fid, "estoque").document(item_id).delete()
    notify_update(fid, "estoque")
    return {"ok": True}


# ─────────────────────────────────────────────
# USUÁRIOS WHATSAPP
# ─────────────────────────────────────────────
PERFIS_WPP = {"admin", "operador", "vet", "visualizador"}

# Mapeamento perfil app → permissões do bot (usadas em _tem_permissao)
_PERFIL_PARA_PERMISSOES = {
    "admin":        ["admin"],
    "operador":     ["ordenha", "armazem"],          # peão: registra produção e usa estoque
    "vet":          ["financeiro", "rebanho"],        # veterinário: animais + gastos sanit.
    "visualizador": [],                               # só consultas (sem permissão de escrita)
}

@mobile_router.get("/usuarios_wpp")
def listar_usuarios_wpp(user=Depends(_get_user)):
    fid = user["fazenda_id"]
    docs = _coll(fid, "usuarios_wpp").stream()
    return [{"id": d.id, **d.to_dict()} for d in docs]

@mobile_router.post("/usuarios_wpp")
def adicionar_usuario_wpp(body: UsuarioWppInput, user=Depends(_get_user)):
    fid  = user["fazenda_id"]
    if body.perfil not in PERFIS_WPP:
        raise HTTPException(400, f"Perfil inválido. Use: {', '.join(PERFIS_WPP)}")
    tel = _normalizar_tel(body.tel)
    if len(tel) < 10:
        raise HTTPException(400, "Número inválido. Use DDD + número: (83) 99999-0000")

    permissoes = _PERFIL_PARA_PERMISSOES[body.perfil]
    agora = datetime.datetime.now().isoformat()
    doc_ui = {"tel": tel, "nome": body.nome.strip(), "perfil": body.perfil,
              "ativo": True, "criado_em": agora}

    db = _db()
    # 1. Salva por fazenda (para a UI do app)
    _coll(fid, "usuarios_wpp").document(tel).set(doc_ui)

    # 2. Salva em registros_tel — fonte de verdade do bot (multi-tenant isolado por fazenda_id)
    db.collection("registros_tel").document(tel).set({
        "tel":        tel,
        "nome":       body.nome.strip(),
        "fazenda_id": fid,
        "permissoes": permissoes,
        "perfil":     body.perfil,
        "ativo":      True,
        "criado_em":  agora,
        "criado_via": "app",
    }, merge=True)

    return {"ok": True, "tel": tel, "permissoes": permissoes}

@mobile_router.delete("/usuarios_wpp/{tel}")
def remover_usuario_wpp(tel: str, user=Depends(_get_user)):
    fid = user["fazenda_id"]
    tel_norm = _normalizar_tel(tel)
    db = _db()
    # Remove da coleção por fazenda (UI)
    _coll(fid, "usuarios_wpp").document(tel_norm).delete()
    # Desativa em registros_tel (mantém histórico mas bloqueia o bot)
    db.collection("registros_tel").document(tel_norm).set(
        {"ativo": False}, merge=True
    )
    return {"ok": True}


# ─────────────────────────────────────────────
# CHAT IA (mesma lógica do bot WhatsApp)
# ─────────────────────────────────────────────
@mobile_router.post("/chat")
def chat_ia(body: ChatInput, user=Depends(_get_user)):
    """Endpoint de chat que usa a mesma IA do bot WhatsApp.
    O identificador de conversa é web_{fazenda_id} para manter estado de sessão."""
    if not body.mensagem.strip():
        raise HTTPException(400, "Mensagem vazia")

    fazenda_id = user.get("fazenda_id", "default")
    permissoes = user.get("permissoes", ["admin"])
    # Identificador único por sessão web (mantém estado de conversa)
    tel_web    = f"web_{fazenda_id}"

    try:
        from whatsapp_bot import _processar
        resposta = _processar(tel_web, body.mensagem.strip(), fazenda_id, permissoes)
        return {"resposta": resposta or "✅ Feito!"}
    except Exception as e:
        logger.exception("Erro no chat IA para fazenda %s", fazenda_id)
        raise HTTPException(status_code=500, detail={"error": "Erro interno ao processar mensagem"})

@mobile_router.patch("/estoque/{item_id}")
def atualizar_estoque(item_id: str, body: EstoqueInput, user=Depends(_get_user)):
    fid = user["fazenda_id"]
    doc = body.model_dump()
    doc["atualizado_em"] = datetime.datetime.now().isoformat()
    _coll(fid, "estoque").document(item_id).set(doc)
    notify_update(fid, "estoque")
    return {"id": item_id, **doc}


# ─────────────────────────────────────────────
# ANIMAIS — POST (adicionar / atualizar)
# ─────────────────────────────────────────────
_STATUS_ANIMAL = {"Lactação", "Seca", "Novilha", "Vendido", "Morto", "Bezerra"}

class AnimalInput(BaseModel):
    nome: str
    status: str = "Lactação"
    raca: str = ""
    sexo: str = "Fêmea"
    nascimento: str = ""
    id: Optional[str] = None
    ins: str = ""          # última inseminação
    mae: str = ""
    obs: str = ""

    @field_validator("nome")
    @classmethod
    def nome_nao_vazio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Nome do animal obrigatório")
        return v

@mobile_router.post("/animais")
def adicionar_animal(body: AnimalInput, user=Depends(_get_user)):
    fid = user["fazenda_id"]
    doc = body.model_dump()
    doc["ts"] = datetime.datetime.now().isoformat()
    aid = doc.pop("id", None) or None
    if aid:
        _coll(fid, "animais").document(aid).set(doc, merge=True)
        doc_id = aid
    else:
        _, ref = _coll(fid, "animais").add(doc)
        doc_id = ref.id
    notify_update(fid, "animais")
    return {"ok": True, "id": doc_id}

@mobile_router.delete("/animais/{aid}")
def remover_animal(aid: str, user=Depends(_get_user)):
    fid = user["fazenda_id"]
    _coll(fid, "animais").document(aid).update({"status": "Vendido"})
    notify_update(fid, "animais")
    return {"ok": True}


# ─────────────────────────────────────────────
# SANITÁRIO (vacinas, exames, protocolos)
# ─────────────────────────────────────────────
_TIPOS_SANITARIO = {"Vacina", "Exame", "Medicamento", "Protocolo"}

class SanitarioInput(BaseModel):
    tipo: str              # Vacina | Exame | Medicamento | Protocolo
    animal: str
    protocolo: str
    data: str
    responsavel: str = ""
    obs: str = ""
    executado: bool = False
    dose: str = ""
    via: str = ""

    @field_validator("tipo")
    @classmethod
    def tipo_valido(cls, v: str) -> str:
        if v not in _TIPOS_SANITARIO:
            raise ValueError(f"tipo deve ser: {', '.join(_TIPOS_SANITARIO)}")
        return v

    @field_validator("data")
    @classmethod
    def data_formato(cls, v: str) -> str:
        try:
            datetime.date.fromisoformat(v)
        except (ValueError, TypeError):
            raise ValueError("Campo 'data' deve estar no formato YYYY-MM-DD")
        return v

    @field_validator("animal", "protocolo")
    @classmethod
    def campo_nao_vazio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Campo obrigatório não pode ser vazio")
        return v

@mobile_router.get("/sanitario")
def listar_sanitario(dias: int = 90, user=Depends(_get_user)):
    fid = user["fazenda_id"]
    docs = []
    for d in _coll(fid, "sanitario").stream():
        row = d.to_dict()
        row["id"] = d.id
        docs.append(row)
    return sorted(docs, key=lambda x: x.get("data", ""), reverse=True)

@mobile_router.post("/sanitario")
def registrar_sanitario(body: SanitarioInput, user=Depends(_get_user)):
    fid = user["fazenda_id"]
    doc = body.model_dump()
    doc["registrado_por"] = user.get("nome", "")
    doc["ts"] = datetime.datetime.now().isoformat()
    _, ref = _coll(fid, "sanitario").add(doc)
    notify_update(fid, "sanitario")
    return {"ok": True, "id": ref.id}

@mobile_router.patch("/sanitario/{sid}/executar")
def executar_sanitario(sid: str, user=Depends(_get_user)):
    fid = user["fazenda_id"]
    _coll(fid, "sanitario").document(sid).update({
        "executado": True,
        "executado_em": datetime.datetime.now().isoformat(),
        "executado_por": user.get("nome", ""),
    })
    notify_update(fid, "sanitario")
    return {"ok": True}


# ─────────────────────────────────────────────
# CONFIG DA FAZENDA
# ─────────────────────────────────────────────
@mobile_router.get("/config")
def get_config(user=Depends(_get_user)):
    fid = user["fazenda_id"]
    config = {}
    for d in _coll(fid, "config").stream():
        c = d.to_dict()
        config[c.get("chave", d.id)] = c.get("valor")
    return config

@mobile_router.post("/config")
def salvar_config(body: dict, user=Depends(_get_user)):
    fid = user["fazenda_id"]
    if not body:
        raise HTTPException(status_code=422, detail={"error": "Body não pode ser vazio"})
    _CHAVES_BLOQUEADAS = {"fazenda_id", "owner_uid", "owner_email", "plano"}
    for chave, valor in body.items():
        if str(chave) in _CHAVES_BLOQUEADAS:
            raise HTTPException(status_code=403, detail={"error": f"Chave protegida: {chave}"})
        _coll(fid, "config").document(str(chave)).set({"chave": str(chave), "valor": valor})
    notify_update(fid, "config")
    return {"ok": True}


# ─────────────────────────────────────────────
# RANKING DE RENTABILIDADE POR ANIMAL
# ─────────────────────────────────────────────
@mobile_router.get("/ranking")
def ranking_rentabilidade(dias: int = 30, user=Depends(_get_user)):
    """Ranking de rentabilidade por animal: litros vs custo ração + veterinário."""
    fid = user["fazenda_id"]
    ini = (datetime.date.today() - datetime.timedelta(days=dias)).isoformat()

    config = {}
    for d in _coll(fid, "config").stream():
        c = d.to_dict()
        config[c.get("chave", d.id)] = c.get("valor")
    preco_leite    = float(config.get("preco_leite", 2.50))
    custo_racao_kg = _custo_racao_kg_real(fid)

    prod_docs = [d.to_dict() for d in
                 _coll(fid, "producao")
                 .where(filter=FieldFilter("data", ">=", ini)).stream()]

    san_docs = [d.to_dict() for d in
                _coll(fid, "sanitario")
                .where(filter=FieldFilter("data", ">=", ini)).stream()]

    ranking: dict = {}
    for p in prod_docs:
        nome = p.get("nome_animal") or "Rebanho"
        if nome not in ranking:
            ranking[nome] = {"nome": nome, "litros": 0.0, "racao_kg": 0.0, "custo_vet": 0.0}
        ranking[nome]["litros"]   += float(p.get("leite")  or 0)
        ranking[nome]["racao_kg"] += float(p.get("racao")  or 0)

    for s in san_docs:
        nome = s.get("nome_animal") or s.get("animal") or "Rebanho"
        val  = float(s.get("valor") or 0)
        if nome in ranking:
            ranking[nome]["custo_vet"] += val

    result = []
    for r in ranking.values():
        receita     = r["litros"] * preco_leite
        custo_racao = r["racao_kg"] * custo_racao_kg
        custo_total = custo_racao + r["custo_vet"]
        margem      = receita - custo_total
        custo_litro = custo_total / r["litros"] if r["litros"] > 0 else 0
        result.append({
            "nome":        r["nome"],
            "litros":      round(r["litros"], 1),
            "racao_kg":    round(r["racao_kg"], 1),
            "receita":     round(receita, 2),
            "custo_racao": round(custo_racao, 2),
            "custo_vet":   round(r["custo_vet"], 2),
            "custo_total": round(custo_total, 2),
            "margem":      round(margem, 2),
            "custo_litro": round(custo_litro, 4),
        })

    return {
        "dias":           dias,
        "preco_leite":    preco_leite,
        "custo_racao_kg": round(custo_racao_kg, 2),
        "ranking":        sorted(result, key=lambda x: x["margem"], reverse=True),
    }


# ─────────────────────────────────────────────
# SSE — ATUALIZAÇÕES EM TEMPO REAL
# ─────────────────────────────────────────────
@mobile_router.get("/eventos")
async def eventos_sse(token: str = Query(default="")):
    """Server-Sent Events: notifica o frontend quando o bot salva novos dados.
    O token JWT é passado como query param pois EventSource não suporta headers."""
    user = _get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Token inválido")
    fid = user["fazenda_id"]

    async def generator():
        # Evento inicial de conexão
        yield "data: {\"type\":\"connected\"}\n\n"
        last_ts = _UPDATE_TS.get(fid, {}).get("ts", 0)
        while True:
            await asyncio.sleep(3)
            current = _UPDATE_TS.get(fid, {})
            cur_ts  = current.get("ts", 0)
            if cur_ts > last_ts:
                last_ts = cur_ts
                payload = json.dumps({"type": "update", "colecao": current.get("colecao", "all")})
                yield f"data: {payload}\n\n"
            else:
                # Heartbeat para manter conexão viva
                yield ": keepalive\n\n"

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",   # desabilita buffer do nginx
            "Connection":       "keep-alive",
        },
    )


# ─────────────────────────────────────────────
# LOTES DE RAÇÃO (histórico de preços)
# ─────────────────────────────────────────────
@mobile_router.get("/lotes_racao")
def listar_lotes_racao(user=Depends(_get_user)):
    """Retorna histórico de lotes de ração com variação de preço."""
    fid  = user["fazenda_id"]
    docs = [d.to_dict() for d in _coll(fid, "lotes_racao").stream()]
    docs.sort(key=lambda x: x.get("data", ""), reverse=True)
    resultado = []
    for i, d in enumerate(docs):
        preco_ant = docs[i + 1].get("custo_unit_kg", 0) if i + 1 < len(docs) else None
        preco_atu = float(d.get("custo_unit_kg", 0))
        variacao  = None
        if preco_ant and preco_ant > 0:
            variacao = round((preco_atu - preco_ant) / preco_ant * 100, 1)
        resultado.append({
            "data":          d.get("data"),
            "produto":       d.get("produto"),
            "qtd_kg":        d.get("qtd_original"),
            "custo_unit_kg": preco_atu,
            "custo_total":   d.get("custo_total"),
            "fornecedor":    d.get("fornecedor"),
            "variacao_pct":  variacao,
        })
    return resultado


# ─────────────────────────────────────────────
# CURVA DE LACTAÇÃO POR ANIMAL
# ─────────────────────────────────────────────
import math as _math

def _wood(dim: int, a=20.0, b=0.12, c=0.0035) -> float:
    if dim <= 0: return 0.0
    return a * (dim ** b) * _math.exp(-c * dim)


@mobile_router.get("/lactacao/{nome}")
def curva_lactacao(nome: str, dias: int = 120, user=Depends(_get_user)):
    """Retorna produção real + curva de Wood padrão para um animal.
    Permite plotar curva esperada vs real no frontend."""
    fid  = user["fazenda_id"]
    hoje = datetime.date.today()
    ini  = (hoje - datetime.timedelta(days=dias)).isoformat()

    # Busca animal para obter dt_parto
    animais = [d.to_dict() for d in _coll(fid, "animais").stream()
               if d.to_dict().get("nome") == nome]
    animal  = animais[0] if animais else {}
    dt_parto_raw = animal.get("dt_parto") or animal.get("parto")
    dt_parto = None
    if dt_parto_raw:
        try:
            dt_parto = datetime.datetime.strptime(str(dt_parto_raw)[:10], "%Y-%m-%d").date()
        except Exception:
            pass

    # Produção real por dia
    docs = [d.to_dict() for d in
            _coll(fid, "producao")
            .where(filter=FieldFilter("data", ">=", ini)).stream()]
    filtrado = [d for d in docs if d.get("nome_animal") == nome]
    por_dia  = {}
    for p in filtrado:
        d_  = p.get("data", "")
        por_dia[d_] = por_dia.get(d_, 0) + float(p.get("leite") or 0)
    real_sorted = sorted(por_dia.items())

    # Fator de escala: ajusta curva ao pico real
    fator = 1.0
    if real_sorted:
        pico_real = max(v for _, v in real_sorted)
        pico_wood = _wood(_math.floor(0.12 / 0.0035))  # ~34
        if pico_wood > 0 and pico_real > 0:
            fator = pico_real / pico_wood

    # Constrói série com curva e real
    series = []
    for data_str, litros_real in real_sorted:
        dim = None
        esperado = None
        if dt_parto:
            try:
                d_obj = datetime.datetime.strptime(data_str, "%Y-%m-%d").date()
                dim   = (d_obj - dt_parto).days
                if dim > 0:
                    esperado = round(_wood(dim) * fator, 1)
            except Exception:
                pass
        series.append({
            "data":    data_str,
            "dia":     data_str[5:],
            "litros":  round(litros_real, 1),
            "esperado": esperado,
            "dim":     dim,
        })

    dim_atual = (hoje - dt_parto).days if dt_parto else None
    media_7d  = None
    if real_sorted:
        ultimos  = [v for _, v in real_sorted[-7:]]
        media_7d = round(sum(ultimos) / len(ultimos), 1) if ultimos else None

    queda_pct = None
    if dim_atual and media_7d and dim_atual > 60:
        esperado_atual = _wood(dim_atual) * fator
        if esperado_atual > 0:
            queda_pct = round((1 - media_7d / esperado_atual) * 100, 1)

    return {
        "animal":     nome,
        "dt_parto":   str(dt_parto) if dt_parto else None,
        "dim_atual":  dim_atual,
        "media_7d":   media_7d,
        "queda_pct":  queda_pct,
        "fator_escala": round(fator, 3),
        "serie":      series,
    }


# ─────────────────────────────────────────────
# AGENDA DOS PRÓXIMOS DIAS
# ─────────────────────────────────────────────
@mobile_router.get("/agenda")
def agenda_semana(dias: int = 7, user=Depends(_get_user)):
    """Retorna tarefas dos próximos N dias agrupadas por data."""
    fid  = user["fazenda_id"]
    hoje = datetime.date.today()

    GESTACAO   = 283
    DIAS_SECAR = 60
    DIAS_DIAGN = 30
    DIAS_PVE   = 45
    DIAS_PT    = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

    agenda: dict = {str(hoje + datetime.timedelta(days=i)): [] for i in range(dias)}

    def _pd(s):
        try:
            return datetime.datetime.strptime(str(s)[:10], "%Y-%m-%d").date() if s else None
        except Exception:
            return None

    try:
        animais = [d.to_dict() for d in _coll(fid, "animais").stream()]
        for a in animais:
            nome    = a.get("nome", "?")
            status  = a.get("status", "")
            d_insem = _pd(a.get("dt_insem"))
            d_parto = _pd(a.get("dt_parto"))
            if status != "Lactação":
                continue
            if d_insem and not a.get("prenhez"):
                data_d = d_insem + datetime.timedelta(days=DIAS_DIAGN)
                if str(data_d) in agenda:
                    agenda[str(data_d)].append({"tipo": "diagnostico", "animal": nome, "texto": f"Diagnóstico prenhez: {nome}"})
            if not d_insem and d_parto:
                data_p = d_parto + datetime.timedelta(days=DIAS_PVE + 1)
                if str(data_p) in agenda:
                    agenda[str(data_p)].append({"tipo": "inseminacao", "animal": nome, "texto": f"Inseminar (atrasada): {nome}"})
            if a.get("prenhez") and d_insem:
                prev  = d_insem + datetime.timedelta(days=GESTACAO)
                d_sec = prev - datetime.timedelta(days=DIAS_SECAR)
                if str(d_sec) in agenda:
                    agenda[str(d_sec)].append({"tipo": "secar", "animal": nome, "texto": f"Secar hoje: {nome}"})
                for dd in range(1, 8):
                    data_a = prev - datetime.timedelta(days=dd)
                    if str(data_a) in agenda:
                        agenda[str(data_a)].append({"tipo": "parto", "animal": nome, "texto": f"Parto em {dd}d: {nome}"})
    except Exception:
        logger.warning("Erro ao calcular agenda de animais para fazenda %s", fid, exc_info=True)

    try:
        protos = [d.to_dict() for d in _coll(fid, "protocolos_sanitarios").stream()
                  if d.to_dict().get("ativo", True)]
        for p in protos:
            prox = _pd(p.get("proxima_data"))
            if prox and str(prox) in agenda:
                agenda[str(prox)].append({"tipo": "sanitario", "animal": p.get("animal",""), "texto": f"Protocolo: {p.get('nome','')}"})
    except Exception:
        logger.warning("Erro ao calcular agenda de protocolos para fazenda %s", fid, exc_info=True)

    resultado = []
    for i in range(dias):
        data = hoje + datetime.timedelta(days=i)
        resultado.append({
            "data":     str(data),
            "dia_semana": DIAS_PT[data.weekday()],
            "tarefas":  agenda.get(str(data), []),
        })
    return resultado


# ─────────────────────────────────────────────
# PRODUÇÃO — por animal (relatório)
# ─────────────────────────────────────────────
@mobile_router.get("/producao/animal/{nome}")
def producao_por_animal(nome: str, dias: int = 30, user=Depends(_get_user)):
    fid = user["fazenda_id"]
    ini = (datetime.date.today() - datetime.timedelta(days=dias)).isoformat()
    # Filtra por data primeiro (índice simples), depois filtra por animal em Python
    # evita índice composto no Firestore
    docs = [d.to_dict() for d in
            _coll(fid, "producao")
            .where(filter=FieldFilter("data", ">=", ini))
            .stream()]
    filtrado = [d for d in docs if d.get("nome_animal") == nome]
    return sorted(filtrado, key=lambda x: x.get("data", ""))


# ─────────────────────────────────────────────
# FINANCEIRO — resumo por categoria
# ─────────────────────────────────────────────
@mobile_router.get("/financeiro/resumo")
def resumo_financeiro(dias: int = 30, user=Depends(_get_user)):
    fid = user["fazenda_id"]
    ini = (datetime.date.today() - datetime.timedelta(days=dias)).isoformat()
    docs = [d.to_dict() for d in
            _coll(fid, "financeiro").where(filter=FieldFilter("data", ">=", ini)).stream()]
    resumo = {}
    for d in docs:
        cat = d.get("categoria") or d.get("cat", "Outros")
        if cat not in resumo:
            resumo[cat] = {"cat": cat, "categoria": cat, "total": 0, "qtd": 0}
        resumo[cat]["total"] += d.get("valor", 0)
        resumo[cat]["qtd"]   += 1
    return sorted(resumo.values(), key=lambda x: x["total"], reverse=True)


# CUSTO POR LITRO (KPI mensal)
# ─────────────────────────────────────────────
@mobile_router.get("/custo_litro")
def custo_por_litro(user=Depends(_get_user)):
    """Custo de produção por litro da fazenda no mês atual.

    Retorna:
        custo_litro  — total de despesas / litros produzidos (R$/L)
        preco_litro  — receita total / litros produzidos (R$/L médio vendas)
        margem_litro — preco_litro - custo_litro
        total_desp   — soma de todas as despesas do mês
        total_rec    — soma de todas as receitas do mês
        total_prod   — litros produzidos no mês
        breakdown    — despesas agrupadas por categoria (para gráfico de pizza)
    """
    fid     = user["fazenda_id"]
    hoje    = datetime.date.today()
    ini_mes = hoje.replace(day=1).isoformat()

    fin_docs  = [d.to_dict() for d in
                 _coll(fid, "financeiro").where(filter=FieldFilter("data", ">=", ini_mes)).stream()]
    prod_docs = [d.to_dict() for d in
                 _coll(fid, "producao").where(filter=FieldFilter("data", ">=", ini_mes)).stream()]

    total_prod = sum(p.get("leite", 0) for p in prod_docs)
    total_rec  = sum(f.get("valor", 0) for f in fin_docs if "Venda" in (f.get("cat") or f.get("categoria", "")))
    total_desp = sum(f.get("valor", 0) for f in fin_docs if "Venda" not in (f.get("cat") or f.get("categoria", "")))

    custo_litro  = round(total_desp / total_prod, 4) if total_prod > 0 else 0.0
    preco_litro  = round(total_rec  / total_prod, 4) if total_prod > 0 else 0.0
    margem_litro = round(preco_litro - custo_litro, 4)

    # Breakdown por categoria para gráfico
    breakdown: dict = {}
    for f in fin_docs:
        if "Venda" in (f.get("cat") or f.get("categoria", "")):
            continue
        cat = f.get("cat") or f.get("categoria") or "Outros"
        breakdown[cat] = breakdown.get(cat, 0) + f.get("valor", 0)

    return {
        "custo_litro":  custo_litro,
        "preco_litro":  preco_litro,
        "margem_litro": margem_litro,
        "total_desp":   round(total_desp, 2),
        "total_rec":    round(total_rec,  2),
        "total_prod":   round(total_prod, 1),
        "mes":          ini_mes,
        "breakdown":    [{"cat": k, "valor": round(v, 2)}
                         for k, v in sorted(breakdown.items(), key=lambda x: -x[1])],
    }


# ─────────────────────────────────────────────
# RELATÓRIO MENSAL EM PDF — design profissional
# ─────────────────────────────────────────────
@mobile_router.get("/relatorio_mensal")
def relatorio_mensal(user=Depends(_get_user), mes: str = Query(default="")):
    """Gera PDF com relatorio mensal premium: KPI cards, barras visuais, design profissional."""
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos, Align
    from fastapi.responses import Response as _Resp

    fid  = user["fazenda_id"]
    hoje = datetime.date.today()

    if mes:
        try:
            ano, m = int(mes[:4]), int(mes[5:7])
            if not (1 <= m <= 12):
                raise ValueError("Mês fora do intervalo")
        except (ValueError, IndexError):
            raise HTTPException(status_code=422, detail={"error": "Parâmetro 'mes' deve estar no formato YYYY-MM"})
    else:
        ano, m = hoje.year, hoje.month

    ini_mes = f"{ano:04d}-{m:02d}-01"
    fim_mes = f"{ano+1:04d}-01-01" if m == 12 else f"{ano:04d}-{m+1:02d}-01"

    import calendar
    meses_pt = ["","Janeiro","Fevereiro","Marco","Abril","Maio","Junho",
                 "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
    mes_label = f"{meses_pt[m]} / {ano}"

    # ── Dados ──────────────────────────────────────────────────
    db = _db()
    # Nome da fazenda: config > fazendas doc > fid
    nome_fazenda = fid
    cfg_doc = _coll(fid, "config").document("principal").get()
    if cfg_doc.exists:
        nome_fazenda = cfg_doc.to_dict().get("nome_fazenda") or fid
    else:
        faz_doc = db.collection("fazendas").document(fid).get()
        if faz_doc.exists:
            nome_fazenda = faz_doc.to_dict().get("nome") or fid

    fin_docs  = [d.to_dict() for d in _coll(fid,"financeiro")
                 .where(filter=FieldFilter("data",">=",ini_mes))
                 .where(filter=FieldFilter("data","<",fim_mes)).stream()]
    prod_docs = [d.to_dict() for d in _coll(fid,"producao")
                 .where(filter=FieldFilter("data",">=",ini_mes))
                 .where(filter=FieldFilter("data","<",fim_mes)).stream()]
    animais   = [d.to_dict() for d in _coll(fid,"animais").stream()]

    total_prod   = sum(p.get("leite",0) for p in prod_docs)
    dias_no_mes  = calendar.monthrange(ano, m)[1]
    media_dia    = round(total_prod / dias_no_mes, 1) if dias_no_mes else 0
    vacas_lact   = len([a for a in animais if a.get("status","") in ("Lactacao","Lactação")])
    total_rec    = sum(f.get("valor",0) for f in fin_docs if "Venda" in (f.get("cat") or f.get("categoria","")))
    total_desp   = sum(f.get("valor",0) for f in fin_docs if "Venda" not in (f.get("cat") or f.get("categoria","")))
    saldo        = total_rec - total_desp
    custo_litro  = round(total_desp / total_prod, 2) if total_prod > 0 else 0.0
    preco_litro  = round(total_rec  / total_prod, 2) if total_prod > 0 else 0.0
    margem_litro = round(preco_litro - custo_litro, 2)

    por_animal: dict = {}
    for p in prod_docs:
        n = p.get("nome_animal") or p.get("id_animal") or "?"
        por_animal[n] = por_animal.get(n, 0) + p.get("leite", 0)
    top_animais = sorted(por_animal.items(), key=lambda x: -x[1])[:8]

    por_cat: dict = {}
    for f in fin_docs:
        if "Venda" in (f.get("cat") or f.get("categoria","")): continue
        cat = f.get("cat") or f.get("categoria") or "Outros"
        por_cat[cat] = por_cat.get(cat, 0) + f.get("valor", 0)
    desp_cats = sorted(por_cat.items(), key=lambda x: -x[1])[:8]

    # ── Design tokens ──────────────────────────────────────────
    C_GREEN_DARK  = (22,  101, 52)
    C_GREEN_MED   = (34,  139, 70)
    C_GREEN_LIGHT = (220, 242, 228)
    C_GREEN_PALE  = (240, 253, 244)
    C_BLUE        = (37,  99,  235)
    C_BLUE_LIGHT  = (219, 234, 254)
    C_RED         = (185, 28,  28)
    C_RED_LIGHT   = (254, 226, 226)
    C_AMBER       = (180, 83,  9)
    C_AMBER_LIGHT = (254, 243, 199)
    C_GRAY_900    = (17,  24,  39)
    C_GRAY_600    = (75,  85,  99)
    C_GRAY_400    = (156, 163, 175)
    C_GRAY_100    = (243, 244, 246)
    C_WHITE       = (255, 255, 255)
    C_BORDER      = (209, 213, 219)

    # margens e largura útil
    ML = 12   # margin left
    MR = 12   # margin right
    W  = 210 - ML - MR   # 186mm útil

    def _s(t: str) -> str:
        return (str(t)
                .replace("\u2014","-").replace("\u2013","-")
                .replace("\u2019","'").replace("\u2018","'")
                .replace("\u201c",'"').replace("\u201d",'"')
                .encode("latin-1", errors="replace").decode("latin-1"))

    def brl(v: float, sign=False) -> str:
        s = f"{abs(v):,.2f}".replace(",","X").replace(".",",").replace("X",".")
        prefix = "R$ " if not sign else ("+ R$ " if v >= 0 else "- R$ ")
        return _s(prefix + s)

    # ── Classe PDF ─────────────────────────────────────────────
    class PDF(FPDF):
        def header(self):
            # Fundo escuro header
            self.set_fill_color(*C_GREEN_DARK)
            self.rect(0, 0, 210, 32, style="F")
            # Faixa accent
            self.set_fill_color(*C_GREEN_MED)
            self.rect(0, 32, 210, 2, style="F")
            # Logo / produto
            self.set_xy(ML, 6)
            self.set_font("Helvetica", "B", 18)
            self.set_text_color(*C_WHITE)
            self.cell(90, 9, "MilkShow", new_x=XPos.RIGHT, new_y=YPos.TOP)
            # Mes/ano alinhado à direita
            self.set_font("Helvetica", "B", 11)
            self.set_text_color(180, 230, 190)
            self.set_xy(ML + 90, 7)
            self.cell(W - 90, 8, _s(mes_label), align="R",
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            # Nome da fazenda
            self.set_xy(ML, 17)
            self.set_font("Helvetica", "", 9)
            self.set_text_color(180, 220, 190)
            self.cell(W/2, 6, _s(nome_fazenda),
                      new_x=XPos.RIGHT, new_y=YPos.TOP)
            # Gerado em - direita
            self.set_font("Helvetica", "", 8)
            self.set_text_color(150, 200, 160)
            self.set_xy(ML + W/2, 18)
            self.cell(W/2, 5, f"Gerado em {hoje.strftime('%d/%m/%Y')}", align="R",
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_text_color(*C_GRAY_900)
            self.set_y(38)

        def footer(self):
            self.set_y(-13)
            self.set_fill_color(*C_GRAY_100)
            self.rect(0, self.get_y(), 210, 13, style="F")
            self.set_font("Helvetica", "", 8)
            self.set_text_color(*C_GRAY_400)
            self.cell(0, 13,
                      _s(f"MilkShow  |  {nome_fazenda}  |  {mes_label}  |  Pag. {self.page_no()}"),
                      align="C")

    pdf = PDF()
    pdf.set_margins(ML, 10, MR)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # ── helpers de layout ──────────────────────────────────────
    def section_title(title: str, icon: str = ""):
        pdf.ln(4)
        y = pdf.get_y()
        pdf.set_fill_color(*C_GREEN_LIGHT)
        pdf.rect(ML, y, W, 8, style="F")
        # linha esquerda accent
        pdf.set_fill_color(*C_GREEN_MED)
        pdf.rect(ML, y, 3, 8, style="F")
        pdf.set_xy(ML + 5, y)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*C_GREEN_DARK)
        txt = _s(f"{icon}  {title}" if icon else title)
        pdf.cell(W - 5, 8, txt, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(*C_GRAY_900)
        pdf.ln(2)

    def kpi_card(x, y, w, h, label, value, unit="", bg=C_WHITE, val_color=None):
        """Desenha um card KPI com borda."""
        pdf.set_fill_color(*bg)
        pdf.set_draw_color(*C_BORDER)
        pdf.rect(x, y, w, h, style="FD")
        # label topo
        pdf.set_xy(x + 2, y + 2)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*C_GRAY_400)
        pdf.cell(w - 4, 4, _s(label.upper()), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        # valor grande
        pdf.set_xy(x + 2, y + 7)
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(*(val_color or C_GRAY_900))
        pdf.cell(w - 4, 8, _s(str(value)), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        # unidade
        if unit:
            pdf.set_xy(x + 2, y + h - 5)
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(*C_GRAY_400)
            pdf.cell(w - 4, 4, _s(unit))
        pdf.set_text_color(*C_GRAY_900)
        pdf.set_draw_color(0, 0, 0)

    def bar_row(label, value, max_val, suffix="", color=C_GREEN_MED, show_val=""):
        """Linha com barra horizontal proporcional."""
        y = pdf.get_y()
        if y > 265:
            pdf.add_page()
            y = pdf.get_y()
        BAR_X   = ML + 38
        BAR_W   = 95
        bar_pct = min(value / max_val, 1.0) if max_val > 0 else 0
        # Label
        pdf.set_xy(ML, y)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*C_GRAY_600)
        pdf.cell(36, 6, _s(label[:18]), new_x=XPos.RIGHT, new_y=YPos.TOP)
        # Track (fundo cinza)
        pdf.set_fill_color(*C_GRAY_100)
        pdf.rect(BAR_X, y + 1.5, BAR_W, 3.5, style="F")
        # Bar preenchida
        if bar_pct > 0:
            pdf.set_fill_color(*color)
            pdf.rect(BAR_X, y + 1.5, BAR_W * bar_pct, 3.5, style="F")
        # Percentual
        pdf.set_xy(BAR_X + BAR_W + 2, y)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*C_GRAY_900)
        pdf.cell(18, 6, _s(suffix), new_x=XPos.RIGHT, new_y=YPos.TOP)
        # Valor
        pdf.set_xy(BAR_X + BAR_W + 22, y)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*C_GRAY_600)
        pdf.cell(W - BAR_W - 60, 6, _s(show_val), align="R",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(*C_GRAY_900)

    # ══ 1. KPI CARDS — Produção ═══════════════════════════════
    section_title("PRODUCAO DE LEITE", "")
    y0  = pdf.get_y()
    gap = 3
    cw  = (W - gap * 3) / 4

    kpi_card(ML,              y0, cw, 22, "Total do Mes",
             f"{total_prod:,.0f}".replace(",","."), "litros",
             bg=C_GREEN_PALE, val_color=C_GREEN_DARK)
    kpi_card(ML + cw + gap,   y0, cw, 22, "Media Diaria",
             f"{media_dia:.1f}", "L / dia",
             bg=C_BLUE_LIGHT, val_color=C_BLUE)
    kpi_card(ML + (cw+gap)*2, y0, cw, 22, "Vacas em Lactacao",
             str(vacas_lact), "animais",
             bg=C_GREEN_PALE, val_color=C_GREEN_MED)
    kpi_card(ML + (cw+gap)*3, y0, cw, 22, "Registros",
             str(len(prod_docs)), "lancamentos",
             bg=C_GRAY_100, val_color=C_GRAY_600)
    pdf.set_y(y0 + 26)

    # ══ 2. BARRAS — Top Animais ════════════════════════════════
    if top_animais:
        section_title("TOP ANIMAIS - PRODUCAO DO MES", "")
        max_anim = top_animais[0][1] if top_animais else 1
        for nome_a, litros in top_animais:
            pct = litros / total_prod * 100 if total_prod > 0 else 0
            bar_row(nome_a, litros, max_anim,
                    suffix=f"{pct:.1f}%",
                    show_val=f"{litros:,.0f} L".replace(",","."),
                    color=C_GREEN_MED)

    # ══ 3. KPI CARDS — Financeiro ══════════════════════════════
    section_title("RESUMO FINANCEIRO", "")
    y1  = pdf.get_y()
    fw  = (W - gap * 2) / 3
    bg_saldo  = C_GREEN_PALE  if saldo >= 0 else C_RED_LIGHT
    cor_saldo = C_GREEN_DARK  if saldo >= 0 else C_RED

    kpi_card(ML,           y1, fw, 22, "Receitas (Venda de Leite)",
             brl(total_rec), "", bg=C_GREEN_PALE, val_color=C_GREEN_DARK)
    kpi_card(ML + fw+gap,  y1, fw, 22, "Despesas Totais",
             brl(total_desp), "", bg=C_RED_LIGHT, val_color=C_RED)
    kpi_card(ML + (fw+gap)*2, y1, fw, 22, "Saldo do Mes",
             brl(saldo), "", bg=bg_saldo, val_color=cor_saldo)
    pdf.set_y(y1 + 26)

    # ══ 4. BARRAS — Despesas por Categoria ════════════════════
    if desp_cats:
        section_title("DESPESAS POR CATEGORIA", "")
        max_cat = desp_cats[0][1] if desp_cats else 1
        for cat, val in desp_cats:
            pct = val / total_desp * 100 if total_desp > 0 else 0
            bar_row(cat, val, max_cat,
                    suffix=f"{pct:.1f}%",
                    show_val=brl(val),
                    color=C_RED)

    # ══ 5. KPI CARDS — Custo por Litro ════════════════════════
    section_title("CUSTO POR LITRO - KPI MENSAL", "")
    y2   = pdf.get_y()
    tw   = (W - gap * 2) / 3
    bg_m = C_GREEN_PALE if margem_litro >= 0 else C_AMBER_LIGHT
    cm   = C_GREEN_DARK  if margem_litro >= 0 else C_AMBER

    kpi_card(ML,           y2, tw, 22, "Custo / Litro",
             f"R$ {custo_litro:.2f}", "despesas / producao",
             bg=C_RED_LIGHT, val_color=C_RED)
    kpi_card(ML + tw+gap,  y2, tw, 22, "Preco Recebido / Litro",
             f"R$ {preco_litro:.2f}", "receita / producao",
             bg=C_BLUE_LIGHT, val_color=C_BLUE)
    kpi_card(ML + (tw+gap)*2, y2, tw, 22, "Margem / Litro",
             f"R$ {margem_litro:+.2f}", "preco - custo",
             bg=bg_m, val_color=cm)
    pdf.set_y(y2 + 26)

    # ══ 6. ANALISE TEXTUAL ════════════════════════════════════
    pdf.ln(4)
    bg_box   = C_GREEN_PALE if margem_litro >= 0 else C_AMBER_LIGHT
    cor_box  = C_GREEN_DARK  if margem_litro >= 0 else C_AMBER
    icon_txt = "Resultado positivo:" if margem_litro >= 0 else "Atencao:"
    if margem_litro >= 0:
        analise = (f"Margem de R$ {margem_litro:.2f}/L. "
                   f"A cada 1.000 litros, a fazenda gerou R$ {margem_litro*1000:.2f} de lucro.")
    else:
        analise = (f"Margem negativa de R$ {margem_litro:.2f}/L. "
                   f"As despesas superaram as receitas em R$ {abs(saldo):.2f} no mes. "
                   f"Revise as categorias de maior impacto.")

    ya = pdf.get_y()
    pdf.set_fill_color(*bg_box)
    pdf.set_draw_color(*cor_box)
    pdf.rect(ML, ya, W, 14, style="FD")
    pdf.set_fill_color(*cor_box)
    pdf.rect(ML, ya, 3, 14, style="F")
    pdf.set_xy(ML + 6, ya + 2)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*cor_box)
    pdf.cell(30, 5, _s(icon_txt), new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*C_GRAY_600)
    pdf.set_xy(ML + 6 + 31, ya + 2)
    pdf.multi_cell(W - 40, 5, _s(analise))
    pdf.set_draw_color(0, 0, 0)
    pdf.set_text_color(*C_GRAY_900)

    # Gera bytes
    pdf_bytes = pdf.output()
    filename  = _s(f"MilkShow_{nome_fazenda.replace(' ','_')}_{ano}{m:02d}.pdf")
    return _Resp(
        content=bytes(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─────────────────────────────────────────────
# NUTRIÇÃO — Motor Nutricional
# ─────────────────────────────────────────────
class RacaoInput(BaseModel):
    ingredientes: list  # [{"nome": str, "kg": float}]

    @field_validator("ingredientes")
    @classmethod
    def ingredientes_nao_vazio(cls, v: list) -> list:
        if not v:
            raise ValueError("Lista de ingredientes não pode ser vazia")
        return v

@mobile_router.get("/nutricao/insumos")
def listar_insumos(user=Depends(_get_user)):
    """Retorna a lista completa de insumos agrupados por categoria."""
    from nutricao import listar_insumos_por_categoria
    return listar_insumos_por_categoria()

@mobile_router.post("/nutricao/calcular")
def calcular_racao(body: RacaoInput, user=Depends(_get_user)):
    """Calcula a tabela nutricional de uma ração pela média ponderada."""
    from nutricao import calcular_racao as _calc
    return _calc(body.ingredientes)

@mobile_router.get("/nutricao/buscar")
def buscar_insumo(termo: str, user=Depends(_get_user)):
    """Desambiguação: retorna os insumos que correspondem ao termo."""
    from nutricao import buscar_insumo as _buscar
    return _buscar(termo)

@mobile_router.get("/nutricao/racoes")
def listar_racoes_salvas(user=Depends(_get_user)):
    """Retorna as fórmulas de ração salvas da fazenda."""
    fid  = user["fazenda_id"]
    docs = [{"id": d.id, **d.to_dict()}
            for d in _coll(fid, "racoes").stream()]
    return sorted(docs, key=lambda x: x.get("criado_em", ""), reverse=True)

@mobile_router.post("/nutricao/racoes")
def salvar_racao(body: dict, user=Depends(_get_user)):
    """Salva uma fórmula de ração com seus nutrientes calculados."""
    from nutricao import calcular_racao as _calc
    fid  = user["fazenda_id"]
    ingredientes = body.get("ingredientes", [])
    if not ingredientes or not isinstance(ingredientes, list):
        raise HTTPException(status_code=422, detail={"error": "Campo 'ingredientes' é obrigatório e deve ser uma lista"})
    nome  = (body.get("nome") or "Ração sem nome").strip() or "Ração sem nome"
    calc  = _calc(ingredientes)
    doc   = {
        "nome":        nome,
        "ingredientes": ingredientes,
        "nutrientes":  calc.get("nutrientes", {}),
        "nutrientes_ms": calc.get("nutrientes_ms", {}),
        "total_kg":    calc.get("total_kg", 0),
        "criado_em":   datetime.datetime.now().isoformat(),
        "criado_por":  user.get("nome", ""),
    }
    _, ref = _coll(fid, "racoes").add(doc)
    notify_update(fid, "nutricao")
    return {"id": ref.id, **doc}

@mobile_router.delete("/nutricao/racoes/{racao_id}")
def deletar_racao(racao_id: str, user=Depends(_get_user)):
    fid = user["fazenda_id"]
    _coll(fid, "racoes").document(racao_id).delete()
    return {"ok": True}


# ─────────────────────────────────────────────
# RANKINGS AVANÇADOS (3 rankings)
# ─────────────────────────────────────────────
@mobile_router.get("/rankings")
def rankings_avancados(dias: int = 30, user=Depends(_get_user)):
    """Retorna 3 rankings: produção, rentabilidade e alerta de descarte."""
    fid = user["fazenda_id"]
    ini = (datetime.date.today() - datetime.timedelta(days=dias)).isoformat()

    config = {}
    for d in _coll(fid, "config").stream():
        c = d.to_dict()
        config[c.get("chave", d.id)] = c.get("valor")

    preco_leite    = float(config.get("preco_leite", 2.50))
    custo_racao_kg = _custo_racao_kg_real(fid)

    # Coleta produção e sanitário
    prod_docs = [d.to_dict() for d in
                 _coll(fid, "producao")
                 .where(filter=FieldFilter("data", ">=", ini)).stream()]
    san_docs  = [d.to_dict() for d in
                 _coll(fid, "sanitario")
                 .where(filter=FieldFilter("data", ">=", ini)).stream()]

    # Agrega por animal
    por_animal: dict = {}
    for p in prod_docs:
        nome = p.get("nome_animal") or "Rebanho"
        if nome not in por_animal:
            por_animal[nome] = {"litros": 0.0, "racao_kg": 0.0, "custo_vet": 0.0, "registros": 0}
        por_animal[nome]["litros"]    += float(p.get("leite", 0) or 0)
        por_animal[nome]["racao_kg"]  += float(p.get("racao", 0) or 0)
        por_animal[nome]["registros"] += 1
    for s in san_docs:
        nome = s.get("nome_animal") or s.get("animal") or "Rebanho"
        if nome in por_animal:
            por_animal[nome]["custo_vet"] += float(s.get("valor", 0) or 0)

    lista = []
    for nome, d in por_animal.items():
        litros = d["litros"]
        if litros <= 0:
            continue
        receita     = litros * preco_leite
        custo_racao = d["racao_kg"] * custo_racao_kg
        custo_total = custo_racao + d["custo_vet"]
        lucro       = receita - custo_total
        custo_litro = custo_total / litros if litros > 0 else 0
        margem_pct  = (lucro / receita * 100) if receita > 0 else 0
        media_dia   = litros / dias

        lista.append({
            "nome":        nome,
            "litros":      round(litros, 1),
            "media_dia":   round(media_dia, 1),
            "racao_kg":    round(d["racao_kg"], 1),
            "receita":     round(receita, 2),
            "custo_racao": round(custo_racao, 2),
            "custo_vet":   round(d["custo_vet"], 2),
            "custo_total": round(custo_total, 2),
            "lucro":       round(lucro, 2),
            "custo_litro": round(custo_litro, 3),
            "margem_pct":  round(margem_pct, 1),
        })

    return {
        "dias":             dias,
        "preco_leite":      preco_leite,
        "custo_racao_kg":   round(custo_racao_kg, 2),
        "total_animais":    len(lista),
        "producao":         sorted(lista, key=lambda x: x["litros"], reverse=True),
        "rentabilidade":    sorted(lista, key=lambda x: x["custo_litro"]),
        "alerta_descarte":  sorted(lista, key=lambda x: x["margem_pct"]),
    }

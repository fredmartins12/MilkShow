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
import datetime
import base64
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

mobile_router = APIRouter(prefix="/api/v1", tags=["mobile"])

# ─────────────────────────────────────────────
# JWT simples (sem dependência extra)
# ─────────────────────────────────────────────
_SECRET = os.environ.get("BOT_ADMIN_TOKEN", "milkshow_secret_2024")

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
        if payload.get("exp", 0) < datetime.datetime.utcnow().timestamp():
            return None
        return payload
    except Exception:
        return None


# ─────────────────────────────────────────────
# Firebase helper
# ─────────────────────────────────────────────
def _db():
    if not firebase_admin._apps:
        key_file = os.path.join(os.path.dirname(__file__), "firebase_key.json")
        cred = credentials.Certificate(key_file)
        firebase_admin.initialize_app(cred)
    return firestore.client()

def _coll(fazenda_id: str, nome: str):
    db = _db()
    if fazenda_id == "default":
        return db.collection(nome)
    return db.collection("fazendas").document(fazenda_id).collection(nome)

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

class ProducaoInput(BaseModel):
    data: str
    id_animal: str
    nome_animal: str
    leite: float
    racao: float = 0.0
    turno: str = "manhã"
    obs: str = ""

class FinanceiroInput(BaseModel):
    data: str
    descricao: str
    cat: str
    valor: float
    tipo: str  # "receita" | "despesa"

class EstoqueInput(BaseModel):
    item: str
    qtd: float
    un: str
    custo_unit: float = 0.0


# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────
@mobile_router.post("/auth/login")
def login(body: LoginRequest):
    tel = _normalizar_tel(body.tel)
    db  = _db()

    user_doc = None
    for variante in _variantes_tel(tel):
        doc = db.collection("registros_tel").document(variante).get()
        if doc.exists and doc.to_dict().get("ativo", True):
            user_doc = doc.to_dict()
            break

    if not user_doc:
        raise HTTPException(status_code=404, detail="Número não cadastrado no MilkShow")

    # Verifica PIN (armazenado como hash SHA256)
    pin_hash = hashlib.sha256(body.pin.encode()).hexdigest()
    pin_salvo = user_doc.get("pin_hash", "")

    if not pin_salvo:
        # Primeiro acesso: define o PIN automaticamente
        db.collection("registros_tel").document(tel).set({"pin_hash": pin_hash}, merge=True)
    elif not hmac.compare_digest(pin_hash, pin_salvo):
        raise HTTPException(status_code=401, detail="PIN incorreto")

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
    return {'token': token, 'nome': nome, 'fazenda_id': fazenda_id}


@mobile_router.post("/auth/set-pin")
def set_pin(body: LoginRequest, user=Depends(_get_user)):
    """Troca o PIN do usuário logado."""
    tel = user["tel"]
    pin_hash = hashlib.sha256(body.pin.encode()).hexdigest()
    _db().collection("registros_tel").document(tel).set({"pin_hash": pin_hash}, merge=True)
    return {"ok": True}


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────
@mobile_router.get("/dashboard")
def dashboard(user=Depends(_get_user)):
    fid   = user["fazenda_id"]
    hoje  = datetime.date.today().isoformat()
    ini_m = datetime.date.today().replace(day=1).isoformat()
    ini_7 = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()

    # Produção hoje
    prod_hoje = [d.to_dict() for d in
                 _coll(fid, "producao").where(filter=FieldFilter("data", "==", hoje)).stream()]
    litros_hoje = sum(p.get("leite", 0) for p in prod_hoje)

    # Produção 7 dias
    prod_7d = [d.to_dict() for d in
               _coll(fid, "producao").where(filter=FieldFilter("data", ">=", ini_7)).stream()]
    litros_7d = sum(p.get("leite", 0) for p in prod_7d)

    # Financeiro mês
    fin_mes = [d.to_dict() for d in
               _coll(fid, "financeiro").where(filter=FieldFilter("data", ">=", ini_m)).stream()]
    receitas  = sum(f.get("valor", 0) for f in fin_mes if "Venda" in f.get("cat", ""))
    despesas  = sum(f.get("valor", 0) for f in fin_mes if "Venda" not in f.get("cat", ""))

    # Animais em lactação
    animais = [d.to_dict() for d in _coll(fid, "animais").stream()]
    em_lactacao = [a for a in animais if a.get("status") == "Lactação"]
    ordenhadas_hoje = len({p.get("id_animal") for p in prod_hoje})

    # Config preço leite
    config = {}
    for d in _coll(fid, "config").stream():
        c = d.to_dict()
        config[c.get("chave", d.id)] = c.get("valor")
    preco_leite = float(config.get("preco_leite", 2.50))

    return {
        "hoje": {
            "data":            hoje,
            "litros":          round(litros_hoje, 1),
            "receita_est":     round(litros_hoje * preco_leite, 2),
            "vacas_lact":      len(em_lactacao),
            "vacas_ordenhadas": ordenhadas_hoje,
        },
        "semana": {
            "litros_7d": round(litros_7d, 1),
            "media_dia":  round(litros_7d / 7, 1),
        },
        "mes": {
            "receitas":  round(receitas, 2),
            "despesas":  round(despesas, 2),
            "saldo":     round(receitas - despesas, 2),
        },
        "preco_leite": preco_leite,
    }


# ─────────────────────────────────────────────
# ANIMAIS
# ─────────────────────────────────────────────
@mobile_router.get("/animais")
def listar_animais(user=Depends(_get_user)):
    fid = user["fazenda_id"]
    docs = [d.to_dict() for d in _coll(fid, "animais").stream()]
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
    docs = [d.to_dict() for d in
            _coll(fid, "producao").where(filter=FieldFilter("data", ">=", ini))
            .order_by("data", direction=firestore.Query.DESCENDING).limit(200).stream()]
    return docs

@mobile_router.post("/producao")
def registrar_producao(body: ProducaoInput, user=Depends(_get_user)):
    fid = user["fazenda_id"]
    doc = body.model_dump()
    doc["registrado_por"] = user.get("nome", user["tel"])
    doc["ts"] = datetime.datetime.now().isoformat()
    _coll(fid, "producao").add(doc)
    return {"ok": True}


# ─────────────────────────────────────────────
# FINANCEIRO
# ─────────────────────────────────────────────
@mobile_router.get("/financeiro")
def listar_financeiro(dias: int = 30, user=Depends(_get_user)):
    fid = user["fazenda_id"]
    ini = (datetime.date.today() - datetime.timedelta(days=dias)).isoformat()
    docs = [d.to_dict() for d in
            _coll(fid, "financeiro").where(filter=FieldFilter("data", ">=", ini))
            .order_by("data", direction=firestore.Query.DESCENDING).limit(200).stream()]
    return docs

@mobile_router.post("/financeiro")
def registrar_financeiro(body: FinanceiroInput, user=Depends(_get_user)):
    fid = user["fazenda_id"]
    doc = body.model_dump()
    doc["registrado_por"] = user.get("nome", user["tel"])
    doc["ts"] = datetime.datetime.now().isoformat()
    _coll(fid, "financeiro").add(doc)
    return {"ok": True}


# ─────────────────────────────────────────────
# ESTOQUE
# ─────────────────────────────────────────────
@mobile_router.get("/estoque")
def listar_estoque(user=Depends(_get_user)):
    fid = user["fazenda_id"]
    return [d.to_dict() for d in _coll(fid, "estoque").stream()]

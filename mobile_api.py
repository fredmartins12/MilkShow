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
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

mobile_router = APIRouter(prefix="/api/v1", tags=["mobile"])

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
        if payload.get("exp", 0) < time.time():
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
    descricao: str = ""
    categoria: str = "Outros"
    cat: str = ""          # alias legacy
    valor: float
    tipo: str              # "receita" | "despesa"
    obs: str = ""

class EstoqueInput(BaseModel):
    item: str
    qtd: float
    un: str
    custo_unit: float = 0.0
    categoria: str = "Outros"
    min_alerta: Optional[float] = None


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

    # Produção: busca 14 dias de uma vez para calcular hoje + ontem + semana atual + semana anterior
    prod_14d = [d.to_dict() for d in
                _coll(fid, "producao")
                .where(filter=FieldFilter("data", ">=", ini_14.isoformat())).stream()]

    litros_hoje      = sum(p.get("leite", 0) for p in prod_14d if p.get("data") == hoje.isoformat())
    litros_ontem     = sum(p.get("leite", 0) for p in prod_14d if p.get("data") == ontem.isoformat())
    litros_7d        = sum(p.get("leite", 0) for p in prod_14d if p.get("data", "") >= ini_7.isoformat())
    litros_semana_ant= sum(p.get("leite", 0) for p in prod_14d
                           if ini_14.isoformat() <= p.get("data", "") < ini_7.isoformat())

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
    _coll(fid, "producao").add(doc)
    notify_update(fid, "producao")
    return {"ok": True}

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
    _coll(fid, "financeiro").add(doc)
    notify_update(fid, "financeiro")
    return {"ok": True}

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

@mobile_router.post("/animais")
def adicionar_animal(body: AnimalInput, user=Depends(_get_user)):
    fid = user["fazenda_id"]
    doc = body.model_dump()
    doc["ts"] = datetime.datetime.now().isoformat()
    aid = doc.pop("id", None) or None
    if aid:
        _coll(fid, "animais").document(aid).set(doc, merge=True)
    else:
        _coll(fid, "animais").add(doc)
    notify_update(fid, "animais")
    return {"ok": True}

@mobile_router.delete("/animais/{aid}")
def remover_animal(aid: str, user=Depends(_get_user)):
    fid = user["fazenda_id"]
    _coll(fid, "animais").document(aid).update({"status": "Vendido"})
    notify_update(fid, "animais")
    return {"ok": True}


# ─────────────────────────────────────────────
# SANITÁRIO (vacinas, exames, protocolos)
# ─────────────────────────────────────────────
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
    _coll(fid, "sanitario").add(doc)
    notify_update(fid, "sanitario")
    return {"ok": True}

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
    for chave, valor in body.items():
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
        pass

    try:
        protos = [d.to_dict() for d in _coll(fid, "protocolos_sanitarios").stream()
                  if d.to_dict().get("ativo", True)]
        for p in protos:
            prox = _pd(p.get("proxima_data"))
            if prox and str(prox) in agenda:
                agenda[str(prox)].append({"tipo": "sanitario", "animal": p.get("animal",""), "texto": f"Protocolo: {p.get('nome','')}"})
    except Exception:
        pass

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

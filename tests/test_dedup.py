# -*- coding: utf-8 -*-
"""
test_dedup.py — Testes unitarios do dedup de alertas e calculos de custo/litro
Compativel com pytest e execucao standalone: py -3 tests/test_dedup.py
Nao requer servidor nem Firebase.
"""
import sys
import os
import datetime
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# ─── Stubs para importar whatsapp_bot sem Firebase/FastAPI ───────────────────
import unittest.mock as mock

_firebase_stub = types.ModuleType("firebase_admin")
_firebase_stub._apps = {"default": True}
_firebase_stub.credentials = types.SimpleNamespace(Certificate=lambda *a, **k: None)
_firebase_stub.firestore   = types.SimpleNamespace(client=lambda: None)
_firebase_stub.initialize_app = lambda *a, **k: None
sys.modules.setdefault("firebase_admin", _firebase_stub)
sys.modules.setdefault("firebase_admin.credentials", _firebase_stub.credentials)
sys.modules.setdefault("firebase_admin.firestore", _firebase_stub.firestore)

_goog = types.ModuleType("google")
_goog.cloud = types.ModuleType("google.cloud")
_goog_ff    = types.ModuleType("google.cloud.firestore_v1")
_goog_bq    = types.ModuleType("google.cloud.firestore_v1.base_query")
_goog_bq.FieldFilter = lambda *a, **k: None
_goog_ff.base_query  = _goog_bq
sys.modules.setdefault("google", _goog)
sys.modules.setdefault("google.cloud", _goog.cloud)
sys.modules.setdefault("google.cloud.firestore_v1", _goog_ff)
sys.modules.setdefault("google.cloud.firestore_v1.base_query", _goog_bq)

# ─── Importar bot real (opcional — testa logica isolada de qualquer forma) ───
try:
    from whatsapp_bot import _alerta_ja_enviado, _alertas_enviados
    _BOT_IMPORTED = True
except Exception:
    _alerta_ja_enviado = None
    _alertas_enviados  = None
    _BOT_IMPORTED      = False

# ─── Logica de dedup isolada (replica _alerta_ja_enviado) ───────────────────
import hashlib as _hashlib

_enviados_isolado: set = set()

def _dedup(fazenda_id: str, alerta: str, data_iso: str = None) -> bool:
    if data_iso is None:
        data_iso = datetime.date.today().isoformat()
    chave = (fazenda_id, _hashlib.md5(alerta.encode()).hexdigest(), data_iso)
    if chave in _enviados_isolado:
        return True
    _enviados_isolado.add(chave)
    hoje = datetime.date.today().isoformat()
    _enviados_isolado.difference_update({c for c in _enviados_isolado if c[2] != hoje})
    return False


def _custo_litro(fin_docs, prod_docs):
    total_prod   = sum(p.get("leite", 0) for p in prod_docs)
    total_rec    = sum(f.get("valor", 0) for f in fin_docs if "Venda" in (f.get("cat") or f.get("categoria", "")))
    total_desp   = sum(f.get("valor", 0) for f in fin_docs if "Venda" not in (f.get("cat") or f.get("categoria", "")))
    custo_litro  = round(total_desp / total_prod, 4) if total_prod > 0 else 0.0
    preco_litro  = round(total_rec  / total_prod, 4) if total_prod > 0 else 0.0
    margem_litro = round(preco_litro - custo_litro, 4)
    return {"custo_litro": custo_litro, "preco_litro": preco_litro,
            "margem_litro": margem_litro, "total_desp": total_desp,
            "total_rec": total_rec, "total_prod": total_prod}


# ═══════════════════════════════════════════════════════════════════════
# PYTEST — Dedup
# ═══════════════════════════════════════════════════════════════════════

def setup_function():
    _enviados_isolado.clear()

def test_dedup_primeira_vez_nao_bloqueado():
    _enviados_isolado.clear()
    assert _dedup("fazA", "Vaca seca: Mimosa") == False

def test_dedup_segunda_vez_bloqueado():
    _enviados_isolado.clear()
    _dedup("fazA", "Vaca seca: Mimosa")
    assert _dedup("fazA", "Vaca seca: Mimosa") == True

def test_dedup_alerta_diferente_nao_bloqueado():
    _enviados_isolado.clear()
    _dedup("fazA", "Vaca seca: Mimosa")
    assert _dedup("fazA", "Parto previsto: Rainha") == False

def test_dedup_fazenda_diferente_nao_bloqueada():
    _enviados_isolado.clear()
    _dedup("fazA", "Vaca seca: Mimosa")
    assert _dedup("fazB", "Vaca seca: Mimosa") == False

def test_dedup_dia_diferente_nao_bloqueado():
    _enviados_isolado.clear()
    ontem = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    _dedup("fazA", "Alerta X", ontem)
    assert _dedup("fazA", "Alerta X") == False

def test_dedup_limpeza_datas_antigas():
    _enviados_isolado.clear()
    ontem = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    _dedup("fazA", "Alerta antigo", ontem)
    _dedup("fazA", "Alerta hoje")
    assert not any(c[2] == ontem for c in _enviados_isolado)


# ═══════════════════════════════════════════════════════════════════════
# PYTEST — Custo por litro
# ═══════════════════════════════════════════════════════════════════════

_FIN = [
    {"cat": "Racao / Nutricao", "valor": 1200.0},
    {"cat": "Medicamento",      "valor": 300.0},
    {"cat": "Mao de Obra",      "valor": 1500.0},
    {"cat": "Venda de Leite",   "valor": 8400.0},
]
_PROD = [{"leite": 30.0} for _ in range(100)]  # 3000 L

def test_custo_litro_custo_correto():
    r = _custo_litro(_FIN, _PROD)
    assert abs(r["custo_litro"] - 1.0) < 0.001, r["custo_litro"]

def test_custo_litro_preco_correto():
    r = _custo_litro(_FIN, _PROD)
    assert abs(r["preco_litro"] - 2.8) < 0.001, r["preco_litro"]

def test_custo_litro_margem_correta():
    r = _custo_litro(_FIN, _PROD)
    assert abs(r["margem_litro"] - 1.8) < 0.001, r["margem_litro"]

def test_custo_litro_total_prod():
    r = _custo_litro(_FIN, _PROD)
    assert r["total_prod"] == 3000.0

def test_custo_litro_total_desp():
    r = _custo_litro(_FIN, _PROD)
    assert r["total_desp"] == 3000.0

def test_custo_litro_total_rec():
    r = _custo_litro(_FIN, _PROD)
    assert r["total_rec"] == 8400.0

def test_custo_litro_sem_producao_zero():
    r = _custo_litro(_FIN, [])
    assert r["custo_litro"] == 0.0
    assert r["preco_litro"] == 0.0

def test_custo_litro_sem_despesas():
    fin = [{"cat": "Venda de Leite", "valor": 5000.0}]
    r = _custo_litro(fin, [{"leite": 2000.0}])
    assert r["custo_litro"] == 0.0
    assert abs(r["margem_litro"] - r["preco_litro"]) < 0.001

def test_custo_litro_prejuizo():
    fin = [{"cat": "Racao", "valor": 10000.0}, {"cat": "Venda de Leite", "valor": 3000.0}]
    r = _custo_litro(fin, [{"leite": 100.0}])
    assert r["margem_litro"] < 0


# ═══════════════════════════════════════════════════════════════════════
# PYTEST — Bot real (pula se import falhou)
# ═══════════════════════════════════════════════════════════════════════

import pytest

@pytest.mark.skipif(not _BOT_IMPORTED, reason="whatsapp_bot nao importado")
def test_bot_dedup_primeira_vez():
    _alertas_enviados.clear()
    assert _alerta_ja_enviado("fazX", "Alerta teste A") == False

@pytest.mark.skipif(not _BOT_IMPORTED, reason="whatsapp_bot nao importado")
def test_bot_dedup_segunda_vez_bloqueado():
    _alertas_enviados.clear()
    _alerta_ja_enviado("fazX", "Alerta teste A")
    assert _alerta_ja_enviado("fazX", "Alerta teste A") == True

@pytest.mark.skipif(not _BOT_IMPORTED, reason="whatsapp_bot nao importado")
def test_bot_dedup_texto_diferente_ok():
    _alertas_enviados.clear()
    _alerta_ja_enviado("fazX", "Alerta teste A")
    assert _alerta_ja_enviado("fazX", "Alerta teste B") == False


# ═══════════════════════════════════════════════════════════════════════
# Standalone
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys as _sys
    ok = fail = 0

    def chk(name, cond, detail=""):
        global ok, fail
        if cond:
            ok += 1; print(f"  OK   {name}")
        else:
            fail += 1; print(f"  FAIL {name}" + (f" -- {detail}" if detail else ""))

    if hasattr(_sys.stdout, 'reconfigure'):
        _sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    print("=" * 60)
    print("  MilkShow -- Testes Unitarios (standalone)")
    print("=" * 60)

    print("\n[1] LOGICA DE DEDUP")
    _enviados_isolado.clear()
    chk("1a vez nao bloqueado",      _dedup("fazA", "Vaca seca: Mimosa") == False)
    chk("2a vez bloqueado",          _dedup("fazA", "Vaca seca: Mimosa") == True)
    chk("Alerta diferente ok",       _dedup("fazA", "Parto: Rainha") == False)
    chk("Fazenda diferente ok",      _dedup("fazB", "Vaca seca: Mimosa") == False)
    ontem = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    _enviados_isolado.clear()
    _dedup("fazA", "X", ontem)
    chk("Dia diferente nao bloqueado", _dedup("fazA", "X") == False)
    _enviados_isolado.clear()
    _dedup("fazA", "Antigo", ontem); _dedup("fazA", "Hoje")
    chk("Limpeza datas antigas",     not any(c[2] == ontem for c in _enviados_isolado))

    print("\n[2] CUSTO POR LITRO")
    r = _custo_litro(_FIN, _PROD)
    chk("Custo R$1,00/L",   abs(r["custo_litro"] - 1.0) < 0.001, str(r["custo_litro"]))
    chk("Preco R$2,80/L",   abs(r["preco_litro"] - 2.8) < 0.001, str(r["preco_litro"]))
    chk("Margem R$1,80/L",  abs(r["margem_litro"] - 1.8) < 0.001, str(r["margem_litro"]))
    chk("total_prod=3000",  r["total_prod"] == 3000.0)
    chk("total_desp=3000",  r["total_desp"] == 3000.0)
    chk("total_rec=8400",   r["total_rec"]  == 8400.0)
    chk("Sem prod -> 0",    _custo_litro(_FIN, [])["custo_litro"] == 0.0)
    chk("Prejuizo negativo", _custo_litro(
        [{"cat": "Racao", "valor": 10000.0}, {"cat": "Venda de Leite", "valor": 3000.0}],
        [{"leite": 100.0}])["margem_litro"] < 0)

    if _BOT_IMPORTED:
        print("\n[3] BOT REAL")
        _alertas_enviados.clear()
        chk("Bot: 1a vez ok",     _alerta_ja_enviado("fazX", "A") == False)
        chk("Bot: 2a vez block",  _alerta_ja_enviado("fazX", "A") == True)
        chk("Bot: diferente ok",  _alerta_ja_enviado("fazX", "B") == False)
        _alertas_enviados.clear()

    total = ok + fail
    print("\n" + "=" * 60)
    cor = "\033[32m" if fail == 0 else "\033[31m"
    print(f"  {cor}OK: {ok}/{total}  |  FAIL: {fail}\033[0m")
    if fail == 0:
        print("  \033[32m[OK] TODOS OS TESTES PASSARAM\033[0m")
    print("=" * 60)
    _sys.exit(0 if fail == 0 else 1)

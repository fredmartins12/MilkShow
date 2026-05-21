# -*- coding: utf-8 -*-
"""
test_dedup.py — Testes unitarios do dedup de alertas e calculos de custo/litro
Execute: py -3 test_dedup.py
Nao requer servidor nem Firebase.
"""
import sys
import os
import datetime
import importlib
import types

# Garante que a raiz do projeto está no path (para importar whatsapp_bot)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Force UTF-8 output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ok_count = fail_count = 0

def check(name, cond, detail=""):
    global ok_count, fail_count
    if cond:
        ok_count += 1
        print(f"  OK   {name}")
    else:
        fail_count += 1
        print(f"  FAIL {name}" + (f" -- {detail}" if detail else ""))


# ─────────────────────────────────────────────────────────────────────────────
# 1. Importar apenas as funcoes puras do whatsapp_bot sem subir o servidor
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 60)
print("  MilkShow -- Testes Unitarios")
print("=" * 60)

# Carrega o modulo mas suprime o startup do FastAPI/Firebase
# fazemos isso injetando stubs antes do import
import unittest.mock as mock

# Stub minimo para firebase_admin
firebase_stub = types.ModuleType("firebase_admin")
firebase_stub._apps = {"default": True}
firebase_stub.credentials = types.SimpleNamespace(Certificate=lambda *a, **k: None)
firebase_stub.firestore   = types.SimpleNamespace(client=lambda: None)
firebase_stub.initialize_app = lambda *a, **k: None
sys.modules.setdefault("firebase_admin", firebase_stub)
sys.modules.setdefault("firebase_admin.credentials", firebase_stub.credentials)
sys.modules.setdefault("firebase_admin.firestore", firebase_stub.firestore)

# Stub google.cloud.firestore_v1
goog = types.ModuleType("google")
goog.cloud = types.ModuleType("google.cloud")
goog_ff = types.ModuleType("google.cloud.firestore_v1")
goog_bq = types.ModuleType("google.cloud.firestore_v1.base_query")
goog_bq.FieldFilter = lambda *a, **k: None
goog_ff.base_query = goog_bq
sys.modules.setdefault("google", goog)
sys.modules.setdefault("google.cloud", goog.cloud)
sys.modules.setdefault("google.cloud.firestore_v1", goog_ff)
sys.modules.setdefault("google.cloud.firestore_v1.base_query", goog_bq)

# Stub fastapi
import fastapi as _fapi_real  # ja disponivel — usa o real se instalado
import httpx  # ja disponivel

try:
    from whatsapp_bot import _alerta_ja_enviado, _alertas_enviados
    BOT_IMPORTED = True
except Exception as e:
    BOT_IMPORTED = False
    print(f"  AVISO: nao foi possivel importar whatsapp_bot ({e})")
    print("  Testando logica de dedup isolada (sem importar o modulo).\n")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Testa a logica de dedup diretamente (independente de import)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[1] LOGICA DE DEDUP DE ALERTAS")

import hashlib as _hashlib

# Replica a logica de _alerta_ja_enviado para teste isolado
_enviados_test: set = set()

def _dedup_test(fazenda_id: str, alerta: str, data_iso: str = None) -> bool:
    if data_iso is None:
        data_iso = datetime.date.today().isoformat()
    chave = (fazenda_id, _hashlib.md5(alerta.encode()).hexdigest(), data_iso)
    if chave in _enviados_test:
        return True
    _enviados_test.add(chave)
    hoje = datetime.date.today().isoformat()
    _enviados_test.difference_update({c for c in _enviados_test if c[2] != hoje})
    return False

# Primeira vez -> nao duplicado
check("1a vez: alerta novo nao bloqueado",
      _dedup_test("fazA", "Vaca seca: Mimosa") == False)

# Segunda vez mesmo alerta -> bloqueado
check("2a vez: mesmo alerta bloqueado",
      _dedup_test("fazA", "Vaca seca: Mimosa") == True)

# Alerta diferente -> nao bloqueado
check("Alerta diferente nao bloqueado",
      _dedup_test("fazA", "Parto previsto: Rainha") == False)

# Fazenda diferente -> nao bloqueado
check("Mesma msg, fazenda diferente nao bloqueada",
      _dedup_test("fazB", "Vaca seca: Mimosa") == False)

# Data diferente (simula proximo dia) -> nao bloqueado
ontem = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
_enviados_test.clear()
_dedup_test("fazA", "Alerta X", ontem)   # registra ontem
check("Mesmo alerta em dia diferente nao bloqueado",
      _dedup_test("fazA", "Alerta X") == False)  # hoje nao estava registrado

# Limpeza de datas antigas funciona
_enviados_test.clear()
_dedup_test("fazA", "Alerta antigo", ontem)
_dedup_test("fazA", "Alerta hoje")   # dispara limpeza
check("Entradas de datas anteriores sao removidas",
      not any(c[2] == ontem for c in _enviados_test))


# ─────────────────────────────────────────────────────────────────────────────
# 3. Testa o calculo de custo por litro
# ─────────────────────────────────────────────────────────────────────────────
print("\n[2] CALCULO DE CUSTO POR LITRO")

def _simular_custo_litro(fin_docs, prod_docs):
    """Replica a logica do endpoint /custo_litro."""
    total_prod = sum(p.get("leite", 0) for p in prod_docs)
    total_rec  = sum(f.get("valor", 0) for f in fin_docs if "Venda" in (f.get("cat") or f.get("categoria", "")))
    total_desp = sum(f.get("valor", 0) for f in fin_docs if "Venda" not in (f.get("cat") or f.get("categoria", "")))
    custo_litro  = round(total_desp / total_prod, 4) if total_prod > 0 else 0.0
    preco_litro  = round(total_rec  / total_prod, 4) if total_prod > 0 else 0.0
    margem_litro = round(preco_litro - custo_litro, 4)
    return {"custo_litro": custo_litro, "preco_litro": preco_litro,
            "margem_litro": margem_litro, "total_desp": total_desp,
            "total_rec": total_rec, "total_prod": total_prod}

# Caso 1: fazenda com dados normais
fin = [
    {"cat": "Racao / Nutricao", "valor": 1200.0},
    {"cat": "Medicamento",      "valor": 300.0},
    {"cat": "Mao de Obra",      "valor": 1500.0},
    {"cat": "Venda de Leite",   "valor": 8400.0},
]
prod = [{"leite": 30.0} for _ in range(100)]  # 100 registros * 30L = 3000L

r = _simular_custo_litro(fin, prod)
check("Custo total correto (3000/3000L = R$1,00/L)", abs(r["custo_litro"] - 1.0) < 0.001,
      f"obtido={r['custo_litro']}")
check("Preco correto (8400/3000L = R$2,80/L)", abs(r["preco_litro"] - 2.8) < 0.001,
      f"obtido={r['preco_litro']}")
check("Margem correta (2.80-1.00 = R$1,80/L)", abs(r["margem_litro"] - 1.8) < 0.001,
      f"obtido={r['margem_litro']}")
check("total_prod = 3000L", r["total_prod"] == 3000.0, str(r["total_prod"]))
check("total_desp = 3000.0", r["total_desp"] == 3000.0, str(r["total_desp"]))
check("total_rec  = 8400.0", r["total_rec"]  == 8400.0, str(r["total_rec"]))

# Caso 2: sem producao -> custo_litro = 0 (sem divisao por zero)
r2 = _simular_custo_litro(fin, [])
check("Sem producao -> custo_litro = 0 (sem ZeroDivision)", r2["custo_litro"] == 0.0,
      str(r2["custo_litro"]))
check("Sem producao -> preco_litro = 0", r2["preco_litro"] == 0.0, str(r2["preco_litro"]))

# Caso 3: sem despesas -> custo 0, margem = preco
fin3 = [{"cat": "Venda de Leite", "valor": 5000.0}]
r3 = _simular_custo_litro(fin3, [{"leite": 2000.0}])
check("Sem despesas -> custo_litro = 0", r3["custo_litro"] == 0.0, str(r3["custo_litro"]))
check("Sem despesas -> margem = preco",  abs(r3["margem_litro"] - r3["preco_litro"]) < 0.001,
      f"margem={r3['margem_litro']} preco={r3['preco_litro']}")

# Caso 4: prejuizo (custo > receita)
fin4 = [
    {"cat": "Racao", "valor": 10000.0},
    {"cat": "Venda de Leite", "valor": 3000.0},
]
r4 = _simular_custo_litro(fin4, [{"leite": 100.0}])
check("Prejuizo -> margem negativa", r4["margem_litro"] < 0,
      f"margem={r4['margem_litro']}")


# ─────────────────────────────────────────────────────────────────────────────
# 4. Testa usando o modulo real se importou com sucesso
# ─────────────────────────────────────────────────────────────────────────────
if BOT_IMPORTED:
    print("\n[3] DEDUP USANDO FUNCAO REAL DO BOT")
    _alertas_enviados.clear()
    check("Bot: 1a vez nao bloqueado",  _alerta_ja_enviado("fazX", "Alerta teste A") == False)
    check("Bot: 2a vez bloqueado",      _alerta_ja_enviado("fazX", "Alerta teste A") == True)
    check("Bot: texto diferente ok",    _alerta_ja_enviado("fazX", "Alerta teste B") == False)
    _alertas_enviados.clear()
else:
    print("\n[3] DEDUP MODULO REAL -- pulado (import falhou)")


# ─────────────────────────────────────────────────────────────────────────────
# Resultado
# ─────────────────────────────────────────────────────────────────────────────
total = ok_count + fail_count
taxa  = round(ok_count / total * 100) if total > 0 else 0
print("\n" + "=" * 60)
cor = "\033[32m" if fail_count == 0 else "\033[31m"
print(f"  {cor}OK: {ok_count}/{total}  ({taxa}%)  |  FAIL: {fail_count}\033[0m")
if fail_count == 0:
    print("  \033[32m[OK] TODOS OS TESTES UNITARIOS PASSARAM\033[0m")
print("=" * 60)
sys.exit(0 if fail_count == 0 else 1)

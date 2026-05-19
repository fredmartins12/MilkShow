"""
test_milkshow.py — Testes completos da API MilkShow
Execute: py -3 test_milkshow.py

Gera um JWT válido e testa todos os endpoints.
"""
import base64, hmac, hashlib, json, datetime, requests, sys

# ── Configuração ─────────────────────────────────────────────────────────────
BASE = "http://localhost:8080/api/v1"
SECRET  = "MkSh@dm1n#2024!"
FAZENDA = "JkDK1KbwlvT26kcZWnFXWWpHhG73"

# ── Gera JWT de teste ─────────────────────────────────────────────────────────
def gen_token():
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b'=').decode()
    exp    = (datetime.datetime.utcnow() + datetime.timedelta(days=1)).timestamp()
    payload= json.dumps({
        "uid": "test_seed",
        "email": "fredericobmartins@gmail.com",
        "fazenda_id": FAZENDA,
        "nome": "Frederico Teste",
        "permissoes": ["admin"],
        "exp": exp,
    })
    body   = base64.urlsafe_b64encode(payload.encode()).rstrip(b'=').decode()
    sig    = hmac.new(SECRET.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest()
    sig_b64= base64.urlsafe_b64encode(sig).rstrip(b'=').decode()
    return f"{header}.{body}.{sig_b64}"

TOKEN = gen_token()
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

# ── Helpers ───────────────────────────────────────────────────────────────────
ok_count = 0
fail_count = 0
results = []

def check(name, cond, detail=""):
    global ok_count, fail_count
    if cond:
        ok_count += 1
        results.append(f"  OK  {name}")
    else:
        fail_count += 1
        results.append(f"  FAIL {name}: {detail}")

def GET(path):
    return requests.get(f"{BASE}{path}", headers=HEADERS, timeout=15)

def POST(path, body):
    return requests.post(f"{BASE}{path}", headers=HEADERS, json=body, timeout=15)

def PATCH(path):
    return requests.patch(f"{BASE}{path}", headers=HEADERS, timeout=15)

def DELETE(path):
    return requests.delete(f"{BASE}{path}", headers=HEADERS, timeout=15)

hoje = datetime.date.today().isoformat()

print("=" * 60)
print("  MilkShow API — Teste Completo")
print(f"  Base: {BASE}")
print(f"  Fazenda: {FAZENDA}")
print("=" * 60)

# ══════════════════════════════════════════════════════════════════════════════
# 1. AUTH — Token inválido deve retornar 401
# ══════════════════════════════════════════════════════════════════════════════
print("\n[1] AUTH")
r = GET("/animais")
r_bad = requests.get(f"{BASE}/animais", headers={"Authorization": "Bearer tok_invalido"})
check("Token inválido retorna 401", r_bad.status_code == 401)
check("Token válido não retorna 401", r.status_code != 401, f"status={r.status_code}")

# ══════════════════════════════════════════════════════════════════════════════
# 2. DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
print("\n[2] DASHBOARD")
r = GET("/dashboard")
check("GET /dashboard status 200", r.status_code == 200, r.text[:100])
if r.ok:
    d = r.json()
    check("Tem campo 'hoje'",   "hoje"   in d)
    check("Tem campo 'semana'", "semana" in d)
    check("Tem campo 'mes'",    "mes"    in d)
    check("Tem preco_leite",    "preco_leite" in d)
    check("hoje.litros >= 0",   d["hoje"]["litros"] >= 0)
    check("hoje.vacas_lact > 0",d["hoje"]["vacas_lact"] > 0, f"valor={d['hoje']['vacas_lact']}")
    print(f"      Producao hoje: {d['hoje']['litros']}L | Vacas lact: {d['hoje']['vacas_lact']}")
    print(f"      Semana: {d['semana']['litros_7d']}L | Media: {d['semana']['media_dia']}L/dia")
    print(f"      Mes — Rec: R${d['mes']['receitas']} | Des: R${d['mes']['despesas']} | Saldo: R${d['mes']['saldo']}")

# ══════════════════════════════════════════════════════════════════════════════
# 3. ANIMAIS
# ══════════════════════════════════════════════════════════════════════════════
print("\n[3] ANIMAIS")
r = GET("/animais")
check("GET /animais status 200", r.status_code == 200, r.text[:100])
if r.ok:
    animais = r.json()
    check("Lista não vazia",         len(animais) > 0, f"len={len(animais)}")
    check("Tem >= 8 animais",        len(animais) >= 8, f"len={len(animais)}")
    check("Animal tem campo 'nome'", all("nome" in a for a in animais))
    check("Animal tem campo 'status'",all("status" in a for a in animais))
    em_lact = [a for a in animais if a.get("status") == "Lactação"]
    check("Tem vacas em lactação",   len(em_lact) > 0, f"encontradas={len(em_lact)}")
    print(f"      Total animais: {len(animais)} | Em lactação: {len(em_lact)}")
    print(f"      Primeiro: {animais[0].get('nome')} — {animais[0].get('status')}")

# POST — adicionar animal novo
r_add = POST("/animais", {
    "nome": "_TestAnimal",
    "status": "Novilha",
    "raca": "Holandesa Teste",
    "sexo": "Fêmea",
    "nascimento": "2025-01-15",
    "ins": "",
    "mae": "",
    "obs": "Animal de teste — deletar"
})
check("POST /animais status 200", r_add.status_code == 200, r_add.text[:100])

# Confirma que foi criado
r2 = GET("/animais")
nomes = [a["nome"] for a in r2.json()]
check("Animal novo aparece na listagem", "_TestAnimal" in nomes)

# DELETE — remove animal de teste
if r2.ok:
    test_id = next((a.get("id") for a in r2.json() if a.get("nome") == "_TestAnimal"), None)
    if not test_id:
        # tenta pegar pelo indice
        for a in r2.json():
            if a.get("nome") == "_TestAnimal":
                test_id = a.get("id") or a.get("_id")
                break
    if test_id:
        r_del = DELETE(f"/animais/{test_id}")
        check("DELETE /animais/{id} status 200", r_del.status_code == 200, r_del.text)
    else:
        # buscar ID no Firestore diretamente - nao temos esse endpoint, pula
        check("DELETE /animais (ID disponivel)", False, "id nao retornado pela API")

# ══════════════════════════════════════════════════════════════════════════════
# 4. PRODUÇÃO
# ══════════════════════════════════════════════════════════════════════════════
print("\n[4] PRODUCAO")
r = GET("/producao?dias=30")
check("GET /producao?dias=30 status 200", r.status_code == 200, r.text[:100])
if r.ok:
    regs = r.json()
    check("Tem registros de producao",  len(regs) > 0, f"len={len(regs)}")
    check("Tem >= 100 registros",       len(regs) >= 100, f"len={len(regs)}")
    check("Registro tem 'leite'",       all("leite" in rr for rr in regs[:5]))
    check("Registro tem 'nome_animal'", all("nome_animal" in rr for rr in regs[:5]))
    total = sum(rr["leite"] for rr in regs)
    check("Total leite > 0", total > 0, f"total={total:.1f}")
    print(f"      Registros: {len(regs)} | Total leite: {total:.1f}L")

# POST — registrar produção
r_post = POST("/producao", {
    "data":        hoje,
    "turno":       "noite",
    "id_animal":   "test_id",
    "nome_animal": "Mimosa",
    "leite":       12.5,
    "racao":       3.0,
    "obs":         "Teste API"
})
check("POST /producao status 200", r_post.status_code == 200, r_post.text[:100])

# Produção por animal
r_anim = GET("/producao/animal/Mimosa?dias=30")
check("GET /producao/animal/{nome} status 200", r_anim.status_code == 200, r_anim.text[:100])
if r_anim.ok:
    da = r_anim.json()
    check("Retorna producao da Mimosa", len(da) > 0, f"len={len(da)}")
    check("Todos sao da Mimosa", all(rr.get("nome_animal") == "Mimosa" for rr in da))
    print(f"      Mimosa — {len(da)} registros nos ultimos 30 dias")

# ══════════════════════════════════════════════════════════════════════════════
# 5. SANITÁRIO
# ══════════════════════════════════════════════════════════════════════════════
print("\n[5] SANITARIO")
r = GET("/sanitario?dias=90")
check("GET /sanitario status 200", r.status_code == 200, r.text[:100])
sanitario_id = None
if r.ok:
    san = r.json()
    check("Tem registros sanitarios", len(san) > 0, f"len={len(san)}")
    check("Registro tem 'animal'",    all("animal" in s for s in san[:3]))
    check("Registro tem 'protocolo'", all("protocolo" in s for s in san[:3]))
    check("Registro tem 'id'",        all("id" in s for s in san[:3]))
    pendentes = [s for s in san if not s.get("executado")]
    executados = [s for s in san if s.get("executado")]
    check("Tem pendentes", len(pendentes) > 0, f"pendentes={len(pendentes)}")
    check("Tem executados", len(executados) > 0, f"executados={len(executados)}")
    sanitario_id = pendentes[0]["id"] if pendentes else None
    print(f"      Total: {len(san)} | Pendentes: {len(pendentes)} | Executados: {len(executados)}")

# POST — registrar protocolo
r_post = POST("/sanitario", {
    "tipo":        "Vacina",
    "animal":      "Mimosa",
    "protocolo":   "Vacina Clostridiose — Teste API",
    "data":        hoje,
    "responsavel": "Teste Automatico",
    "dose":        "5mL",
    "via":         "SC",
    "obs":         "Registro de teste"
})
check("POST /sanitario status 200", r_post.status_code == 200, r_post.text[:100])

# PATCH — executar protocolo
if sanitario_id:
    r_exec = PATCH(f"/sanitario/{sanitario_id}/executar")
    check("PATCH /sanitario/{id}/executar status 200", r_exec.status_code == 200, r_exec.text[:100])
    # Confirma que foi marcado
    r3 = GET("/sanitario?dias=90")
    if r3.ok:
        after = [s for s in r3.json() if s["id"] == sanitario_id]
        if after:
            check("Protocolo marcado como executado", after[0].get("executado") == True)
else:
    check("PATCH /sanitario (sem pendente para testar)", False, "sem sanitario_id")

# ══════════════════════════════════════════════════════════════════════════════
# 6. FINANCEIRO
# ══════════════════════════════════════════════════════════════════════════════
print("\n[6] FINANCEIRO")
r = GET("/financeiro?dias=90")
check("GET /financeiro status 200", r.status_code == 200, r.text[:100])
if r.ok:
    fin = r.json()
    check("Tem lancamentos financeiros", len(fin) > 0, f"len={len(fin)}")
    check("Tem >= 10 lancamentos", len(fin) >= 10, f"len={len(fin)}")
    receitas = [f for f in fin if f.get("tipo") == "receita"]
    despesas = [f for f in fin if f.get("tipo") == "despesa"]
    check("Tem receitas", len(receitas) > 0, f"receitas={len(receitas)}")
    check("Tem despesas", len(despesas) > 0, f"despesas={len(despesas)}")
    print(f"      Total: {len(fin)} | Receitas: {len(receitas)} | Despesas: {len(despesas)}")

# POST — receita
r_rec = POST("/financeiro", {
    "data":       hoje,
    "tipo":       "receita",
    "categoria":  "Venda de Leite",
    "descricao":  "Teste API — venda 100L",
    "valor":      255.00,
    "obs":        "teste automatico"
})
check("POST /financeiro receita status 200", r_rec.status_code == 200, r_rec.text[:100])

# POST — despesa
r_des = POST("/financeiro", {
    "data":       hoje,
    "tipo":       "despesa",
    "categoria":  "Ração",
    "descricao":  "Teste API — compra racao",
    "valor":      150.00,
    "obs":        "teste automatico"
})
check("POST /financeiro despesa status 200", r_des.status_code == 200, r_des.text[:100])

# Resumo
r_res = GET("/financeiro/resumo?dias=90")
check("GET /financeiro/resumo status 200", r_res.status_code == 200, r_res.text[:100])
if r_res.ok:
    res = r_res.json()
    check("Resumo nao vazio", len(res) > 0, f"len={len(res)}")
    check("Resumo tem campo 'total'", all("total" in x for x in res))
    print(f"      Categorias no resumo: {len(res)}")

# ══════════════════════════════════════════════════════════════════════════════
# 6b. CUSTO POR LITRO (KPI mensal)
# ══════════════════════════════════════════════════════════════════════════════
print("\n[6b] CUSTO POR LITRO")
r = GET("/custo_litro")
check("GET /custo_litro status 200", r.status_code == 200, r.text[:100])
if r.ok:
    kpi = r.json()
    check("Tem campo 'custo_litro'",  "custo_litro"  in kpi)
    check("Tem campo 'preco_litro'",  "preco_litro"  in kpi)
    check("Tem campo 'margem_litro'", "margem_litro" in kpi)
    check("Tem campo 'total_prod'",   "total_prod"   in kpi)
    check("Tem campo 'total_desp'",   "total_desp"   in kpi)
    check("Tem campo 'total_rec'",    "total_rec"    in kpi)
    check("Tem campo 'breakdown'",    "breakdown"    in kpi)
    check("custo_litro >= 0",   kpi.get("custo_litro", -1)  >= 0, str(kpi.get("custo_litro")))
    check("total_prod >= 0",    kpi.get("total_prod",  -1)  >= 0, str(kpi.get("total_prod")))
    check("total_desp >= 0",    kpi.get("total_desp",  -1)  >= 0, str(kpi.get("total_desp")))
    check("breakdown e lista",  isinstance(kpi.get("breakdown"), list), type(kpi.get("breakdown")).__name__)
    if kpi.get("total_prod", 0) > 0 and kpi.get("total_desp", 0) > 0:
        custo_calc = round(kpi["total_desp"] / kpi["total_prod"], 4)
        check("custo_litro = total_desp / total_prod",
              abs(kpi["custo_litro"] - custo_calc) < 0.01,
              f"kpi={kpi['custo_litro']} calc={custo_calc}")
        check("margem_litro = preco - custo",
              abs(kpi["margem_litro"] - (kpi["preco_litro"] - kpi["custo_litro"])) < 0.01,
              f"{kpi['margem_litro']} vs {kpi['preco_litro'] - kpi['custo_litro']:.4f}")
    print(f"      Producao: {kpi.get('total_prod')}L | Despesas: R${kpi.get('total_desp')}")
    print(f"      Custo/L: R${kpi.get('custo_litro')} | Preco/L: R${kpi.get('preco_litro')} | Margem: R${kpi.get('margem_litro')}")

# ══════════════════════════════════════════════════════════════════════════════
# 7. CONFIG
# ══════════════════════════════════════════════════════════════════════════════
print("\n[7] CONFIG")
r = GET("/config")
check("GET /config status 200", r.status_code == 200, r.text[:100])
if r.ok:
    cfg = r.json()
    check("Config nao vazio",            len(cfg) > 0, f"len={len(cfg)}")
    check("Tem nome_fazenda",            "nome_fazenda" in cfg, str(cfg.keys()))
    check("Tem preco_leite",             "preco_leite" in cfg)
    print(f"      Fazenda: {cfg.get('nome_fazenda')} | Preco leite: R${cfg.get('preco_leite')}/L")

# POST — salvar config
r_save = POST("/config", {
    "nome_fazenda":    "Fazenda Santa Clara — Teste",
    "preco_leite":     "2.60",
    "custo_por_litro": "1.20",
    "meta_producao":   "1000",
})
check("POST /config status 200", r_save.status_code == 200, r_save.text[:100])

# Confirma que salvou
r2 = GET("/config")
if r2.ok:
    check("Config atualizado — preco_leite=2.60", r2.json().get("preco_leite") == "2.60")
    check("Config atualizado — meta_producao=1000", r2.json().get("meta_producao") == "1000")

# ══════════════════════════════════════════════════════════════════════════════
# 8. ESTOQUE
# ══════════════════════════════════════════════════════════════════════════════
print("\n[8] ESTOQUE")
r = GET("/estoque")
check("GET /estoque status 200", r.status_code == 200, r.text[:100])
if r.ok:
    est = r.json()
    check("Tem itens no estoque", len(est) > 0, f"len={len(est)}")
    check("Item tem campo 'item'", all("item" in e for e in est))
    check("Item tem campo 'qtd'",  all("qtd" in e for e in est))
    print(f"      {len(est)} itens no estoque")

# ══════════════════════════════════════════════════════════════════════════════
# 9. INTEGRIDADE DE DADOS — Dashboard bate com producao
# ══════════════════════════════════════════════════════════════════════════════
print("\n[9] INTEGRIDADE")
r_dash  = GET("/dashboard")
r_prod  = GET("/producao?dias=1")
r_anim2 = GET("/animais")
if r_dash.ok and r_prod.ok and r_anim2.ok:
    dash   = r_dash.json()
    prods  = [p for p in r_prod.json() if p.get("data") == hoje]
    animais2 = r_anim2.json()
    lact_count = len([a for a in animais2 if a.get("status") == "Lactação"])
    check("Dashboard vacas_lact bate com /animais", dash["hoje"]["vacas_lact"] == lact_count,
          f"dashboard={dash['hoje']['vacas_lact']} vs api={lact_count}")
    litros_api = sum(p.get("leite", 0) for p in prods)
    check("Litros hoje > 0 na producao", litros_api > 0, f"litros={litros_api:.1f}")

# ══════════════════════════════════════════════════════════════════════════════
# RESULTADO FINAL
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  RESULTADOS")
print("=" * 60)
for line in results:
    print(line)

total = ok_count + fail_count
print(f"\n  OK: {ok_count}/{total}  |  FAIL: {fail_count}/{total}")
if fail_count == 0:
    print("  TODOS OS TESTES PASSARAM")
else:
    print(f"  {fail_count} TESTE(S) FALHARAM")
print("=" * 60)

sys.exit(0 if fail_count == 0 else 1)

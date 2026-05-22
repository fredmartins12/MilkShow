"""
seed_dados.py — Popula o Firebase com dados fictícios realistas para testes.
Execute: python seed_dados.py
"""
import datetime
import random
import firebase_admin
from firebase_admin import credentials, firestore

# ── Firebase ──────────────────────────────────────────────────────────────────
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_key.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

hoje = datetime.date.today()

def d(dias_atras):
    return str(hoje - datetime.timedelta(days=dias_atras))

def add(colecao, dados):
    db.collection(colecao).add(dados)

def limpar(colecao):
    for doc in db.collection(colecao).stream():
        doc.reference.delete()

print("🧹 Limpando coleções antigas...")
for col in ["animais", "producao", "financeiro", "estoque", "sanitario"]:
    limpar(col)
    print(f"   {col} limpo")

# ══════════════════════════════════════════════════════════════════════════════
# ANIMAIS
# ══════════════════════════════════════════════════════════════════════════════
print("\n🐄 Inserindo animais...")

animais = [
    # Em lactação
    {"id":"101","nome":"Mimosa",   "status":"Lactação","lote":"A","sexo":"Fêmea","nasc":d(1825),"dt_parto":d(60),"dt_insem":d(30),"prenhez":False,"colostro":True,"freq":2},
    {"id":"102","nome":"Estrela",  "status":"Lactação","lote":"A","sexo":"Fêmea","nasc":d(2100),"dt_parto":d(45),"dt_insem":d(10),"prenhez":False,"colostro":True,"freq":2},
    {"id":"103","nome":"Mansinha", "status":"Lactação","lote":"A","sexo":"Fêmea","nasc":d(1500),"dt_parto":d(90),"dt_insem":d(55),"prenhez":True, "colostro":True,"freq":2},
    {"id":"104","nome":"Pintada",  "status":"Lactação","lote":"B","sexo":"Fêmea","nasc":d(1650),"dt_parto":d(20),"dt_insem":None,"prenhez":False,"colostro":True,"freq":3},
    {"id":"105","nome":"Branquinha","status":"Lactação","lote":"B","sexo":"Fêmea","nasc":d(1900),"dt_parto":d(110),"dt_insem":d(75),"prenhez":True,"colostro":True,"freq":2},
    {"id":"106","nome":"Moreninha","status":"Lactação","lote":"A","sexo":"Fêmea","nasc":d(1750),"dt_parto":d(15),"dt_insem":None,"prenhez":False,"colostro":True,"freq":2},
    {"id":"107","nome":"Faceira",  "status":"Lactação","lote":"B","sexo":"Fêmea","nasc":d(2200),"dt_parto":d(70),"dt_insem":d(35),"prenhez":False,"colostro":True,"freq":2},
    {"id":"108","nome":"Rainha",   "status":"Lactação","lote":"A","sexo":"Fêmea","nasc":d(1600),"dt_parto":d(5),"dt_insem":None,"prenhez":False,"colostro":True,"freq":3},

    # Secas
    {"id":"201","nome":"Velha",    "status":"Seca","lote":"C","sexo":"Fêmea","nasc":d(3000),"dt_parto":d(280),"dt_insem":d(240),"prenhez":True,"colostro":True,"freq":0},
    {"id":"202","nome":"Gordinha", "status":"Seca","lote":"C","sexo":"Fêmea","nasc":d(2800),"dt_parto":d(300),"dt_insem":d(260),"prenhez":True,"colostro":True,"freq":0},

    # Bezerros
    {"id":"301","nome":"Fresquinho","status":"Bezerro","lote":"Berçário","sexo":"Macho","nasc":d(5),"mae_id":"104","colostro":True,"freq":0},
    {"id":"302","nome":"Estrelinha","status":"Bezerro","lote":"Berçário","sexo":"Fêmea","nasc":d(20),"mae_id":"101","colostro":True,"freq":0},
    {"id":"303","nome":"Pretinho",  "status":"Bezerro","lote":"Berçário","sexo":"Macho","nasc":d(45),"mae_id":"103","colostro":True,"freq":0},

    # Novilhas
    {"id":"401","nome":"Boneca",   "status":"Novilha","lote":"Recria","sexo":"Fêmea","nasc":d(500),"colostro":True,"freq":0},
    {"id":"402","nome":"Caprichosa","status":"Novilha","lote":"Recria","sexo":"Fêmea","nasc":d(420),"colostro":True,"freq":0},

    # Touro
    {"id":"501","nome":"Trovão",   "status":"Touro","lote":"Geral","sexo":"Macho","nasc":d(1460),"colostro":True,"freq":0},
]

for a in animais:
    a.setdefault("mae_id", None)
    a.setdefault("dt_insem", None)
    a.setdefault("dt_parto", None)
    a.setdefault("prenhez", False)
    add("animais", a)

print(f"   {len(animais)} animais inseridos")

# ══════════════════════════════════════════════════════════════════════════════
# PRODUÇÃO — últimos 35 dias para vacas em lactação
# ══════════════════════════════════════════════════════════════════════════════
print("\n🥛 Inserindo produções...")

# Produção base por vaca (litros/dia variando)
base_prod = {
    "101": 22, "102": 18, "103": 28, "104": 32,
    "105": 20, "106": 35, "107": 15, "108": 40,
}
nomes = {a["id"]: a["nome"] for a in animais}

count_prod = 0
for dias_atras in range(35, 0, -1):
    data_str = d(dias_atras)
    for vid, base in base_prod.items():
        # Variação aleatória realista ±15%
        variacao = random.uniform(0.85, 1.15)
        leite_total = round(base * variacao, 2)

        # Dois turnos (manhã e tarde)
        leite_m = round(leite_total * random.uniform(0.55, 0.65), 2)
        leite_t = round(leite_total - leite_m, 2)
        racao_m = round(random.uniform(3.0, 5.5), 2)
        racao_t = round(random.uniform(2.5, 4.5), 2)

        add("producao", {"data": data_str, "turno": 1, "id_animal": vid,
                          "nome_animal": nomes[vid], "leite": leite_m, "racao": racao_m})
        add("producao", {"data": data_str, "turno": 2, "id_animal": vid,
                          "nome_animal": nomes[vid], "leite": leite_t, "racao": racao_t})
        count_prod += 2

print(f"   {count_prod} registros de produção inseridos")

# ══════════════════════════════════════════════════════════════════════════════
# ESTOQUE
# ══════════════════════════════════════════════════════════════════════════════
print("\n📦 Inserindo estoque...")

estoque_items = [
    {"item":"Ração Concentrada",  "qtd":850.0, "un":"kg",     "custo_medio":2.30},
    {"item":"Silagem de Milho",   "qtd":4200.0,"un":"kg",     "custo_medio":0.28},
    {"item":"Sal Mineral",        "qtd":120.0, "un":"kg",     "custo_medio":3.50},
    {"item":"Ocitocina",          "qtd":18.0,  "un":"dose",   "custo_medio":4.20},
    {"item":"Ivermectina",        "qtd":5.0,   "un":"frasco", "custo_medio":32.00},
    {"item":"Penicilina G",       "qtd":12.0,  "un":"frasco", "custo_medio":18.50},
    {"item":"Soro Fisiológico",   "qtd":20.0,  "un":"L",      "custo_medio":8.00},
    {"item":"Vacina Aftosa",      "qtd":25.0,  "un":"dose",   "custo_medio":2.80},
    {"item":"Prostaglandina",     "qtd":8.0,   "un":"dose",   "custo_medio":15.00},
    {"item":"Antibiótico Mastite","qtd":6.0,   "un":"bisnaga","custo_medio":12.00},
]

for e in estoque_items:
    add("estoque", e)

print(f"   {len(estoque_items)} itens de estoque inseridos")

# ══════════════════════════════════════════════════════════════════════════════
# FINANCEIRO — 3 meses de movimentações
# ══════════════════════════════════════════════════════════════════════════════
print("\n💰 Inserindo movimentações financeiras...")

lancamentos = []

# Vendas de leite (quinzenais)
for i in [90, 75, 60, 45, 30, 15, 3]:
    litros = random.randint(2800, 3400)
    preco  = round(random.uniform(2.40, 2.70), 2)
    valor  = round(litros * preco, 2)
    lancamentos.append({
        "data": d(i), "cat": "Venda de Leite",
        "desc": f"Venda leite laticínio Cooperativa — {litros} L",
        "valor": valor, "tipo": "Geral", "animal": None,
        "ref_ini": d(i+14), "ref_fim": d(i),
    })

# Compras de ração (mensais)
for i in [85, 55, 25]:
    add("financeiro", {
        "data": d(i), "cat": "Ração / Nutrição",
        "desc": "Compra Ração Concentrada 500 kg — AgroCenter",
        "valor": 1150.00, "tipo": "Geral", "animal": None, "origem": "armazem",
    })
    add("financeiro", {
        "data": d(i-3), "cat": "Ração / Nutrição",
        "desc": "Compra Silagem de Milho 2000 kg — Fazenda Vizinha",
        "valor": 560.00, "tipo": "Geral", "animal": None, "origem": "armazem",
    })

# Medicamentos
for i in [70, 40, 12]:
    add("financeiro", {
        "data": d(i), "cat": "Medicamento / Sanitário",
        "desc": "Compra Ocitocina 10 doses — Cortvet",
        "valor": 42.00, "tipo": "Geral", "animal": None, "origem": "armazem",
    })
    add("financeiro", {
        "data": d(i+2), "cat": "Medicamento / Sanitário",
        "desc": "Compra Ivermectina 2 frascos — Cortvet",
        "valor": 64.00, "tipo": "Geral", "animal": None, "origem": "armazem",
    })

# Mão de obra mensal
for i in [90, 60, 30, 5]:
    add("financeiro", {
        "data": d(i), "cat": "Mão de Obra",
        "desc": "Pagamento funcionário — Ordenha e trato",
        "valor": 1800.00, "tipo": "Geral", "animal": None,
    })

# Energia elétrica
for i in [88, 58, 28]:
    add("financeiro", {
        "data": d(i), "cat": "Energia",
        "desc": "Fatura energia elétrica — Fazenda",
        "valor": round(random.uniform(320, 480), 2), "tipo": "Geral", "animal": None,
    })

# Infraestrutura
add("financeiro", {"data": d(50), "cat": "Infraestrutura", "desc": "Reforma bebedouro — curral B", "valor": 380.00, "tipo": "Geral", "animal": None})
add("financeiro", {"data": d(20), "cat": "Infraestrutura", "desc": "Mangueira e acessórios lavagem", "valor": 145.00, "tipo": "Geral", "animal": None})

# Venda de animais
add("financeiro", {"data": d(35), "cat": "Venda de Animais", "desc": "Venda Garrote Neguinho — Frigorífico", "valor": 2800.00, "tipo": "Receita", "animal": "ex_303"})

# Compra de animal
add("financeiro", {"data": d(80), "cat": "Compra de Animais", "desc": "Compra Novilha Caprichosa #402 — Rebanho Santos", "valor": 3500.00, "tipo": "Geral", "animal": "402", "origem": "rebanho"})

for l in lancamentos:
    add("financeiro", l)

print(f"   Lançamentos financeiros inseridos")

# ══════════════════════════════════════════════════════════════════════════════
# SANITÁRIO
# ══════════════════════════════════════════════════════════════════════════════
print("\n💉 Inserindo registros sanitários...")

sanitarios = [
    {"data": d(60), "tipo": "Vacina",    "prod": "Vacina Aftosa",   "modo": "Rebanho Todo", "animal": None,    "custo": 56.00, "obs": "Vacinação semestral obrigatória"},
    {"data": d(45), "tipo": "Vermífugo", "prod": "Ivermectina",      "modo": "Rebanho Todo", "animal": None,    "custo": 64.00, "obs": "Controle parasitário trimestral"},
    {"data": d(30), "tipo": "Hormônio",  "prod": "Ocitocina",        "modo": "Individual",   "animal": "103",   "custo": 4.20,  "obs": "Aplicado para auxiliar descida do leite"},
    {"data": d(25), "tipo": "Hormônio",  "prod": "Prostaglandina",   "modo": "Individual",   "animal": "102",   "custo": 15.00, "obs": "Protocolo de sincronização IATF"},
    {"data": d(20), "tipo": "Antibiótico","prod":"Penicilina G",      "modo": "Individual",   "animal": "107",   "custo": 18.50, "obs": "Mastite clínica lado esquerdo"},
    {"data": d(15), "tipo": "Antibiótico","prod":"Antibiótico Mastite","modo":"Individual",    "animal": "107",   "custo": 12.00, "obs": "Tratamento continuado — 3ª dose"},
    {"data": d(12), "tipo": "Hormônio",  "prod": "Ocitocina",        "modo": "Individual",   "animal": "104",   "custo": 4.20,  "obs": "Pós-parto"},
    {"data": d(8),  "tipo": "Hormônio",  "prod": "Ocitocina",        "modo": "Individual",   "animal": "108",   "custo": 4.20,  "obs": "Retenção de placenta suspeita"},
    {"data": d(5),  "tipo": "Vacina",    "prod": "Vacina Brucelose",  "modo": "Individual",   "animal": "302",   "custo": 22.00, "obs": "Bezerrinha — dose única"},
    {"data": d(2),  "tipo": "Casqueamento","prod":"Casqueamento",     "modo": "Rebanho Todo", "animal": None,    "custo": 200.00,"obs": "Preventivo — 4 vacas do lote A"},
]

for s in sanitarios:
    add("sanitario", s)

print(f"   {len(sanitarios)} registros sanitários inseridos")

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════
print("\n⚙️ Inserindo configurações...")
for doc in db.collection("config").stream():
    doc.reference.delete()

configs = [
    {"chave": "nome_fazenda", "valor": "Fazenda Santa Clara"},
    {"chave": "preco_leite",  "valor": 2.55},
    {"chave": "preco_periodo_2026-04", "valor": 2.55},
    {"chave": "preco_periodo_2026-03", "valor": 2.50},
    {"chave": "preco_periodo_2026-02", "valor": 2.45},
    {"chave": "preco_periodo_2026-01", "valor": 2.40},
]
for c in configs:
    add("config", c)

print(f"   {len(configs)} configurações inseridas")

print("\n✅ Seed completo! Acesse http://localhost:8507 e recarregue a página.")
print(f"   Animais: {len(animais)}")
print(f"   Produções: {count_prod} registros (35 dias × 8 vacas × 2 turnos)")
print(f"   Estoque: {len(estoque_items)} itens")
print(f"   Sanitário: {len(sanitarios)} procedimentos")
print(f"   Financeiro: lançamentos dos últimos 90 dias")

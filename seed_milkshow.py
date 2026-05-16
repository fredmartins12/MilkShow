"""
seed_milkshow.py — Popula Firebase (multi-tenant) com dados aleatórios realistas
Execute: py -3 seed_milkshow.py

Estrutura: fazendas/{FAZENDA_ID}/{colecao}
"""
import datetime
import random
import firebase_admin
from firebase_admin import credentials, firestore

FAZENDA_ID = "JkDK1KbwlvT26kcZWnFXWWpHhG73"

if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_key.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

hoje = datetime.date.today()

def d(dias_atras: int) -> str:
    return (hoje - datetime.timedelta(days=dias_atras)).isoformat()

def d_futura(dias: int) -> str:
    return (hoje + datetime.timedelta(days=dias)).isoformat()

def coll(nome: str):
    return db.collection("fazendas").document(FAZENDA_ID).collection(nome)

def limpar(nome: str):
    batch = db.batch()
    docs = list(coll(nome).stream())
    for doc in docs:
        batch.delete(doc.reference)
    if docs:
        batch.commit()
    return len(docs)

# ── Limpa tudo ────────────────────────────────────────────────────────────────
print("Limpando colecoes...")
for col in ["animais", "producao", "financeiro", "sanitario", "config", "estoque"]:
    n = limpar(col)
    print(f"  {col}: {n} docs removidos")

# ══════════════════════════════════════════════════════════════════════════════
# ANIMAIS — estrutura compativel com AnimalInput
# ══════════════════════════════════════════════════════════════════════════════
print("\nInserindo animais...")

RACAS = ["Holandesa", "Girolando", "Jersey", "Nelore Leiteiro", "Pardo Suíço"]

animais_data = [
    # Lactação
    dict(nome="Mimosa",    status="Lactação", raca="Holandesa",       sexo="Fêmea",
         nascimento=d(1825), ins=d(60), mae="", obs="Alto volume — 32L/dia"),
    dict(nome="Estrela",   status="Lactação", raca="Girolando",       sexo="Fêmea",
         nascimento=d(2100), ins=d(45), mae="", obs=""),
    dict(nome="Mansinha",  status="Lactação", raca="Holandesa",       sexo="Fêmea",
         nascimento=d(1500), ins=d(90), mae="", obs="Suspeita prenhez"),
    dict(nome="Pintada",   status="Lactação", raca="Jersey",          sexo="Fêmea",
         nascimento=d(1650), ins="",    mae="", obs="Parto recente — 20 dias"),
    dict(nome="Branquinha",status="Lactação", raca="Girolando",       sexo="Fêmea",
         nascimento=d(1900), ins=d(75), mae="", obs=""),
    dict(nome="Moreninha", status="Lactação", raca="Pardo Suíço",     sexo="Fêmea",
         nascimento=d(1750), ins="",    mae="", obs="Secagem prevista em 26 dias"),
    dict(nome="Faceira",   status="Lactação", raca="Holandesa",       sexo="Fêmea",
         nascimento=d(2200), ins=d(35), mae="", obs=""),
    dict(nome="Rainha",    status="Lactação", raca="Nelore Leiteiro", sexo="Fêmea",
         nascimento=d(1600), ins="",    mae="", obs="Parto há 5 dias"),
    # Secas
    dict(nome="Velha",     status="Seca",     raca="Holandesa",       sexo="Fêmea",
         nascimento=d(3000), ins=d(240), mae="", obs="Parto previsto " + d_futura(43)),
    dict(nome="Gordinha",  status="Seca",     raca="Girolando",       sexo="Fêmea",
         nascimento=d(2800), ins=d(260), mae="", obs="Parto previsto " + d_futura(23)),
    # Gestação
    dict(nome="Rosa",      status="Gestação", raca="Holandesa",       sexo="Fêmea",
         nascimento=d(2000), ins=d(200), mae="", obs="DG positivo — 200 dias gestação"),
    # Bezerros
    dict(nome="Fresquinho",status="Bezerro",  raca="Holandesa",       sexo="Macho",
         nascimento=d(5),   ins="",     mae="Pintada",  obs="Colostro administrado"),
    dict(nome="Estrelinha",status="Bezerro",  raca="Girolando",       sexo="Fêmea",
         nascimento=d(20),  ins="",     mae="Estrela",  obs=""),
    dict(nome="Pretinho",  status="Bezerro",  raca="Holandesa",       sexo="Macho",
         nascimento=d(45),  ins="",     mae="Mansinha", obs=""),
    dict(nome="Bolinha",   status="Bezerro",  raca="Jersey",          sexo="Fêmea",
         nascimento=d(92),  ins="",     mae="Mimosa",   obs="DESMAME VENCIDO"),
    # Novilhas
    dict(nome="Boneca",    status="Novilha",  raca="Holandesa",       sexo="Fêmea",
         nascimento=d(500), ins="",     mae="", obs=""),
    dict(nome="Caprichosa",status="Novilha",  raca="Girolando",       sexo="Fêmea",
         nascimento=d(420), ins="",     mae="", obs=""),
]

animais_ids = {}
for a in animais_data:
    doc = a.copy()
    doc["ts"] = datetime.datetime.now().isoformat()
    _, ref = coll("animais").add(doc)
    animais_ids[a["nome"]] = ref.id

print(f"  {len(animais_data)} animais inseridos")

# ══════════════════════════════════════════════════════════════════════════════
# PRODUÇÃO — últimos 35 dias, 2–3 turnos por vaca em lactação
# ══════════════════════════════════════════════════════════════════════════════
print("\nInserindo producao...")

vacas_lact = {
    "Mimosa":     32, "Estrela":  18, "Mansinha": 28, "Pintada":    22,
    "Branquinha": 20, "Moreninha":24, "Faceira":  15, "Rainha":     35,
}
turnos = ["manhã", "tarde", "noite"]
count_prod = 0

for dias_atras in range(35, 0, -1):
    data_str = d(dias_atras)
    for nome, base in vacas_lact.items():
        # variação ±15%
        total = round(base * random.uniform(0.85, 1.15), 2)
        # 2 turnos normalmente, às vezes 3
        n_turnos = random.choices([2, 3], weights=[0.7, 0.3])[0]
        partes = sorted([random.random() for _ in range(n_turnos - 1)])
        partes = [0] + partes + [1]
        for i in range(n_turnos):
            frac   = partes[i+1] - partes[i]
            leite  = round(total * frac, 2)
            racao  = round(random.uniform(2.5, 5.0), 2)
            coll("producao").add({
                "data":        data_str,
                "turno":       turnos[i],
                "id_animal":   animais_ids.get(nome, nome),
                "nome_animal": nome,
                "leite":       leite,
                "racao":       racao,
                "obs":         "",
                "ts":          datetime.datetime.now().isoformat(),
            })
            count_prod += 1

# Produção de hoje
for nome, base in vacas_lact.items():
    leite = round(base * random.uniform(0.88, 1.12), 2)
    coll("producao").add({
        "data":        hoje.isoformat(),
        "turno":       "manhã",
        "id_animal":   animais_ids.get(nome, nome),
        "nome_animal": nome,
        "leite":       leite,
        "racao":       round(random.uniform(3.0, 5.0), 2),
        "obs":         "",
        "ts":          datetime.datetime.now().isoformat(),
    })
    count_prod += 1

print(f"  {count_prod} registros de producao inseridos")

# ══════════════════════════════════════════════════════════════════════════════
# SANITÁRIO — histórico + futuros pendentes
# ══════════════════════════════════════════════════════════════════════════════
print("\nInserindo sanitario...")

sanitarios = [
    # Executados (passados)
    dict(tipo="Vacina",     animal="Mimosa",    protocolo="Aftosa — Dose Semestral",
         data=d(60),  responsavel="Dr. Paulo Silva", dose="2mL", via="SC",
         executado=True, obs="Vacinação semestral obrigatória"),
    dict(tipo="Vacina",     animal="Estrela",   protocolo="Aftosa — Dose Semestral",
         data=d(60),  responsavel="Dr. Paulo Silva", dose="2mL", via="SC",
         executado=True, obs=""),
    dict(tipo="Medicamento",animal="Faceira",   protocolo="Penicilina G — Mastite",
         data=d(20),  responsavel="Dr. Paulo Silva", dose="10mL", via="IM",
         executado=True, obs="Mastite clínica lado esquerdo"),
    dict(tipo="Medicamento",animal="Faceira",   protocolo="Penicilina G — Mastite 2ª dose",
         data=d(18),  responsavel="Dr. Paulo Silva", dose="10mL", via="IM",
         executado=True, obs="Continuação tratamento"),
    dict(tipo="Vacina",     animal="Estrelinha",protocolo="Brucelose — Dose Única",
         data=d(15),  responsavel="Dr. Paulo Silva", dose="2mL", via="SC",
         executado=True, obs="Bezerrinha 20 dias"),
    dict(tipo="Protocolo",  animal="Mansinha",  protocolo="Prostaglandina — IATF",
         data=d(25),  responsavel="Dr. Paulo Silva", dose="2mL", via="IM",
         executado=True, obs="Sincronização de cio"),
    dict(tipo="Exame",      animal="Rosa",      protocolo="Ultrassonografia — DG",
         data=d(10),  responsavel="Dr. Paulo Silva", dose="", via="",
         executado=True, obs="DG positivo confirmado"),
    # Pendentes futuros
    dict(tipo="Vacina",     animal="Mimosa",    protocolo="Aftosa — Reforço Semestral",
         data=d_futura(3),  responsavel="Dr. Paulo Silva", dose="2mL", via="SC",
         executado=False, obs="Agendado"),
    dict(tipo="Vacina",     animal="Estrela",   protocolo="Aftosa — Reforço Semestral",
         data=d_futura(3),  responsavel="Dr. Paulo Silva", dose="2mL", via="SC",
         executado=False, obs=""),
    dict(tipo="Protocolo",  animal="Moreninha", protocolo="Secagem — Mastivac",
         data=d_futura(26), responsavel="Dr. Paulo Silva", dose="1 bisnaga", via="Intramamário",
         executado=False, obs="Secagem programada"),
    dict(tipo="Exame",      animal="Branquinha",protocolo="Ultrassonografia — DG Confirmação",
         data=d_futura(7),  responsavel="Dr. Paulo Silva", dose="", via="",
         executado=False, obs="30 dias pós-IA"),
    # Vencidos (críticos)
    dict(tipo="Protocolo",  animal="Bolinha",   protocolo="Desmame — 92 dias",
         data=d(2),   responsavel="Equipe de campo", dose="", via="",
         executado=False, obs="URGENTE: 92 dias de vida"),
    dict(tipo="Vacina",     animal="Velha",     protocolo="Clostridiose — Reforço",
         data=d(1),   responsavel="Dr. Paulo Silva", dose="5mL", via="SC",
         executado=False, obs=""),
]

for s in sanitarios:
    doc = s.copy()
    doc["registrado_por"] = "seed"
    doc["ts"] = datetime.datetime.now().isoformat()
    coll("sanitario").add(doc)

print(f"  {len(sanitarios)} registros sanitarios inseridos")

# ══════════════════════════════════════════════════════════════════════════════
# FINANCEIRO — 90 dias de movimentações (compatível com novo modelo)
# ══════════════════════════════════════════════════════════════════════════════
print("\nInserindo financeiro...")

lancamentos = []

# Vendas de leite quinzenais
for i in [90, 75, 60, 45, 30, 15, 3]:
    litros = random.randint(2800, 3800)
    preco  = round(random.uniform(2.45, 2.70), 2)
    lancamentos.append(dict(
        data=d(i), tipo="receita", categoria="Venda de Leite", cat="Venda de Leite",
        descricao=f"Venda leite Cooperativa — {litros}L × R${preco:.2f}",
        valor=round(litros * preco, 2), obs=f"{litros}L"
    ))

# Ração mensal
for i in [85, 55, 25]:
    lancamentos.append(dict(
        data=d(i), tipo="despesa", categoria="Ração", cat="Ração",
        descricao="Compra Ração Concentrada 500 kg — AgroCenter",
        valor=round(random.uniform(1050, 1250), 2), obs=""
    ))
    lancamentos.append(dict(
        data=d(i-2), tipo="despesa", categoria="Ração", cat="Ração",
        descricao="Compra Silagem de Milho 2000 kg",
        valor=round(random.uniform(520, 620), 2), obs=""
    ))

# Medicamentos
for i in [70, 40, 12]:
    lancamentos.append(dict(
        data=d(i), tipo="despesa", categoria="Medicamentos", cat="Medicamentos",
        descricao="Compra insumos veterinários — Cortvet",
        valor=round(random.uniform(120, 280), 2), obs=""
    ))

# Mão de obra mensal
for i in [90, 60, 30, 5]:
    lancamentos.append(dict(
        data=d(i), tipo="despesa", categoria="Mão de Obra", cat="Mão de Obra",
        descricao="Salário funcionário — Ordenha e trato",
        valor=round(random.uniform(1700, 1900), 2), obs=""
    ))

# Energia
for i in [88, 58, 28]:
    lancamentos.append(dict(
        data=d(i), tipo="despesa", categoria="Energia", cat="Energia",
        descricao="Fatura energia elétrica",
        valor=round(random.uniform(320, 490), 2), obs=""
    ))

# Manutenção
lancamentos.append(dict(
    data=d(50), tipo="despesa", categoria="Manutenção", cat="Manutenção",
    descricao="Reforma bebedouro — curral B", valor=380.0, obs=""
))
lancamentos.append(dict(
    data=d(20), tipo="despesa", categoria="Manutenção", cat="Manutenção",
    descricao="Mangueira e acessórios lavagem", valor=145.0, obs=""
))

# Venda de animal
lancamentos.append(dict(
    data=d(35), tipo="receita", categoria="Venda de Animal", cat="Venda de Animal",
    descricao="Venda Garrote Neguinho — Frigorífico", valor=2800.0, obs=""
))

# Serviço veterinário
lancamentos.append(dict(
    data=d(10), tipo="despesa", categoria="Veterinário", cat="Veterinário",
    descricao="Visita Dr. Paulo — diagnóstico e procedimentos", valor=350.0, obs=""
))

for l in lancamentos:
    doc = l.copy()
    doc["registrado_por"] = "seed"
    doc["ts"] = datetime.datetime.now().isoformat()
    coll("financeiro").add(doc)

print(f"  {len(lancamentos)} lancamentos financeiros inseridos")

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════
print("\nInserindo config...")

configs = {
    "nome_fazenda":    "Fazenda Santa Clara",
    "preco_leite":     "2.55",
    "custo_por_litro": "1.18",
    "meta_producao":   "900",
    "responsavel_vet": "Dr. Paulo Silva",
    "cnpj":            "12.345.678/0001-90",
    "municipio":       "Uberaba — MG",
    "contato":         "(34) 99999-0000",
}
for chave, valor in configs.items():
    coll("config").document(chave).set({"chave": chave, "valor": valor})

print(f"  {len(configs)} configuracoes inseridas")

# ══════════════════════════════════════════════════════════════════════════════
# ESTOQUE
# ══════════════════════════════════════════════════════════════════════════════
print("\nInserindo estoque...")

estoque = [
    dict(item="Ração Concentrada",  qtd=850.0,  un="kg",     custo_unit=2.30),
    dict(item="Silagem de Milho",   qtd=4200.0, un="kg",     custo_unit=0.28),
    dict(item="Sal Mineral",        qtd=120.0,  un="kg",     custo_unit=3.50),
    dict(item="Ocitocina",          qtd=18.0,   un="dose",   custo_unit=4.20),
    dict(item="Ivermectina",        qtd=5.0,    un="frasco", custo_unit=32.00),
    dict(item="Penicilina G",       qtd=12.0,   un="frasco", custo_unit=18.50),
    dict(item="Vacina Aftosa",      qtd=25.0,   un="dose",   custo_unit=2.80),
    dict(item="Prostaglandina",     qtd=8.0,    un="dose",   custo_unit=15.00),
    dict(item="Antibiótico Mastite",qtd=6.0,    un="bisnaga",custo_unit=12.00),
]
for e in estoque:
    coll("estoque").add(e)

print(f"  {len(estoque)} itens de estoque inseridos")

# ── Resumo ────────────────────────────────────────────────────────────────────
print(f"""
=== SEED CONCLUIDO ===
Fazenda ID : {FAZENDA_ID}
Animais    : {len(animais_data)}
Producao   : {count_prod} registros (35 dias)
Sanitario  : {len(sanitarios)} procedimentos
Financeiro : {len(lancamentos)} lancamentos (90 dias)
Config     : {len(configs)} parametros
Estoque    : {len(estoque)} itens
""")

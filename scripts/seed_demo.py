"""
Seed de fazenda demo para demonstração ao cliente.
Cria conta Firebase + dados fictícios realistas no Firestore.

Uso: python3 /opt/milkshow/scripts/seed_demo.py
"""
import os, sys, datetime, random, time
sys.path.insert(0, '/opt/milkshow')
os.environ.setdefault('GOOGLE_APPLICATION_CREDENTIALS', '/opt/milkshow/firebase_key.json')

import firebase_admin
from firebase_admin import credentials, auth as fb_auth, firestore

if not firebase_admin._apps:
    firebase_admin.initialize_app(credentials.Certificate('/opt/milkshow/firebase_key.json'))

db = firestore.client()

# ── CREDENCIAIS DA DEMO ──────────────────────────────────────
DEMO_EMAIL = "demo@milkshow.com.br"
DEMO_SENHA = "Demo@2026"
DEMO_NOME  = "Fazenda Três Irmãos"

# ── CRIAR USUÁRIO NO FIREBASE AUTH ──────────────────────────
print(f"Criando usuário Firebase: {DEMO_EMAIL}")
try:
    user = fb_auth.get_user_by_email(DEMO_EMAIL)
    print(f"  Usuário já existe: {user.uid}")
    # Atualiza senha
    fb_auth.update_user(user.uid, password=DEMO_SENHA)
except fb_auth.UserNotFoundError:
    user = fb_auth.create_user(
        email=DEMO_EMAIL,
        password=DEMO_SENHA,
        display_name="Demo MilkShow",
    )
    print(f"  Criado com uid: {user.uid}")

UID   = user.uid
FID   = UID  # fazenda_id = uid para novos usuários

# ── CRIAR FAZENDA E USUÁRIO NO FIRESTORE ────────────────────
print("Criando fazenda e usuário no Firestore...")
db.collection("fazendas").document(FID).set({
    "nome":        DEMO_NOME,
    "owner_uid":   UID,
    "owner_email": DEMO_EMAIL,
    "created_at":  datetime.datetime.now().isoformat(),
    "plano":       "beta",
})
db.collection("users").document(UID).set({
    "email":      DEMO_EMAIL,
    "fazenda_id": FID,
    "nome":       "Demo MilkShow",
    "created_at": datetime.datetime.now().isoformat(),
    "permissoes": ["admin"],
})

def coll(nome):
    return db.collection("fazendas").document(FID).collection(nome)

# ── CONFIG ──────────────────────────────────────────────────
print("Configurando fazenda...")
for chave, valor in [
    ("nome_fazenda",   DEMO_NOME),
    ("preco_leite",    "3.75"),
    ("custo_por_litro","1.30"),
    ("meta_producao",  "950"),
    ("vet",            "Dr. Marcos Ferreira"),
    ("municipio",      "Governador Valadares — MG"),
    ("telefone",       "(33) 99210-4455"),
    ("cnpj",           "12.345.678/0001-99"),
]:
    coll("config").add({"chave": chave, "valor": valor})

# ── ANIMAIS ─────────────────────────────────────────────────
print("Cadastrando animais...")
animais = [
    {"nome":"Estrela",   "raca":"Girolando",  "status":"Lactação", "sexo":"Fêmea", "nascimento":"2019-03-12", "mae":"Princesa"},
    {"nome":"Rainha",    "raca":"Holandesa",  "status":"Lactação", "sexo":"Fêmea", "nascimento":"2020-07-08", "mae":"Beleza"},
    {"nome":"Mimosa",    "raca":"Girolando",  "status":"Lactação", "sexo":"Fêmea", "nascimento":"2021-01-22", "mae":"Estrela"},
    {"nome":"Pintada",   "raca":"Jersey",     "status":"Lactação", "sexo":"Fêmea", "nascimento":"2020-11-05", "mae":""},
    {"nome":"Docinha",   "raca":"Holandesa",  "status":"Seca",     "sexo":"Fêmea", "nascimento":"2018-06-30", "mae":""},
    {"nome":"Moreninha", "raca":"Girolando",  "status":"Gestação", "sexo":"Fêmea", "nascimento":"2021-09-14", "mae":"Rainha"},
    {"nome":"Faceira",   "raca":"Jersey",     "status":"Novilha",  "sexo":"Fêmea", "nascimento":"2023-04-03", "mae":"Pintada"},
    {"nome":"Guerreira", "raca":"Girolando",  "status":"Lactação", "sexo":"Fêmea", "nascimento":"2019-08-18", "mae":""},
]
animal_ids = {}
for a in animais:
    ts, ref = coll("animais").add({**a, "ts": datetime.datetime.now().isoformat()})
    animal_ids[a["nome"]] = ref.id
    print(f"  + {a['nome']} ({a['status']})")

# ── PRODUÇÃO — 30 dias ──────────────────────────────────────
print("Gerando histórico de produção (30 dias)...")
lact_animais = [a for a in animais if a["status"] == "Lactação"]
hoje = datetime.date.today()
random.seed(42)

prod_por_animal = {
    "Estrela":  (22, 3),
    "Rainha":   (19, 2),
    "Mimosa":   (15, 2),
    "Pintada":  (13, 2),
    "Guerreira":(17, 2),
}

for d in range(29, -1, -1):
    data = (hoje - datetime.timedelta(days=d)).isoformat()
    for animal, (media, std) in prod_por_animal.items():
        for turno in ["manhã", "tarde"]:
            litros = round(max(6, random.gauss(media / 2, std / 2)), 1)
            coll("producao").add({
                "data":         data,
                "nome_animal":  animal,
                "id_animal":    animal_ids.get(animal, ""),
                "leite":        litros,
                "turno":        turno,
                "racao":        round(random.uniform(2.5, 4.5), 1),
                "origem":       "app",
            })

print("  30 dias × 5 vacas × 2 turnos = 300 registros")

# ── FINANCEIRO — 30 dias ────────────────────────────────────
print("Gerando lançamentos financeiros...")
ini_mes = hoje.replace(day=1)
lancamentos = [
    # Receitas
    {"data": (ini_mes + datetime.timedelta(days=4)).isoformat(),  "tipo":"receita",  "cat":"Venda de Leite",       "categoria":"Venda de Leite",       "desc":"Venda quinzenal — Laticínio Boa Safra",   "valor":4218.75},
    {"data": (ini_mes + datetime.timedelta(days=19)).isoformat(), "tipo":"receita",  "cat":"Venda de Leite",       "categoria":"Venda de Leite",       "desc":"Venda quinzenal — Laticínio Boa Safra",   "valor":4031.25},
    # Despesas
    {"data": ini_mes.isoformat(),                                  "tipo":"despesa",  "cat":"Mão de Obra",          "categoria":"Mão de Obra",          "desc":"Salário João Peão — junho",                "valor":1800.00},
    {"data": ini_mes.isoformat(),                                  "tipo":"despesa",  "cat":"Mão de Obra",          "categoria":"Mão de Obra",          "desc":"Salário Carlos Ajudante — junho",           "valor":1400.00},
    {"data": (ini_mes + datetime.timedelta(days=2)).isoformat(),   "tipo":"despesa",  "cat":"Ração e Alimentação",  "categoria":"Ração e Alimentação",  "desc":"Concentrado proteico 50sc — Agropecuária",  "valor":920.00},
    {"data": (ini_mes + datetime.timedelta(days=2)).isoformat(),   "tipo":"despesa",  "cat":"Ração e Alimentação",  "categoria":"Ração e Alimentação",  "desc":"Milho triturado 200kg",                     "valor":320.00},
    {"data": (ini_mes + datetime.timedelta(days=8)).isoformat(),   "tipo":"despesa",  "cat":"Veterinário",          "categoria":"Veterinário",          "desc":"Visita Dr. Marcos + vacinas rebanho",       "valor":380.00},
    {"data": (ini_mes + datetime.timedelta(days=10)).isoformat(),  "tipo":"despesa",  "cat":"Energia",              "categoria":"Energia",              "desc":"Conta de energia elétrica — CEMIG",         "valor":510.00},
    {"data": (ini_mes + datetime.timedelta(days=12)).isoformat(),  "tipo":"despesa",  "cat":"Combustível",          "categoria":"Combustível",          "desc":"Diesel bomba ordenha + trator",             "valor":280.00},
    {"data": (ini_mes + datetime.timedelta(days=15)).isoformat(),  "tipo":"despesa",  "cat":"Medicamento / Sanitário","categoria":"Medicamento / Sanitário","desc":"Ivermectina + antibiótico rebanho",        "valor":195.00},
    {"data": (ini_mes + datetime.timedelta(days=20)).isoformat(),  "tipo":"despesa",  "cat":"Manutenção",           "categoria":"Manutenção",           "desc":"Reparo bomba de ordenha",                   "valor":350.00},
]
for l in lancamentos:
    l["origem"] = "app"
    coll("financeiro").add(l)
print(f"  {len(lancamentos)} lançamentos criados")

# ── SANITÁRIO ───────────────────────────────────────────────
print("Criando protocolos sanitários...")
san_base = (hoje - datetime.timedelta(days=20)).isoformat()
protocolos = [
    {"tipo":"Vacina", "animal":"Estrela",   "protocolo":"Aftosa — 3ª dose semestral",  "dose":"2mL", "via":"SC", "responsavel":"Dr. Marcos Ferreira", "executado":True,  "data":san_base},
    {"tipo":"Vacina", "animal":"Rainha",    "protocolo":"Aftosa — 3ª dose semestral",  "dose":"2mL", "via":"SC", "responsavel":"Dr. Marcos Ferreira", "executado":True,  "data":san_base},
    {"tipo":"Vacina", "animal":"Mimosa",    "protocolo":"Brucelose — reforço anual",   "dose":"2mL", "via":"SC", "responsavel":"Dr. Marcos Ferreira", "executado":True,  "data":(hoje - datetime.timedelta(days=15)).isoformat()},
    {"tipo":"Exame",  "animal":"Moreninha", "protocolo":"Diagnóstico gestação (60d)",  "dose":"",   "via":"",   "responsavel":"Dr. Marcos Ferreira", "executado":True,  "data":(hoje - datetime.timedelta(days=10)).isoformat()},
    {"tipo":"Vacina", "animal":"Docinha",   "protocolo":"Carrapaticida — tratamento",  "dose":"10mL","via":"Pour-on","responsavel":"João Peão",        "executado":False, "data":hoje.isoformat()},
    {"tipo":"Exame",  "animal":"Guerreira", "protocolo":"Revisão pós-parto (45d)",     "dose":"",   "via":"",   "responsavel":"Dr. Marcos Ferreira", "executado":False, "data":(hoje + datetime.timedelta(days=3)).isoformat()},
]
for p in protocolos:
    coll("sanitario").add(p)
print(f"  {len(protocolos)} protocolos criados")

# ── ESTOQUE ─────────────────────────────────────────────────
print("Criando estoque do armazém...")
estoque = [
    {"item":"Ivermectina 1%",       "qtd":45,   "un":"mL",  "categoria":"Medicamento",   "custo_medio":0.85,  "min_alerta":20},
    {"item":"Penicilina G",         "qtd":12,   "un":"fr",  "categoria":"Medicamento",   "custo_medio":8.50,  "min_alerta":5},
    {"item":"Oxitocina 10UI",       "qtd":30,   "un":"mL",  "categoria":"Medicamento",   "custo_medio":1.20,  "min_alerta":15},
    {"item":"Vacina Aftosa",        "qtd":8,    "un":"fr",  "categoria":"Vacina",        "custo_medio":12.00, "min_alerta":3},
    {"item":"Concentrado Proteico", "qtd":1200, "un":"kg",  "categoria":"Ração",         "custo_medio":2.10,  "min_alerta":400},
    {"item":"Milho Triturado",      "qtd":850,  "un":"kg",  "categoria":"Ração",         "custo_medio":1.55,  "min_alerta":300},
    {"item":"Sal Mineral",          "qtd":120,  "un":"kg",  "categoria":"Suplemento",    "custo_medio":4.80,  "min_alerta":50},
    {"item":"Diesel",               "qtd":180,  "un":"L",   "categoria":"Combustível",   "custo_medio":6.40,  "min_alerta":80},
    {"item":"Luvas de Ordenha",     "qtd":4,    "un":"cx",  "categoria":"Outros",        "custo_medio":22.00, "min_alerta":2},
]
for e in estoque:
    coll("estoque").add(e)
print(f"  {len(estoque)} itens no estoque")

# ── BEZERROS ────────────────────────────────────────────────
print("Cadastrando bezerros...")
bezerros_data = [
    {"nome":"Estrelinha", "mae":"Estrela",  "nascimento":(hoje-datetime.timedelta(days=45)).isoformat(), "raca":"Girolando", "sexo":"Fêmea",  "status":"Bezerro"},
    {"nome":"Ragazzo",    "mae":"Rainha",   "nascimento":(hoje-datetime.timedelta(days=12)).isoformat(), "raca":"Holandesa", "sexo":"Macho",  "status":"Bezerro"},
]
for b in bezerros_data:
    coll("animais").add({**b, "ts": datetime.datetime.now().isoformat()})
    print(f"  + {b['nome']} ({b['sexo']})")

print()
print("=" * 55)
print("  DEMO CRIADA COM SUCESSO!")
print("=" * 55)
print(f"  Site:   https://milshow.com.br/app/")
print(f"  Login:  {DEMO_EMAIL}")
print(f"  Senha:  {DEMO_SENHA}")
print("=" * 55)
print()
print("  Dados da Fazenda Três Irmãos:")
print("  - 10 animais (8 vacas + 2 bezerros)")
print("  - 5 em lactação produzindo ~86L/dia")
print("  - 30 dias de histórico de produção")
print("  - R$8.250 receitas + despesas mensais")
print("  - 6 protocolos sanitários")
print("  - 9 itens no estoque")
print("=" * 55)

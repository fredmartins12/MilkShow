"""
MilkShow — Motor Nutricional
Banco de dados de insumos baseado em tabelas EMBRAPA/CNCPS para bovinos leiteiros
e funções de cálculo de rações por média ponderada.
"""

from typing import List, Dict, Optional
import re

# ─── BANCO DE DADOS NUTRICIONAL ──────────────────────────────────────────────
# Valores por kg de produto natural (tal-qual, não na MS)
# Campos: ms=%, ndt=%, pb=%, ca=%, p=%, emoji, sinonimos (para desambiguação)
INSUMOS: Dict[str, dict] = {
    # ── ENERGÉTICOS ──────────────────────────────────────────────────────────
    "Milho, grão":           { "ms": 87.0, "ndt": 78.0, "pb":  8.5, "ca": 0.04, "p": 0.28, "emoji": "🌽", "categoria": "Energético",    "sinonimos": ["milho", "milho grao", "milho inteiro", "milho em grao"] },
    "Milho, farelo":         { "ms": 88.0, "ndt": 73.0, "pb":  9.0, "ca": 0.04, "p": 0.33, "emoji": "🌽", "categoria": "Energético",    "sinonimos": ["farelo de milho", "farelo milho", "milho farelo"] },
    "Milho, silagem":        { "ms": 35.0, "ndt": 65.0, "pb":  7.0, "ca": 0.25, "p": 0.18, "emoji": "🌽", "categoria": "Volumoso",      "sinonimos": ["silagem de milho", "silagem milho", "silo de milho"] },
    "Sorgo, grão":           { "ms": 88.0, "ndt": 73.0, "pb":  8.5, "ca": 0.03, "p": 0.28, "emoji": "🌾", "categoria": "Energético",    "sinonimos": ["sorgo", "sorgo grao", "sorgo em grao"] },
    "Sorgo, silagem":        { "ms": 30.0, "ndt": 58.0, "pb":  6.5, "ca": 0.30, "p": 0.17, "emoji": "🌾", "categoria": "Volumoso",      "sinonimos": ["silagem de sorgo", "silagem sorgo"] },
    "Polpa cítrica, pelet":  { "ms": 88.0, "ndt": 74.0, "pb":  6.5, "ca": 1.77, "p": 0.12, "emoji": "🍊", "categoria": "Energético",    "sinonimos": ["polpa citrica", "polpa de laranja", "citrus pellet"] },
    "Cana-de-açúcar, colmo": { "ms": 28.0, "ndt": 56.0, "pb":  2.5, "ca": 0.16, "p": 0.08, "emoji": "🎋", "categoria": "Volumoso",      "sinonimos": ["cana", "cana de acucar", "cana fresca"] },
    "Bagaço de cana":        { "ms": 90.0, "ndt": 44.0, "pb":  1.5, "ca": 0.16, "p": 0.04, "emoji": "🎋", "categoria": "Volumoso",      "sinonimos": ["bagaco", "bagaco de cana"] },
    "Melaço de cana":        { "ms": 74.0, "ndt": 58.0, "pb":  4.0, "ca": 0.88, "p": 0.08, "emoji": "🍯", "categoria": "Energético",    "sinonimos": ["melaco", "melaço"] },
    "Glúten de milho, 21%":  { "ms": 90.0, "ndt": 83.0, "pb": 21.0, "ca": 0.04, "p": 0.37, "emoji": "🌽", "categoria": "Proteico",      "sinonimos": ["gluten de milho", "gluten milho", "germen de milho"] },
    "Caroço de algodão":     { "ms": 91.0, "ndt": 75.0, "pb": 22.0, "ca": 0.18, "p": 0.57, "emoji": "⚪", "categoria": "Energético",    "sinonimos": ["caroco de algodao", "caroco algodao", "whole cottonseed"] },

    # ── PROTEICOS ─────────────────────────────────────────────────────────────
    "Soja, farelo":          { "ms": 88.0, "ndt": 78.0, "pb": 44.0, "ca": 0.28, "p": 0.61, "emoji": "🫘", "categoria": "Proteico",      "sinonimos": ["farelo de soja", "soja farelo", "soja"] },
    "Soja, grão":            { "ms": 89.0, "ndt": 88.0, "pb": 35.0, "ca": 0.28, "p": 0.59, "emoji": "🫘", "categoria": "Proteico",      "sinonimos": ["grao de soja", "soja inteira", "soja grao"] },
    "Algodão, farelo 38%":   { "ms": 91.0, "ndt": 63.0, "pb": 38.0, "ca": 0.16, "p": 0.87, "emoji": "🪴", "categoria": "Proteico",      "sinonimos": ["farelo de algodao", "torta de algodao", "algodao farelo"] },
    "Girassol, farelo":      { "ms": 91.0, "ndt": 62.0, "pb": 32.0, "ca": 0.35, "p": 0.90, "emoji": "🌻", "categoria": "Proteico",      "sinonimos": ["farelo de girassol", "girassol farelo"] },
    "Farinha de peixe":      { "ms": 92.0, "ndt": 65.0, "pb": 58.0, "ca": 6.00, "p": 3.80, "emoji": "🐟", "categoria": "Proteico",      "sinonimos": ["farinha peixe", "fish meal"] },
    "Levedura seca":         { "ms": 93.0, "ndt": 75.0, "pb": 35.0, "ca": 0.17, "p": 0.47, "emoji": "🧫", "categoria": "Proteico",      "sinonimos": ["levedura", "levedura de cana"] },
    "Farelo de trigo":       { "ms": 88.0, "ndt": 65.0, "pb": 15.0, "ca": 0.10, "p": 0.92, "emoji": "🌾", "categoria": "Proteico",      "sinonimos": ["farelo trigo", "trigo farelo"] },
    "Ureia, pecuária":       { "ms": 99.0, "ndt":  0.0, "pb":281.0, "ca": 0.00, "p": 0.00, "emoji": "⚗️", "categoria": "NNP",           "sinonimos": ["ureia", "ureia pecuaria", "NN"], "observacao": "NNP: 1kg = 2,81kg PB equiv. Máx 1% da MS total" },

    # ── VOLUMOSOS ─────────────────────────────────────────────────────────────
    "Feno de coast-cross":   { "ms": 88.0, "ndt": 56.0, "pb":  9.0, "ca": 0.40, "p": 0.19, "emoji": "🌿", "categoria": "Volumoso",      "sinonimos": ["coast cross", "feno coast cross", "feno de bermuda"] },
    "Feno de tifton":        { "ms": 88.0, "ndt": 54.0, "pb":  9.5, "ca": 0.45, "p": 0.21, "emoji": "🌿", "categoria": "Volumoso",      "sinonimos": ["tifton", "feno tifton", "feno de tifton 85"] },
    "Capim napier picado":   { "ms": 19.0, "ndt": 55.0, "pb":  7.5, "ca": 0.36, "p": 0.28, "emoji": "🌿", "categoria": "Volumoso",      "sinonimos": ["napier", "elefante", "capim elefante", "capim napier"] },
    "Capim braquiaria":      { "ms": 23.0, "ndt": 50.0, "pb":  6.5, "ca": 0.30, "p": 0.18, "emoji": "🌿", "categoria": "Volumoso",      "sinonimos": ["braquiaria", "brachiaria", "capim braquiaria"] },
    "Palma forrageira":      { "ms": 11.0, "ndt": 62.0, "pb":  3.5, "ca": 2.60, "p": 0.13, "emoji": "🌵", "categoria": "Volumoso",      "sinonimos": ["palma", "palma forrageira"] },

    # ── MINERAIS / SUPLEMENTOS ────────────────────────────────────────────────
    "Calcário calcítico":    { "ms":100.0, "ndt":  0.0, "pb":  0.0, "ca":38.00, "p": 0.00, "emoji": "🪨", "categoria": "Mineral",       "sinonimos": ["calcario", "cal", "calcario calitico"] },
    "Fosfato bicálcico":     { "ms":100.0, "ndt":  0.0, "pb":  0.0, "ca":22.00, "p":18.00, "emoji": "⬜", "categoria": "Mineral",       "sinonimos": ["fosfato bicalcico", "fosfato", "fosfato bi-calcico"] },
    "Sal branco":            { "ms":100.0, "ndt":  0.0, "pb":  0.0, "ca": 0.00, "p": 0.00, "emoji": "🧂", "categoria": "Mineral",       "sinonimos": ["sal", "sal comum", "nacl", "cloreto de sodio"] },
    "Suplemento mineral":    { "ms":100.0, "ndt":  0.0, "pb":  0.0, "ca":14.00, "p": 8.00, "emoji": "💊", "categoria": "Mineral",       "sinonimos": ["mineral", "suplemento", "sal mineral", "premix"] },
    "Bicarbonato de sódio":  { "ms":100.0, "ndt":  0.0, "pb":  0.0, "ca": 0.00, "p": 0.00, "emoji": "🧪", "categoria": "Mineral",       "sinonimos": ["bicarbonato", "bicarb", "bicarbonato de sodio"] },
}

# ─── CATEGORIAS PARA EXIBIÇÃO ─────────────────────────────────────────────────
CATEGORIAS_ORDEM = ["Energético", "Proteico", "Volumoso", "NNP", "Mineral"]


# ─── DESAMBIGUAÇÃO — busca o insumo pelo termo digitado ───────────────────────
def buscar_insumo(termo: str) -> List[dict]:
    """
    Recebe um termo livre (ex: 'milho', 'farelo de soja') e retorna
    a lista de insumos que fazem match (pode ser >1 para desambiguação).
    Retorna lista de dicts com 'nome' e 'insumo'.
    """
    termo_n = _normalizar(termo)
    matches = []
    for nome, dados in INSUMOS.items():
        nome_n = _normalizar(nome)
        if termo_n in nome_n or nome_n in termo_n:
            matches.append({"nome": nome, "dados": dados})
            continue
        for sin in dados.get("sinonimos", []):
            if termo_n in _normalizar(sin) or _normalizar(sin) in termo_n:
                if not any(m["nome"] == nome for m in matches):
                    matches.append({"nome": nome, "dados": dados})
                break
    return matches


def match_exato(termo: str) -> Optional[tuple]:
    """
    Retorna (nome, dados) se houver exatamente 1 match.
    Retorna None se ambíguo ou não encontrado.
    """
    matches = buscar_insumo(termo)
    if len(matches) == 1:
        return matches[0]["nome"], matches[0]["dados"]
    return None


def _normalizar(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r'[áàãâä]', 'a', s)
    s = re.sub(r'[éèêë]', 'e', s)
    s = re.sub(r'[íìîï]', 'i', s)
    s = re.sub(r'[óòõôö]', 'o', s)
    s = re.sub(r'[úùûü]', 'u', s)
    s = re.sub(r'[ç]', 'c', s)
    s = re.sub(r'[^a-z0-9 ]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


# ─── MOTOR DE CÁLCULO ─────────────────────────────────────────────────────────
def calcular_racao(ingredientes: List[dict]) -> dict:
    """
    Calcula a composição nutricional de uma ração.

    ingredientes: lista de {"nome": str, "kg": float}

    Retorna dict com:
    - total_kg: peso total da ração
    - composicao: [{"nome", "kg", "pct", "ms_kg", "ndt_kg", "pb_kg", ...}]
    - nutrientes: {"ms", "ndt", "pb", "ca", "p"} em % na matéria natural
    - nutrientes_ms: {"ndt", "pb", "ca", "p"} em % na matéria seca
    - ms_total_kg: kg de matéria seca total
    - alertas: lista de avisos nutricionais
    """
    if not ingredientes:
        return {"erro": "Nenhum ingrediente fornecido"}

    total_kg = sum(i["kg"] for i in ingredientes)
    if total_kg <= 0:
        return {"erro": "Total de kg deve ser maior que zero"}

    # Acumula nutrientes (em kg absolutos)
    acc = {"ms": 0, "ndt": 0, "pb": 0, "ca": 0, "p": 0}
    composicao = []

    for item in ingredientes:
        nome = item["nome"]
        kg   = item["kg"]
        if nome not in INSUMOS:
            return {"erro": f"Insumo não encontrado: {nome}"}
        d = INSUMOS[nome]
        pct = (kg / total_kg) * 100

        # kg de cada nutriente neste ingrediente
        ms_kg  = kg * d["ms"]  / 100
        ndt_kg = ms_kg * d["ndt"] / 100   # NDT é % da MS
        pb_kg  = ms_kg * d["pb"]  / 100
        ca_kg  = kg * d["ca"]  / 100
        p_kg   = kg * d["p"]   / 100

        acc["ms"]  += ms_kg
        acc["ndt"] += ndt_kg
        acc["pb"]  += pb_kg
        acc["ca"]  += ca_kg
        acc["p"]   += p_kg

        composicao.append({
            "nome":    nome,
            "emoji":   d["emoji"],
            "kg":      round(kg, 3),
            "pct":     round(pct, 1),
            "ms_pct":  d["ms"],
            "ms_kg":   round(ms_kg, 3),
            "ndt_pct": d["ndt"],
            "pb_pct":  d["pb"],
            "ca_pct":  d["ca"],
            "p_pct":   d["p"],
        })

    ms_total_kg = acc["ms"]

    # % na matéria natural (por kg de ração)
    nutrientes = {
        "ms":  round(acc["ms"]  / total_kg * 100, 2),
        "ndt": round(acc["ndt"] / total_kg * 100, 2),
        "pb":  round(acc["pb"]  / total_kg * 100, 2),
        "ca":  round(acc["ca"]  / total_kg * 100, 2),
        "p":   round(acc["p"]   / total_kg * 100, 2),
    }

    # % na matéria seca (mais relevante para nutricionistas)
    if ms_total_kg > 0:
        nutrientes_ms = {
            "ndt": round(acc["ndt"] / ms_total_kg * 100, 2),
            "pb":  round(acc["pb"]  / ms_total_kg * 100, 2),
            "ca":  round(acc["ca"]  / ms_total_kg * 100, 2),
            "p":   round(acc["p"]   / ms_total_kg * 100, 2),
        }
    else:
        nutrientes_ms = {"ndt": 0, "pb": 0, "ca": 0, "p": 0}

    # Alertas nutricionais básicos para vacas em lactação
    alertas = []
    pb_ms = nutrientes_ms["pb"]
    ndt_ms = nutrientes_ms["ndt"]
    ca_n   = nutrientes["ca"]
    p_n    = nutrientes["p"]

    if pb_ms < 14:
        alertas.append({"tipo": "warn", "msg": f"PB na MS ({pb_ms}%) abaixo do mínimo para lactação (14-18%). Adicione proteína."})
    elif pb_ms > 20:
        alertas.append({"tipo": "info", "msg": f"PB na MS ({pb_ms}%) elevado. Pode causar desperdício e aumento de custo."})

    if ndt_ms < 65:
        alertas.append({"tipo": "warn", "msg": f"NDT na MS ({ndt_ms}%) baixo para lactação (65-72%). Aumente a energia."})
    elif ndt_ms > 78:
        alertas.append({"tipo": "warn", "msg": f"NDT na MS ({ndt_ms}%) muito alto. Risco de acidose ruminal."})

    if ca_n > 0 and p_n > 0:
        relacao_cap = ca_n / p_n
        if relacao_cap < 1.5:
            alertas.append({"tipo": "warn", "msg": f"Relação Ca:P ({relacao_cap:.1f}:1) abaixo do ideal (2:1). Adicione calcário."})
        elif relacao_cap > 4:
            alertas.append({"tipo": "info", "msg": f"Relação Ca:P ({relacao_cap:.1f}:1) elevada. Verifique fontes de fósforo."})

    # Verifica ureia
    ureia_items = [i for i in ingredientes if "reia" in i["nome"].lower()]
    if ureia_items:
        pct_ureia = sum(i["kg"] for i in ureia_items) / total_kg * 100
        if pct_ureia > 1.0:
            alertas.append({"tipo": "erro", "msg": f"Ureia ({pct_ureia:.1f}% da ração) acima do limite seguro (1%). Risco de intoxicação!"})

    return {
        "total_kg":      round(total_kg, 3),
        "ms_total_kg":   round(ms_total_kg, 3),
        "composicao":    composicao,
        "nutrientes":    nutrientes,
        "nutrientes_ms": nutrientes_ms,
        "alertas":       alertas,
    }


# ─── RANKING DE ANIMAIS ────────────────────────────────────────────────────────
def calcular_ranking(animais: list, producao: list, preco_leite: float,
                     custo_por_litro: float) -> dict:
    """
    Cruza dados de produção com custos para gerar rankings por animal.

    animais:         lista de dicts do Firestore (id, nome, status)
    producao:        lista de registros de produção (id_animal, nome_animal, leite, racao, data)
    preco_leite:     R$/litro
    custo_por_litro: custo operacional base R$/litro (configurado na fazenda)

    Retorna dict com tres listas ordenadas.
    """
    from collections import defaultdict
    from datetime import datetime, timedelta

    # Filtra últimos 30 dias
    hoje   = datetime.now().date()
    inicio = hoje - timedelta(days=30)
    prod_recente = [
        p for p in producao
        if p.get("data", "") >= str(inicio)
    ]

    # Agrega por animal
    por_animal = defaultdict(lambda: {"litros": 0, "racao_kg": 0, "registros": 0})
    for reg in prod_recente:
        chave = reg.get("nome_animal") or reg.get("id_animal", "?")
        por_animal[chave]["litros"]    += float(reg.get("leite", 0) or 0)
        por_animal[chave]["racao_kg"]  += float(reg.get("racao", 0) or 0)
        por_animal[chave]["registros"] += 1

    CUSTO_RACAO_KG = 1.20  # R$/kg padrão; idealmente viria da config

    lista = []
    for nome, dados in por_animal.items():
        litros   = dados["litros"]
        racao_kg = dados["racao_kg"]
        if litros <= 0:
            continue

        receita         = litros * preco_leite
        custo_racao     = racao_kg * CUSTO_RACAO_KG
        custo_op        = litros * custo_por_litro
        custo_total     = custo_racao + custo_op
        lucro           = receita - custo_total
        custo_por_litro_animal = custo_total / litros if litros > 0 else 0
        margem_pct      = ((receita - custo_total) / receita * 100) if receita > 0 else 0
        media_dia       = litros / 30

        lista.append({
            "nome":           nome,
            "litros":         round(litros, 1),
            "media_dia":      round(media_dia, 1),
            "racao_kg":       round(racao_kg, 1),
            "receita":        round(receita, 2),
            "custo_total":    round(custo_total, 2),
            "lucro":          round(lucro, 2),
            "custo_por_litro": round(custo_por_litro_animal, 2),
            "margem_pct":     round(margem_pct, 1),
        })

    if not lista:
        return {
            "producao":      [],
            "rentabilidade": [],
            "alerta_descarte": [],
            "periodo_dias":  30,
        }

    # Ranking 1: Produção (maior litros)
    ranking_producao = sorted(lista, key=lambda x: x["litros"], reverse=True)

    # Ranking 2: Rentabilidade (menor custo por litro)
    ranking_rent = sorted(lista, key=lambda x: x["custo_por_litro"])

    # Ranking 3: Alerta de Descarte (menor margem % ou lucro negativo)
    ranking_descarte = sorted(lista, key=lambda x: x["margem_pct"])

    return {
        "producao":        ranking_producao,
        "rentabilidade":   ranking_rent,
        "alerta_descarte": ranking_descarte,
        "periodo_dias":    30,
        "total_animais":   len(lista),
    }


def listar_insumos_por_categoria() -> list:
    """Retorna a lista de insumos agrupados por categoria para o frontend."""
    grupos = {}
    for nome, dados in INSUMOS.items():
        cat = dados.get("categoria", "Outros")
        if cat not in grupos:
            grupos[cat] = []
        grupos[cat].append({
            "nome":      nome,
            "emoji":     dados["emoji"],
            "ms":        dados["ms"],
            "ndt":       dados["ndt"],
            "pb":        dados["pb"],
            "ca":        dados["ca"],
            "p":         dados["p"],
            "categoria": cat,
        })
    # Ordena por categoria definida
    resultado = []
    for cat in CATEGORIAS_ORDEM:
        if cat in grupos:
            resultado.append({
                "categoria": cat,
                "itens": sorted(grupos[cat], key=lambda x: x["nome"]),
            })
    return resultado

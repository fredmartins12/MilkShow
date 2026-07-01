# MilkShow — Gestão Leiteira Enterprise

> **SaaS B2B para propriedades leiteiras.** PWA mobile-first para operação em campo + dashboard web gerencial, com bot WhatsApp integrado para registro por voz e texto.

🌐 **Produção:** [milshow.com.br/app](https://milshow.com.br/app/)

---

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Frontend / PWA | React 19 + Vite 8 + Tailwind CSS v4 |
| Backend | Python 3.12 + FastAPI |
| Banco de dados | Firebase Firestore (multi-tenant) |
| Bot WhatsApp | Evolution API / Z-API / Twilio |
| IA | Groq Whisper + Gemini 2.0 Flash + Claude Haiku |
| Infra | VPS Ubuntu, nginx, systemd, Let's Encrypt |

---

## Funcionalidades

### 📊 Dashboard BI
KPIs de produção (litros/dia, média diária), margem operacional, custo/litro, composição do rebanho, alertas automáticos e tarefas sanitárias.

### 🐄 Rebanho
Cadastro completo de animais com histórico de produção, status reprodutivo, curva de lactação e prontuário individual.

### 🥛 Produção
Registro de ordenhas por turno (manhã/tarde), histórico de 90 dias, gráficos por animal e exportação CSV.

### 💰 Financeiro
Fluxo de caixa com receitas e despesas, saldo do período, gráfico receita vs. despesa e categorização por centro de custo.

### 📦 Armazém
Controle de estoque de ração, medicamentos e insumos com alertas de estoque mínimo.

### 🏥 Sanidade & Veterinária
Protocolos sanitários (vacinas, exames, tratamentos, secagem, desmame, colostragem) com calendário de manejo.

### 👶 Berçário
Gestão de bezerros e novilhas, controle de colostragem e alertas de desmame.

### 🌿 Nutrição
Formulação de rações com base no banco nutricional CQBAL 4.0 (Embrapa/UFV) — 56+ ingredientes com PB, FDN, NDT, EM, Ca, P.

### 🤖 Bot WhatsApp
Registro de ordenhas, consultas e alertas diretamente pelo WhatsApp do produtor — por texto ou áudio transcrito via IA.

---

## Estrutura do Projeto

```
MilkShow/
├── mobile/                 # Frontend React PWA
│   └── src/
│       ├── tabs/           # TabBI, TabProducao, TabRebanho, TabFinanceiro…
│       ├── pages/          # Login, etc.
│       ├── ui.jsx          # Design system + tokens
│       └── api.js          # Chamadas para o backend
├── mobile_api.py           # FastAPI — rotas /api/v1/*
├── whatsapp_bot.py         # Bot WhatsApp + servidor principal
├── nutricao.py             # Motor de formulação de rações
├── deploy/
│   ├── deploy_frontend.sh  # Build + envio via tar/SSH
│   ├── milkshow-bot.service
│   └── nginx.conf
└── docs/
    ├── ingredientes_nutricionais.sql   # Banco nutricional (56 ingredientes)
    └── ingredientes_nutricionais.json
```

---

## Desenvolvimento Local

### Frontend

```bash
cd mobile
npm install
npm run dev
# Acesse: http://localhost:5173/app/
```

### Backend

```bash
# Requer Python 3.12+ e arquivo .env com credenciais Firebase
py -3 -m uvicorn whatsapp_bot:app --port 8000 --host 0.0.0.0 --reload
```

### Variáveis de ambiente (`.env`)

```env
GOOGLE_APPLICATION_CREDENTIALS=./firebase_key.json
FIREBASE_API_KEY=...
BOT_ADMIN_TOKEN=...
GROQ_API_KEY=...
GEMINI_API_KEY=...
```

---

## Deploy

### Frontend

```bash
bash deploy/deploy_frontend.sh
```

O script faz build, empacota em `.tar.gz` e envia via SSH para o servidor.

### Backend

```bash
# No servidor (via SSH)
cd /opt/milkshow && git pull origin main
systemctl restart milkshow-bot
```

---

## Arquitetura Multi-tenant

Todos os dados são isolados por fazenda no Firestore:

```
fazendas/{fazenda_id}/
  ├── animais/
  ├── producao/
  ├── sanitario/
  ├── financeiro/
  ├── estoque/
  ├── racoes/
  └── usuarios/
```

Nenhuma query acessa dados sem filtrar por `fazenda_id` extraído do JWT.

---

## Banco Nutricional

O módulo de nutrição usa dados do **CQBAL 4.0** (Tabelas Brasileiras de Composição de Alimentos para Ruminantes — Embrapa/UFV) e da planilha **Embrapa Gado de Corte** (J.M. da Silva), totalizando **56 ingredientes** com:

- Proteína Bruta (PB %), FDN %, NDT %, Energia Metabolizável (Mcal/kg), Ca %, P %
- Degradabilidade ruminal da PB (Degr. PB %)

Scripts de importação em `docs/ingredientes_nutricionais.sql` e `.json`.

---

## Licença

Proprietário — © 2026 MilkShow. Todos os direitos reservados.

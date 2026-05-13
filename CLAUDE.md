# MilkShow — Instruções para Claude Code

## Stack do Projeto

- **Backend:** FastAPI (`whatsapp_bot.py` + `mobile_api.py`), Python, Firebase Firestore
- **Frontend:** React 19 + Vite 8 PWA em `mobile/`, base path `/app/`
- **CSS:** Tailwind CSS v4 (CSS-first: `@import "tailwindcss"`, blocos `@theme`)
- **Auth:** JWT customizado HMAC-SHA256, secret `MkSh@dm1n#2024!`
- **Firebase:** multi-tenant `fazendas/{fazenda_id}/{collection}`
- **Python:** usar `py -3` (nunca `python` ou `python3`)
- **Servidor:** `py -3 -m uvicorn whatsapp_bot:app --port 8080 --host 0.0.0.0`

## Ferramentas Obrigatórias para Interface

Sempre que trabalhar em qualquer tarefa de UI/UX, design de componente, ou interface visual:

### 1. UI/UX Pro Max (Skill)
- **SEMPRE** invocar o skill `/ui-ux-pro-max` antes de criar ou refatorar componentes React
- Aplicar princípios: hierarquia visual, espaçamento generoso, micro-interações, paleta coerente
- Priorizar: mobile-first, acessibilidade, feedback visual imediato

### 2. Context7 (MCP — já instalado)
- **SEMPRE** usar `mcp__context7__resolve-library-id` + `mcp__context7__query-docs` para buscar documentação atualizada de qualquer biblioteca antes de escrever código
- Especialmente para: React, Tailwind v4, Recharts, Vite, FastAPI
- Nunca assumir sintaxe de memória — verificar na doc via Context7

### 3. Playwright MCP (já instalado)
- Usar para verificar visualmente componentes quando o servidor estiver rodando
- Capturar screenshots para validar layout antes de finalizar

## Padrões de Código

- Firestore `add()` retorna `(timestamp, DocumentReference)` — desempacotar como `_, ref = coll.add(doc)`
- Queries compostas Firestore (range + equality em campos diferentes) requerem índice composto — evitar; filtrar em Python
- `user.get("nome") or user.get("email") or user.get("tel", "")` para campos opcionais de usuário
- Tailwind v4: sem `tailwind.config.js`, usar `@theme` em CSS

## Estrutura de Abas (`mobile/src/tabs/`)

| Arquivo | Módulo | Descrição |
|---|---|---|
| TabBI.jsx | bi | Dashboard principal com gráficos |
| TabProducao.jsx | producao | Registro e histórico de produção |
| TabVet.jsx | vet | Registros veterinários |
| TabSanidade.jsx | sanidade | Protocolos sanitários |
| TabBercario.jsx | bercario | Bezerros e novilhas |
| TabFinanceiro.jsx | financeiro | Lançamentos financeiros |
| TabConfig.jsx | config | Configurações da fazenda |

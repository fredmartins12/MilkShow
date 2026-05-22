# MilkShow — Documentação Técnica do Sistema

**Versão:** 1.0  
**Data:** Maio de 2026  
**Autor:** Frederico Martins  
**Repositório:** github.com/fredmartins12/MilkShow  

---

## Sumário

1. [Descrição Geral do Sistema](#1-descrição-geral-do-sistema)
2. [Estudo de Viabilidade](#2-estudo-de-viabilidade)
3. [Histórias de Usuário](#3-histórias-de-usuário)
4. [Requisitos Funcionais](#4-requisitos-funcionais)
5. [Requisitos Não Funcionais](#5-requisitos-não-funcionais)
6. [Casos de Uso](#6-casos-de-uso)
7. [Descrição de Casos de Uso](#7-descrição-de-casos-de-uso)
8. [Arquitetura de Alto Nível](#8-arquitetura-de-alto-nível)
9. [Diagrama de Classes](#9-diagrama-de-classes)
10. [Diagrama de Sequências](#10-diagrama-de-sequências)
11. [Diagrama de Estados](#11-diagrama-de-estados)
12. [Plano de Testes](#12-plano-de-testes)
13. [Telas do Sistema](#13-telas-do-sistema)

---

## 1. Descrição Geral do Sistema

### 1.1 Identificação do Sistema

**Nome:** MilkShow  
**Tipo:** Sistema de gestão integrada para fazendas leiteiras  
**Modalidade:** SaaS multi-tenant com acesso web, mobile (PWA) e por WhatsApp  

### 1.2 Objetivo

O MilkShow é um sistema de gestão completa voltado para pequenas e médias propriedades leiteiras. Seu objetivo central é digitalizar e centralizar o controle produtivo, sanitário, reprodutivo e financeiro da fazenda, permitindo que o produtor tome decisões baseadas em dados reais. A grande diferença do MilkShow em relação a planilhas e sistemas convencionais é a possibilidade de registrar eventos diretamente pelo WhatsApp usando linguagem natural, sem necessidade de abrir qualquer aplicativo.

### 1.3 Escopo

O sistema abrange:

- **Gestão do rebanho:** cadastro de animais, acompanhamento de status produtivo e reprodutivo.
- **Controle de ordenha:** registros individuais e em lote, análise de produção por animal e por período.
- **Saúde e sanidade:** vacinações, tratamentos, vermifugações e protocolos sanitários recorrentes.
- **Gestão reprodutiva:** inseminações, diagnósticos de prenhez, partos e secagem.
- **Berçário:** acompanhamento de bezerros, colostro, aleitamento e desmame.
- **Financeiro:** receitas, despesas, vendas de leite e animais, custo por litro e rentabilidade.
- **Armazém:** controle de estoque de insumos com custo médio ponderado.
- **Inteligência de negócios (BI):** dashboards, gráficos, rankings, curva de lactação, previsão de produção.
- **Bot WhatsApp com IA:** registro de eventos por voz, texto e foto, consultas sobre a fazenda em linguagem natural.
- **Painel Mobile:** acesso simplificado via PWA React para uso em campo.
- **Protocolos Sanitários:** agendamento e acompanhamento de procedimentos periódicos.

### 1.4 Usuários do Sistema

| Perfil | Descrição | Forma de Acesso |
|--------|-----------|-----------------|
| **Produtor Rural** | Proprietário da fazenda. Registra eventos e consulta informações no dia a dia. Pouco familiarizado com tecnologia. | WhatsApp (principal), App Mobile |
| **Gestor / Técnico** | Responsável pela análise gerencial da fazenda. Acessa relatórios, BI e configurações. | Web (Streamlit) |
| **Administrador do Sistema** | Cadastra fazendas, associa números de telefone, gerencia multi-tenant. | Web (página Configurações) |

### 1.5 Contexto de Uso

O produtor rural, durante sua rotina diária, envia mensagens de voz ou texto pelo WhatsApp informando eventos como ordenhas, compras, gastos e reproduções. O sistema interpreta essas mensagens com Inteligência Artificial e persiste os dados no Firebase. O gestor acessa o painel web para análise dos indicadores, relatórios e tomada de decisão.

---

## 2. Estudo de Viabilidade

### 2.1 Viabilidade Técnica

O sistema é tecnicamente viável dado que:

- **Python** é linguagem madura com vasto ecossistema de bibliotecas para ciência de dados, ML e web.
- **Streamlit** permite criar dashboards interativos de dados com código Python mínimo, sem frontend dedicado.
- **Firebase Firestore** oferece banco de dados NoSQL escalável, com SDK Python e sincronização em tempo real.
- **Evolution API** (auto-hospedada) e cascata com Z-API e Twilio garantem integração confiável com WhatsApp.
- **LLMs de terceiros** (Groq, Gemini, Claude Anthropic) proveem NLP de alta qualidade sem necessidade de treinamento próprio.
- A infraestrutura de produção é um VPS Hetzner (Ubuntu, R$50–100/mês), suficiente para dezenas de fazendas.

**Principais riscos técnicos:**

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Instabilidade da API do WhatsApp | Média | Alto | Cascata: Evolution → Z-API → Twilio |
| Limites de rate do LLM gratuito | Média | Médio | Cascata: Groq → Gemini → Claude (pago) |
| Perda de dados Firebase | Baixa | Alto | Backups automáticos do Firestore |
| Latência alta na transcrição de áudio | Baixa | Baixo | Groq Whisper processa em <3s |

### 2.2 Viabilidade Econômica

**Custos de operação estimados (mensal):**

| Item | Custo Estimado |
|------|---------------|
| VPS Hetzner (2 vCPU / 4 GB) | R$ 80–120/mês |
| Firebase Firestore (Spark) | Gratuito até cota |
| Groq API (LLaMA 70B) | Gratuito — 14.400 req/dia |
| Gemini 2.0 Flash | Gratuito — ~1M tokens/dia |
| Claude Haiku (fallback) | ~R$ 0–30/mês (uso marginal) |
| Evolution API | Gratuito (auto-hospedado) |
| Z-API (backup WhatsApp) | R$ 97/mês (opcional) |
| **Total mínimo** | **~R$ 80/mês** |

**Modelo de receita:** assinatura por fazenda (estimado R$ 150–300/mês por cliente). Ponto de equilíbrio: 1 cliente.

### 2.3 Viabilidade Operacional

O sistema foi projetado para operar com mínima intervenção técnica:
- Deploy automatizado via GitHub Actions (CI/CD) a cada push na branch `main`.
- Reinicialização automática do bot via `systemctl` em caso de falha.
- Interface web sem instalação, acessível em qualquer navegador.
- Bot WhatsApp não exige instalação de aplicativo pelo produtor.

### 2.4 Cronograma de Desenvolvimento

| Fase | Descrição | Status |
|------|-----------|--------|
| Fase 1 | Módulos base: Rebanho, Ordenha, Financeiro, Sanidade | Concluído |
| Fase 2 | Bot WhatsApp com NLP, multi-tenant | Concluído |
| Fase 3 | BI & Inteligência, Berçário, Armazém, Calendário | Concluído |
| Fase 4 | App Mobile (React PWA), API REST | Concluído |
| Fase 5 | Protocolos Sanitários, Painel Mobile | Concluído |
| Fase 6 | CI/CD automatizado, infraestrutura Hetzner | Concluído |
| Fase 7 | Expansão de clientes, monitoramento, SLA | Em andamento |

---

## 3. Histórias de Usuário

### 3.1 Bot WhatsApp

**HU-01** — Como produtor rural, quero enviar uma mensagem de texto simples pelo WhatsApp informando a produção do dia para que ela seja registrada sem precisar abrir nenhum aplicativo.

**HU-02** — Como produtor rural, quero enviar uma foto do quadro de produção (com vários animais e litros) para que o sistema reconheça e registre todos automaticamente.

**HU-03** — Como produtor rural, quero enviar um áudio descrevendo uma compra de ração para que o sistema transcreva, entenda e registre no estoque.

**HU-04** — Como produtor rural, quero perguntar "quanto produzi essa semana?" pelo WhatsApp e receber a resposta com dados reais da fazenda.

**HU-05** — Como produtor rural, quero que o bot me avise quando eu perguntar "o que tenho pra fazer hoje?" sobre pendências como ordenhas não registradas, vacinas vencidas e partos previstos.

### 3.2 Rebanho e Reprodução

**HU-06** — Como gestor, quero cadastrar um novo animal (nascimento ou compra) com nome, raça, data de nascimento e mãe, para manter o registro genealógico do rebanho.

**HU-07** — Como gestor, quero registrar uma inseminação artificial com a data, tipo (IA ou touro) e tourador, para acompanhar o calendário reprodutivo.

**HU-08** — Como gestor, quero visualizar quais vacas estão em atraso de inseminação (mais de 45 dias pós-parto sem inseminar) para tomar providências.

**HU-09** — Como gestor, quero saber quais vacas precisam ser secadas nos próximos dias com base na data prevista de parto e no período de secagem configurado.

### 3.3 Controle de Ordenha

**HU-10** — Como operador, quero registrar a produção de uma vaca específica (litros e ração consumida) para ter controle individual de produtividade.

**HU-11** — Como gestor, quero ver um heatmap de produção por dia e por animal para identificar padrões e quedas de produtividade.

**HU-12** — Como gestor, quero visualizar a curva de lactação de cada vaca comparada ao modelo teórico (Wood) para identificar animais abaixo do esperado.

### 3.4 Sanidade e Protocolos

**HU-13** — Como gestor, quero registrar a aplicação de um medicamento com nome, dose, animal (ou rebanho todo) e custo, para controlar gastos sanitários.

**HU-14** — Como gestor, quero cadastrar um protocolo de vacinação recorrente (ex: aftosa a cada 6 meses) para que o sistema me lembre automaticamente da próxima aplicação.

**HU-15** — Como gestor, quero executar um protocolo sanitário com um clique, registrando automaticamente o evento no histórico e atualizando a próxima data.

### 3.5 Financeiro

**HU-16** — Como gestor, quero registrar a venda mensal de leite (litros e valor recebido) para controlar a receita da fazenda.

**HU-17** — Como gestor, quero ver o saldo financeiro do mês atual, com total de receitas e despesas, no painel financeiro.

**HU-18** — Como gestor, quero saber o custo por litro de cada vaca no mês para identificar animais não rentáveis.

### 3.6 Armazém

**HU-19** — Como operador, quero registrar a entrada de ração no estoque (produto, quantidade, valor pago) para controlar o inventário e o custo médio.

**HU-20** — Como operador, quero ver o estoque atual com quantidade disponível e custo médio por item para planejar compras.

### 3.7 BI e Inteligência

**HU-21** — Como gestor, quero ver um dashboard com os principais KPIs da fazenda (produção, receita, custo/L, saldo) para ter uma visão geral rápida.

**HU-22** — Como gestor, quero um ranking das vacas mais e menos lucrativas do mês para embasar decisões de descarte ou investimento.

**HU-23** — Como gestor, quero uma previsão de produção para os próximos 7 dias baseada no histórico recente.

### 3.8 Berçário

**HU-24** — Como operador, quero registrar o nascimento de um bezerro com data, mãe, sexo e peso, para acompanhar seu desenvolvimento.

**HU-25** — Como operador, quero ver a lista de bezerros que ainda não receberam colostro (até 2 dias de vida) para não perder o prazo crítico.

### 3.9 Configurações

**HU-26** — Como administrador, quero associar um número de WhatsApp a uma fazenda para habilitar o bot para aquele produtor.

**HU-27** — Como gestor, quero configurar o preço do leite, custo da ração e nome da fazenda para que os cálculos de rentabilidade usem valores corretos.

---

## 4. Requisitos Funcionais

### RF001 — Cadastro de Animais
O sistema deve permitir o cadastro de animais com os campos: nome, raça, sexo, data de nascimento, data de entrada, mãe (referência a outro animal), status (Lactação, Seca, Novilha, Bezerro, Vendido, Descartado) e observações.

### RF002 — Controle de Status Produtivo
O sistema deve controlar o status produtivo de cada animal, atualizando-o automaticamente quando eventos reprodutivos são registrados (parto → Lactação, secagem → Seca).

### RF003 — Registro de Ordenha Individual
O sistema deve registrar a produção de leite por animal por dia, incluindo: data, animal, litros, ração consumida (kg), turno (manhã/tarde/noite) e observações.

### RF004 — Registro de Ordenha em Lote (PRODUCAO_MULTIPLA)
O sistema deve aceitar registros de múltiplos animais em uma única operação, seja por texto formatado, áudio, foto de quadro ou tabela mensal.

### RF005 — Interpretação de Imagens com IA
O sistema deve usar visão computacional para interpretar fotos de quadros de produção (CASO A: múltiplos animais/dia; CASO B: um animal/múltiplas datas) e notas fiscais de compra.

### RF006 — Transcrição de Áudio
O sistema deve transcrever mensagens de voz recebidas pelo WhatsApp usando Groq Whisper, com fallback para OpenAI Whisper.

### RF007 — Bot WhatsApp com NLP
O sistema deve processar mensagens de texto em linguagem natural pelo WhatsApp, identificando a intenção do produtor e coletando os dados necessários via diálogo conversacional.

### RF008 — Persistência de Estado Conversacional
O bot deve manter o estado da conversa entre mensagens, incluindo tipo do registro em andamento, dados coletados parcialmente, e contexto do último registro salvo (para evitar duplicatas).

### RF009 — Registro Financeiro
O sistema deve registrar lançamentos financeiros com: data, descrição, categoria (Venda de Leite, Venda de Animais, Ração/Nutrição, Medicamento, Infraestrutura, Mão de Obra, Energia, Compra de Animais, Outros), valor e tipo (receita/despesa).

### RF010 — Controle de Estoque
O sistema deve controlar o estoque de insumos (ração, medicamentos, etc.) com: produto, quantidade, unidade, custo unitário, custo médio ponderado histórico.

### RF011 — Baixa Automática de Estoque
O sistema deve dar baixa automática no estoque quando um gasto sanitário é registrado com quantidade utilizada.

### RF012 — Registro de Eventos Reprodutivos
O sistema deve registrar: inseminação artificial (data, tourador, tipo), cobertura natural, diagnóstico de prenhez (positivo/negativo), parto (data, bezerro), secagem e aborto.

### RF013 — Cálculo de Datas Reprodutivas
O sistema deve calcular automaticamente: data prevista de parto (inseminação + 283 dias), data de secagem prevista (parto previsto − 60 dias), data de diagnóstico sugerida (inseminação + 30 dias).

### RF014 — Agenda Automática
O sistema deve gerar uma agenda diária e semanal com: ordenhas pendentes, diagnósticos de prenhez vencidos, inseminações em atraso (PVE > 45 dias), secagens urgentes, partos previstos, colostro pendente, desmames.

### RF015 — Alertas Automáticos
O sistema deve gerar alertas classificados em "crítico" e "atenção" visíveis no painel web e mobile, baseados na agenda automática.

### RF016 — Registro de Sanidade
O sistema deve registrar aplicações de medicamentos/vacinas com: data, tipo (Vacina, Vermífugo, Antibiótico, Hormônio, Casqueamento, Outros), produto, modo (individual/rebanho todo), animal, custo e observações.

### RF017 — Protocolos Sanitários Recorrentes
O sistema deve permitir o cadastro de protocolos periódicos com frequência em dias, alvo (animal, lote ou rebanho todo) e custo estimado. A execução atualiza automaticamente a próxima data e registra o evento no histórico.

### RF018 — Dashboard de BI
O sistema deve exibir KPIs macro (produção total, receita, despesa, saldo, custo/L, lucro/L), gráficos de produção diária (barras), composição de custos (pizza) e tendência.

### RF019 — Raio-X Individual por Animal
O sistema deve calcular e exibir, por animal e por período: produção total, receita estimada, custo de ração, custo veterinário direto, custo fixo rateado, custo/L e lucro/L.

### RF020 — Ranking de Animais
O sistema deve ordenar os animais por diferentes métricas: produção total, custo/L, lucro/L, margem.

### RF021 — Curva de Lactação
O sistema deve gerar a curva de lactação de cada animal e compará-la ao modelo teórico de Wood (305 dias).

### RF022 — Previsão de Produção
O sistema deve gerar previsão de produção para os próximos 7 dias usando regressão polinomial sobre o histórico.

### RF023 — Heatmap de Produção
O sistema deve exibir um heatmap com produção diária por animal no período selecionado.

### RF024 — Calendário de Eventos
O sistema deve exibir um calendário mensal com eventos de reprodução, sanidade e partos, com filtros por tipo de evento.

### RF025 — Berçário
O sistema deve controlar bezerros (nascimento, mãe, sexo, peso), registrar eventos (colostro, vacinas de bezerro, pesagens) e alertar sobre desmame (90 dias de vida) e colostro pendente (≤ 2 dias de vida).

### RF026 — Exportação de Dados
O sistema deve permitir exportação de relatórios em formato Excel (.xlsx) e PDF.

### RF027 — App Mobile (PWA)
O sistema deve fornecer um Progressive Web App React com login por PIN, consulta de KPIs, registro de produção e finanças otimizados para toque.

### RF028 — API REST para Mobile
O sistema deve expor endpoints REST autenticados via JWT para o app mobile: login, dashboard, produção, financeiro, estoque, animais, agenda, alertas.

### RF029 — Multi-Tenant
O sistema deve suportar múltiplas fazendas com dados completamente isolados no Firebase, identificadas por `fazenda_id`.

### RF030 — Autenticação Web
O sistema deve exigir autenticação para acesso às páginas web (Firebase Auth ou PIN configurado).

### RF031 — Configuração por Fazenda
O sistema deve permitir configurar por fazenda: nome, preço do leite, custo da ração, período de secagem, período PVE.

### RF032 — Painel Mobile Streamlit
O sistema deve oferecer uma versão do painel principal otimizada para tela pequena (layout "centered"), com KPIs do dia, semana, mês, alertas e top vacas.

---

## 5. Requisitos Não Funcionais

### RNF001 — Desempenho
- O bot deve responder mensagens de texto simples em menos de 5 segundos.
- Transcrição de áudio deve ser concluída em menos de 10 segundos.
- O painel web deve carregar dados iniciais em menos de 3 segundos.

### RNF002 — Disponibilidade
- O sistema deve ter disponibilidade mínima de 95% por mês.
- O bot deve retomar operação automaticamente em caso de reinicialização (systemctl restart).

### RNF003 — Escalabilidade
- A arquitetura multi-tenant com Firebase Firestore deve suportar expansão para centenas de fazendas sem alteração de código.
- A cascata de IA (Groq → Gemini → Claude) garante operação mesmo com indisponibilidade de fornecedores individuais.

### RNF004 — Segurança
- Chaves de API (ANTHROPIC_API_KEY, GROQ_API_KEY, etc.) devem ser armazenadas em variáveis de ambiente, nunca em código ou repositório.
- O arquivo `firebase_key.json` deve constar no `.gitignore`.
- Tokens JWT para o app mobile devem expirar em 30 dias com validação de assinatura HMAC-SHA256.
- PINs de usuário mobile armazenados como hash SHA-256.

### RNF005 — Usabilidade
- O bot deve entender mensagens com erros ortográficos, gírias e regionalismos do produtor rural.
- O produtor não deve precisar seguir um formato rígido de mensagem.
- O sistema deve pedir confirmação antes de salvar qualquer registro.

### RNF006 — Manutenibilidade
- O código Python deve seguir organização modular: `utils.py` (funções compartilhadas), `whatsapp_bot.py` (bot + API), `pages/` (uma página por módulo).
- Deploy automatizado via GitHub Actions a cada push em `main`.

### RNF007 — Compatibilidade
- O app web deve funcionar nos navegadores Chrome, Firefox, Edge e Safari (últimas 2 versões).
- O PWA mobile deve funcionar em Android 9+ e iOS 14+.

### RNF008 — Portabilidade
- O sistema deve poder ser migrado entre provedores de VPS sem alteração de código.
- Toda configuração sensível gerenciada via variáveis de ambiente.

### RNF009 — Confiabilidade dos Dados
- Todos os registros persistidos no Firebase devem incluir timestamp de criação.
- O bot não deve salvar dados sem confirmação explícita do produtor ("sim" / "confirmar").
- O bot deve preservar contexto do último registro salvo para evitar duplicatas em seguimento de conversa.

### RNF010 — Privacidade
- Dados de cada fazenda devem ser isolados por `fazenda_id`, sem acesso cruzado.
- Números de telefone são a chave de identificação do produtor e não devem ser expostos em logs públicos.

---

## 6. Casos de Uso

### 6.1 Atores

| Ator | Descrição |
|------|-----------|
| **Produtor** | Usuário final que interage pelo WhatsApp ou App Mobile |
| **Gestor** | Usuário com acesso ao painel web completo |
| **Administrador** | Configura o sistema e gerencia cadastros |
| **Bot IA** | Sistema automatizado que processa mensagens |
| **Firebase** | Sistema externo de persistência |
| **LLM** | Sistema externo de inteligência artificial (Groq/Gemini/Claude) |

### 6.2 Diagrama de Casos de Uso — Bot WhatsApp

```
┌─────────────────────────────────────────────────────────────────┐
│                     Sistema MilkShow — Bot                       │
│                                                                   │
│   ┌────────────────────────────┐                                 │
│   │ UC01: Registrar Produção   │◄──────────────┐                │
│   └────────────────────────────┘               │                │
│   ┌────────────────────────────┐               │                │
│   │ UC02: Registrar Compra     │◄──────────────┤                │
│   └────────────────────────────┘               │                │
│   ┌────────────────────────────┐               │ «uses»         │
│   │ UC03: Registrar Gasto      │◄──────────────┤                │
│   └────────────────────────────┘  [Produtor]──►│                │
│   ┌────────────────────────────┐               │                │
│   │ UC04: Registrar Reprodução │◄──────────────┤                │
│   └────────────────────────────┘               │                │
│   ┌────────────────────────────┐               │                │
│   │ UC05: Consultar Fazenda    │◄──────────────┤                │
│   └────────────────────────────┘               │                │
│   ┌────────────────────────────┐               │                │
│   │ UC06: Enviar Foto/Áudio    │◄──────────────┘                │
│   └────────────────────────────┘                                 │
│                                                                   │
│        ┌─────────────────────────┐                               │
│        │ UC07: Processar com IA  │  ◄── [LLM] (Groq/Gemini/Claude) │
│        └─────────────────────────┘                               │
│        ┌─────────────────────────┐                               │
│        │ UC08: Persistir Dados   │  ◄── [Firebase]               │
│        └─────────────────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

### 6.3 Diagrama de Casos de Uso — Painel Web

```
┌──────────────────────────────────────────────────────────────────┐
│                    Sistema MilkShow — Web                         │
│                                                                    │
│   ┌────────────────────────────┐                                  │
│   │ UC10: Acessar Dashboard BI │◄────────────────┐               │
│   └────────────────────────────┘                 │               │
│   ┌────────────────────────────┐                 │               │
│   │ UC11: Gerenciar Rebanho    │◄────────────────┤               │
│   └────────────────────────────┘                 │               │
│   ┌────────────────────────────┐                 │               │
│   │ UC12: Gerenciar Financeiro │◄────────────────┤  [Gestor]     │
│   └────────────────────────────┘                 │               │
│   ┌────────────────────────────┐                 │               │
│   │ UC13: Controlar Sanidade   │◄────────────────┤               │
│   └────────────────────────────┘                 │               │
│   ┌────────────────────────────┐                 │               │
│   │ UC14: Gerenciar Estoque    │◄────────────────┤               │
│   └────────────────────────────┘                 │               │
│   ┌────────────────────────────┐                 │               │
│   │ UC15: Configurar Sistema   │◄────────────────┘               │
│   └────────────────────────────┘            [Administrador]──►UC15│
└──────────────────────────────────────────────────────────────────┘
```

---

## 7. Descrição de Casos de Uso

### UC01 — Registrar Produção pelo WhatsApp

**Atores:** Produtor, Bot IA, Firebase  
**Pré-condição:** Número de telefone cadastrado e associado a uma fazenda.  
**Pós-condição:** Registro de produção salvo na coleção `producao` do Firebase.

**Fluxo Principal:**
1. Produtor envia mensagem de texto (ex: "Joana deu 22 litros hoje manhã").
2. Bot normaliza o número de telefone e identifica a fazenda (`_find_fazenda`).
3. Bot carrega contexto: lista de animais, estoque, dados da fazenda.
4. Bot envia ao LLM (Groq → Gemini → Claude) o histórico + system prompt.
5. LLM identifica intenção `PRODUCAO_LEITE` e coleta campos necessários.
6. LLM retorna JSON `{"tipo":"PRODUCAO_LEITE", "estado":"CONFIRMANDO", "dados":{...}, "texto":"Confirma? Joana — 22L, manhã."}`.
7. Bot envia confirmação ao produtor.
8. Produtor responde "sim".
9. Bot salva registro no Firebase e responde com resumo.
10. Bot reseta conversa, preservando contexto do último registro.

**Fluxo Alternativo A — Múltiplas Vacas:**
3a. Produtor envia "Joana 22, Moreninha 18, Pintada 15" ou foto de quadro.
3b. Bot identifica `PRODUCAO_MULTIPLA` com lista de animais (CASO A: múltiplos animais/mesmo dia).
3c. Bot salva um registro por animal na mesma transação.

**Fluxo Alternativo B — Tabela Mensal:**
3a. Produtor envia foto de tabela com datas e litros de uma vaca.
3b. Vision IA classifica como `[TABELA MENSAL]` (CASO B: um animal/múltiplas datas).
3c. Bot coleta o nome do animal (não o cabeçalho da tabela).
3d. Bot salva um registro por linha da tabela.

**Fluxo de Exceção:**
- Se o animal citado não existe no rebanho → bot avisa e pergunta se quer cadastrá-lo.
- Se litros > 1.000 por animal → bot questiona o valor.

---

### UC02 — Registrar Compra de Produto

**Atores:** Produtor, Bot IA, Firebase  
**Pré-condição:** Número cadastrado.  
**Pós-condição:** Item adicionado/atualizado na coleção `estoque` com custo médio ponderado. Lançamento de despesa criado em `financeiro`.

**Fluxo Principal:**
1. Produtor envia "comprei 5 sacos de ração por R$300".
2. LLM identifica `COMPRA_PRODUTO`: produto="ração", qtd=5, valor_unit=60.
3. Bot confirma com produtor.
4. `_salvar` atualiza o estoque com custo médio ponderado: `(qtd_atual × custo_atual + qtd_nova × custo_novo) / (qtd_atual + qtd_nova)`.
5. Lançamento financeiro registrado como despesa categoria "Ração / Nutrição".

**Fluxo Alternativo — Nota Fiscal:**
2a. Produtor envia foto de nota fiscal.
2b. Claude Vision extrai: fornecedor, data, lista de itens com quantidade e valor.
2c. Bot processa como múltiplos `COMPRA_PRODUTO` (array `itens`).

---

### UC03 — Consultar Dados da Fazenda

**Atores:** Produtor, Bot IA, Firebase  
**Pré-condição:** Número cadastrado.  
**Pós-condição:** Resposta com dados reais enviada ao produtor.

**Fluxo Principal:**
1. Produtor envia "quanto produzi essa semana?".
2. Bot detecta palavra-chave de consulta, carrega contexto completo (`_ctx_dados_fazenda`).
3. LLM recebe contexto com: rebanho, produção dos últimos 7 dias, financeiro do mês, estoque, reprodução recente, agenda e rentabilidade por animal.
4. LLM gera resposta em linguagem natural com dados específicos.
5. Estado retorna `CONSULTA` — histórico mantido para follow-up.

---

### UC10 — Acessar Dashboard de BI

**Atores:** Gestor  
**Pré-condição:** Usuário autenticado no painel web.  
**Pós-condição:** Dashboard exibido com dados do período selecionado.

**Fluxo Principal:**
1. Gestor acessa a página "BI e Inteligência".
2. Sistema carrega dados do Firebase (animais, produção, financeiro).
3. Sistema calcula KPIs usando `calcular_bi(df_prod, df_fin, ini, fim)`.
4. Exibe: produção total, receita estimada, despesa, saldo, custo/L, lucro/L.
5. Exibe gráficos: barras de produção diária, pizza de composição de custos.
6. Disponibiliza aba Rankings com scatter custo vs volume.
7. Gestor pode exportar relatório em Excel ou PDF.

---

### UC14 — Executar Protocolo Sanitário

**Atores:** Gestor  
**Pré-condição:** Protocolo cadastrado na lista de protocolos ativos.  
**Pós-condição:** Execução registrada em `protocolos_execucoes`, evento lançado em `sanitario`, próxima data atualizada.

**Fluxo Principal:**
1. Gestor acessa página "Protocolos Sanitários" → aba "Protocolos Ativos".
2. Sistema lista protocolos ordenados por proximidade da data de aplicação, com badge de cor (vencido/hoje/em breve/ok).
3. Gestor clica "Executar" no protocolo desejado.
4. Sistema registra execução em `protocolos_execucoes`.
5. Sistema lança evento em `sanitario` (tipo, produto, modo, custo).
6. Sistema atualiza `proxima_data = hoje + frequencia_dias`.
7. Sistema exibe confirmação e recarrega a página.

---

## 8. Arquitetura de Alto Nível

### 8.1 Visão Geral

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Camada de Clientes                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │  WhatsApp    │  │ Browser Web  │  │   Mobile (React PWA)     │   │
│  │  (Produtor)  │  │  (Gestor)    │  │   (Produtor/Gestor)      │   │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬──────────────┘   │
└─────────┼────────────────┼───────────────────────┼──────────────────┘
          │                │                        │
          ▼                ▼                        ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        Camada de Servidor (Hetzner VPS)               │
│  ┌────────────────────────────────┐  ┌──────────────────────────┐   │
│  │  FastAPI (porta 8080)          │  │  Streamlit (porta 8501)  │   │
│  │  ├── /webhook/evolution        │  │  ├── gestor.py           │   │
│  │  ├── /webhook/zapi             │  │  └── pages/ (12 módulos) │   │
│  │  ├── /webhook/whatsapp (Twilio)│  └──────────────────────────┘   │
│  │  └── /api/v1/* (Mobile API)    │                                  │
│  │       whatsapp_bot.py          │                                  │
│  └────────────────┬───────────────┘                                  │
│                   │                                                   │
│  ┌────────────────▼───────────────────────────────────────────────┐  │
│  │             Camada de Integração IA                             │  │
│  │  1º Groq LLaMA 3.3 70B (gratuito, 14.400 req/dia)             │  │
│  │  2º Gemini 2.0 Flash   (gratuito, ~1M tokens/dia)             │  │
│  │  3º Claude Haiku 4.5   (pago, fallback)                       │  │
│  │                                                                 │  │
│  │  Groq Whisper (transcrição de áudio — gratuito)                │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────────────────────────┐
│                   Firebase (Google Cloud)                             │
│  Firestore — banco NoSQL multi-tenant                                │
│  ├── registros_tel/{phone}     → mapeamento tel → fazenda            │
│  ├── conversas_bot/{tel}       → estado conversacional               │
│  ├── sugestoes_bot             → perguntas sem resposta              │
│  ├── config/ngrok_url          → URL pública do bot                  │
│  └── fazendas/{fazenda_id}/    → dados isolados por fazenda          │
│       ├── animais              → rebanho                             │
│       ├── producao             → ordenhas                            │
│       ├── financeiro           → lançamentos                         │
│       ├── sanitario            → sanidade e reprodução               │
│       ├── estoque              → armazém                             │
│       ├── protocolos_sanitarios                                      │
│       ├── protocolos_execucoes                                       │
│       └── config               → configurações por fazenda           │
└──────────────────────────────────────────────────────────────────────┘
```

### 8.2 Cascata de WhatsApp

```
Mensagem recebida
       │
       ▼
┌─────────────┐   falha   ┌─────────────┐   falha   ┌─────────────┐
│ Evolution   │──────────►│   Z-API     │──────────►│   Twilio    │
│ API (free)  │           │ (R$97/mês)  │           │ (por msg)   │
└─────────────┘           └─────────────┘           └─────────────┘
```

### 8.3 Fluxo de Processamento do Bot

```
Webhook recebe mensagem
       │
       ├─► áudio → Groq Whisper → texto transcrito
       ├─► imagem → Claude Vision → prefixo classificado + dados
       └─► texto → direto
              │
              ▼
       _normalizar_tel → _find_fazenda → carrega conversa
              │
              ▼
       _processar(tel, texto, fazenda_id)
              │
              ├─► TTL check: conversa > 2h → reset
              ├─► keyword check: consulta? → carrega contexto completo
              │
              ▼
       _chamar_claude(historico, animais, estoque, dados_fazenda, ultimo_salvo)
              │ Groq → Gemini → Claude (fallback)
              ▼
       Parse JSON da resposta
              │
              ├── estado=COLETANDO  → envia pergunta
              ├── estado=CONFIRMANDO → envia resumo para confirmar
              ├── estado=SALVAR     → _salvar(tipo, dados) → reseta conv
              ├── estado=CANCELAR   → reseta conversa
              ├── estado=CONSULTA   → envia resposta, mantém histórico
              └── estado=SEM_RESPOSTA → salva sugestão, informa produtor
```

### 8.4 Padrões Arquiteturais

| Padrão | Aplicação |
|--------|-----------|
| **Multi-tenant** | Dados isolados por `fazenda_id` no Firestore |
| **Cascata** | IA e WhatsApp com múltiplos provedores em fallback |
| **State Machine** | Estados de conversa do bot (idle/coletando/confirmando/salvar/...) |
| **Repository** | `_coll(fazenda_id, nome)` isola acesso ao Firestore |
| **Cache** | `@st.cache_resource` para conexão Firebase; TTL de 60s para dados |
| **Strategy** | Alternância entre provedores de IA conforme disponibilidade |

### 8.5 Infraestrutura de Deploy

```
GitHub (main branch)
       │
       │ push
       ▼
GitHub Actions (ubuntu-latest)
       │
       │ appleboy/ssh-action
       ▼
Hetzner VPS (178.104.252.193)
       │
       ├── git checkout origin/main -- [arquivos relevantes]
       ├── systemctl restart milkshow-bot
       └── verifica: systemctl is-active milkshow-bot

Processos ativos no VPS:
  ├── milkshow-bot.service  → uvicorn whatsapp_bot:app --port 8080
  └── streamlit             → streamlit run gestor.py --port 8501
```

---

## 9. Diagrama de Classes

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Entidades de Domínio                         │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────────────┐
│       Animal          │
├──────────────────────┤
│ doc_id: str           │
│ nome: str             │
│ raca: str             │
│ sexo: str             │
│ data_nasc: date       │
│ data_entrada: date    │
│ mae: str              │◄──────────────────────────┐
│ status: str           │                            │
│ obs: str              │              ┌─────────────┴───────────┐
└──────────┬───────────┘              │     EventoReprodutivo    │
           │ 1                         ├─────────────────────────┤
           │                           │ doc_id: str              │
           │ N                         │ animal: str              │
           ▼                           │ tipo: str (IA/cobertura  │
┌──────────────────────┐              │       /prenhez/parto/...) │
│    Producao           │              │ data: date               │
├──────────────────────┤              │ tourador: str            │
│ doc_id: str           │              │ resultado: str           │
│ data: date            │              │ obs: str                 │
│ id_animal: str        │              └──────────────────────────┘
│ nome_animal: str      │
│ leite: float (L)      │              ┌──────────────────────────┐
│ racao: float (kg)     │              │     EventoSanitario      │
│ turno: str            │              ├──────────────────────────┤
│ obs: str              │              │ doc_id: str              │
└──────────────────────┘              │ data: date               │
                                       │ tipo: str                │
┌──────────────────────┐              │ prod: str                │
│    Lancamento         │              │ modo: str (Individual/   │
├──────────────────────┤              │          Rebanho Todo)   │
│ doc_id: str           │              │ animal: str              │
│ data: date            │              │ custo: float             │
│ descricao: str        │              │ obs: str                 │
│ cat: str              │              └──────────────────────────┘
│ valor: float          │
│ tipo: str (rec/desp)  │              ┌──────────────────────────┐
└──────────────────────┘              │    ItemEstoque           │
                                       ├──────────────────────────┤
┌──────────────────────┐              │ doc_id: str              │
│  ProtocoloSanitario  │              │ item: str                │
├──────────────────────┤              │ qtd: float               │
│ doc_id: str           │              │ un: str                  │
│ nome: str             │              │ custo_unit: float        │
│ tipo: str             │              │ custo_medio: float       │
│ frequencia_dias: int  │              └──────────────────────────┘
│ proxima_data: date    │
│ ultima_data: date     │              ┌──────────────────────────┐
│ alvo: str             │              │     Conversa Bot         │
│ custo_estimado: float │              ├──────────────────────────┤
│ obs: str              │              │ tel: str (PK)            │
│ ativo: bool           │              │ historico: list[dict]    │
└──────────────────────┘              │ estado: str              │
                                       │ dados: dict              │
                                       │ tipo: str                │
┌──────────────────────┐              │ itens: list              │
│   RegistroTelefone   │              │ ultimo_salvo: dict        │
├──────────────────────┤              │ ts: datetime             │
│ phone: str (PK)       │              └──────────────────────────┘
│ fazenda_id: str       │
│ nome: str             │
│ ativo: bool           │
│ pin_hash: str         │
│ permissoes: list      │
└──────────────────────┘
```

### 9.1 Módulos Python

```
┌────────────────────────────────────────────────────────────────┐
│                         utils.py                               │
├────────────────────────────────────────────────────────────────┤
│ CONSTANTES                                                     │
│   DIAS_PVE=45, DIAS_DIAGNOSTICO=30, DIAS_SECAGEM=60           │
│   GESTACAO=283, DIAS_DESMAME=90                                │
│   PRECO_PADRAO_LEITE=2.50, FATOR_CONVERSAO=3.0               │
│   CATEGORIAS_FINANCEIRAS, TIPOS_SANITARIOS                     │
│                                                                │
│ FUNÇÕES                                                        │
│   init_firebase() → singleton Firebase Admin                  │
│   carregar_dados() → carrega coleções no session_state        │
│   get_config(chave, default) → lê configuração da fazenda     │
│   get_custo_racao() → custo médio ponderado do estoque        │
│   calcular_bi(df_prod, df_fin, ini, fim) → KPIs macro         │
│   processar_alertas() → lista alertas criticos/atencao        │
│   apply_theme() → CSS dark theme                              │
│   page_banner(icon, title, subtitle) → cabeçalho padrão       │
│   requer_autenticacao() → guard de autenticação               │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                      whatsapp_bot.py                           │
├────────────────────────────────────────────────────────────────┤
│ FastAPI app                                                    │
│                                                                │
│ FUNÇÕES AUXILIARES                                             │
│   _normalizar_tel(raw) → str                                  │
│   _variantes_tel(tel) → list[str]                             │
│   _find_fazenda(tel) → str (fazenda_id)                       │
│   _coll(fazenda_id, nome) → CollectionReference               │
│   _ctx_animais(fazenda_id) → str                              │
│   _ctx_estoque(fazenda_id) → str                              │
│   _ctx_dados_fazenda(fazenda_id) → str (contexto rico)        │
│   _buscar_no_estoque(fazenda_id, nome) → dict|None            │
│   _parse_float(v) → float                                     │
│   _clear_conv(tel, ultimo_salvo=None)                         │
│   _get_conv(tel) → dict                                       │
│                                                                │
│ ENVIO WHATSAPP (cascata)                                       │
│   _enviar_evolution(para, msg) → bool                         │
│   _enviar_zapi(para, msg) → bool                              │
│   _enviar_twilio(para, msg) → bool                            │
│   _enviar_whatsapp(para, msg) → bool                          │
│                                                                │
│ IA (cascata)                                                   │
│   _ia_groq(system, historico) → str|None                      │
│   _ia_gemini(system, historico) → str|None                    │
│   _ia_claude(system, historico) → str|None                    │
│   _chamar_claude(hist, animais, estoque, dados_fazenda,       │
│                  memoria, ultimo_salvo) → str                 │
│                                                                │
│ MULTIMIDIA                                                     │
│   _transcrever(audio_url, content_type) → str                 │
│   _ler_imagem(image_url, animais_str) → str                   │
│                                                                │
│ PROCESSAMENTO                                                  │
│   _processar(tel, texto, fazenda_id) → str                    │
│   _salvar(tipo, dados, fazenda_id) → str                      │
│                                                                │
│ ENDPOINTS                                                      │
│   POST /webhook/whatsapp (Twilio)                             │
│   POST /webhook/evolution                                     │
│   POST /webhook/zapi                                          │
│   GET  /status                                                 │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                       mobile_api.py                            │
├────────────────────────────────────────────────────────────────┤
│ APIRouter prefix="/api/v1"                                     │
│                                                                │
│ AUTH                                                           │
│   POST /auth/login     → JWT com fazenda_id, tel, permissoes  │
│   POST /auth/google    → Google ID Token → JWT                │
│                                                                │
│ DADOS (requer JWT)                                             │
│   GET  /dashboard      → KPIs, últimas produções, alertas     │
│   GET  /animais        → lista animais ativos                 │
│   POST /producao       → registrar ordenha                    │
│   GET  /producao       → histórico de produção                │
│   GET  /financeiro     → lançamentos do mês                   │
│   POST /financeiro     → registrar lançamento                 │
│   GET  /estoque        → lista estoque                        │
│   POST /estoque        → registrar entrada                    │
│   GET  /agenda         → tarefas pendentes                    │
│   GET  /alertas        → alertas ativos                       │
└────────────────────────────────────────────────────────────────┘
```

---

## 10. Diagrama de Sequências

### 10.1 Fluxo Completo de Registro por WhatsApp (Produção)

```
Produtor     Evolution API      FastAPI(bot)        Groq LLM         Firebase
    │               │                │                  │                │
    │──"Joana 22L"──►               │                  │                │
    │               │──POST /webhook/evolution──►       │                │
    │               │                │                  │                │
    │               │                │──_find_fazenda()─────────────────►│
    │               │                │◄─fazenda_id──────────────────────│
    │               │                │                  │                │
    │               │                │──_get_conv()─────────────────────►│
    │               │                │◄─historico + estado──────────────│
    │               │                │                  │                │
    │               │                │──_ctx_animais()──────────────────►│
    │               │                │◄─lista animais───────────────────│
    │               │                │                  │                │
    │               │                │──_ia_groq(system, hist)──────────►│
    │               │                │◄─JSON {tipo:PRODUCAO_LEITE,       │
    │               │                │        estado:CONFIRMANDO,        │
    │               │                │        dados:{animal:Joana,22L}}──│
    │               │                │                  │                │
    │               │                │──salva estado CONFIRMANDO────────►│
    │               │◄──"Confirma? Joana — 22L"─────────│                │
    │◄──"Confirma? Joana — 22L"────│                  │                │
    │               │                │                  │                │
    │──"sim"────────►               │                  │                │
    │               │──POST /webhook/evolution──►       │                │
    │               │                │──_ia_groq(...)───────────────────►│
    │               │                │◄─{estado:SALVAR}─────────────────│
    │               │                │                  │                │
    │               │                │──_salvar(PRODUCAO_LEITE, dados)──►│
    │               │                │◄─doc_id criado───────────────────│
    │               │                │                  │                │
    │               │                │──_clear_conv(tel, ultimo_salvo)──►│
    │               │◄──"Joana: 22L registrado!"──────────────────────  │
    │◄──"Joana: 22L registrado!"───│                  │                │
    │               │                │                  │                │
```

### 10.2 Fluxo de Foto de Nota Fiscal

```
Produtor     Evolution API      FastAPI(bot)      Claude Vision      Firebase
    │               │                │                  │                │
    │──[foto NF]────►               │                  │                │
    │               │──POST /webhook/evolution──►       │                │
    │               │                │                  │                │
    │               │                │──_ler_imagem(url, animais)───────►│
    │               │                │◄─"[NOTA FISCAL] Fornecedor: X    │
    │               │                │   Item1: ração 50kg R$300        │
    │               │                │   Item2: vacina 10ml R$50"        │
    │               │                │                  │                │
    │               │                │──_processar("prefixo...", faz)    │
    │               │                │──_ia_groq(system, hist)──────────►(Groq)
    │               │                │◄─{tipo:COMPRA_PRODUTO,           │
    │               │                │   estado:CONFIRMANDO,            │
    │               │                │   itens:[{ração,50kg,R$300},     │
    │               │                │          {vacina,10ml,R$50}]}    │
    │               │◄──"2 itens: ração 50kg + vacina. Confirma?"──────  │
    │◄──"Confirma?"────────────────│                  │                │
    │──"sim"────────►               │                  │                │
    │               │               │──_salvar (loop itens)────────────►│
    │◄──"2 itens salvos no estoque."│                  │                │
```

### 10.3 Fluxo de Autenticação Mobile

```
App Mobile          FastAPI /api/v1          Firebase
    │                     │                     │
    │──POST /auth/login   │                     │
    │  {tel, pin}─────────►                     │
    │                     │──busca registros_tel/{tel}──►│
    │                     │◄─{fazenda_id, pin_hash}──────│
    │                     │                     │
    │                     │ verifica SHA256(pin)==pin_hash
    │                     │                     │
    │                     │──gera JWT {tel, fazenda_id, exp=+30d}
    │◄──{token, nome, fazenda_id}──────────────│
    │                     │                     │
    │──GET /dashboard     │                     │
    │  Authorization: Bearer <token>────────────►
    │                     │ valida JWT (HMAC-SHA256)
    │                     │──carrega dados fazenda──────►│
    │◄──{kpis, alertas, animais}───────────────│
```

---

## 11. Diagrama de Estados

### 11.1 Estados da Conversa do Bot

```
                           ┌─────────┐
                           │  idle   │◄─────────────────────────────────┐
                           └────┬────┘                                   │
                                │ mensagem recebida                      │
                                ▼                                        │
                     ┌──────────────────┐                               │
                     │   detecta tipo   │                               │
                     └────────┬─────────┘                               │
                              │                                          │
           ┌──────────────────┼──────────────────┐                     │
           ▼                  ▼                   ▼                     │
    ┌─────────────┐   ┌──────────────┐   ┌──────────────┐             │
    │ COLETANDO   │   │  CONFIRMANDO │   │   CONSULTA   │─────────────►│
    └──────┬──────┘   └──────┬───────┘   └──────────────┘   follow-up  │
           │                 │                                           │
           │ mais dados      │ "sim"                                     │
           │ necessários     ▼                                           │
           │         ┌───────────────┐                                  │
           └────────►│     SALVAR    │──────────────────────────────────┤
                     └───────────────┘                                  │
                                                                        │
    ┌─────────────────────────────────────────┐                        │
    │ "cancelar" / "reiniciar" / qualquer estado│──────────────────────►│
    └─────────────────────────────────────────┘    CANCELAR            │
                                                                        │
    ┌─────────────────────────────────────────┐                        │
    │ LLM não entende / fora do escopo        │──────────────────────►│
    └─────────────────────────────────────────┘  SEM_RESPOSTA          │
                                                                        │
    ┌─────────────────────────────────────────┐                        │
    │ TTL: conversa > 2h em estado não-idle   │──────────────────────►│
    └─────────────────────────────────────────┘    TIMEOUT             │
```

### 11.2 Estados de Status do Animal

```
                  ┌──────────┐
                  │ Bezerro  │
                  └────┬─────┘
                       │ 90 dias (desmame)
                       ▼
                  ┌──────────┐
     ┌────────────│ Novilha  │
     │            └────┬─────┘
     │                 │ parto
     │                 ▼
     │            ┌──────────┐
     │  secagem   │ Lactação │◄─────────────────┐
     │◄───────────│          │                   │
     │            └──────────┘                   │
     │                                           │ parto
     ▼                                           │
┌──────────┐                               ┌────┴─────┐
│   Seca   │──────────────────────────────►│ Gestante │
└──────────┘         prenhez+              └──────────┘
     │
     ▼
┌──────────┐
│ Vendido  │ (estado terminal)
└──────────┘
┌──────────┐
│Descartado│ (estado terminal)
└──────────┘
```

### 11.3 Ciclo de Vida de um Protocolo Sanitário

```
                ┌──────────────┐
                │  Cadastrado  │
                └──────┬───────┘
                       │ ativo=True
                       ▼
          ┌────────────────────────┐
          │       Aguardando       │
          │  (proxima_data futura) │
          └────────────┬───────────┘
                       │ proxima_data <= hoje
                       ▼
          ┌────────────────────────┐
          │    Vencido/Próximo     │ (badge vermelho/amarelo na UI)
          └────────────┬───────────┘
                       │ clique em "Executar"
                       ▼
          ┌────────────────────────┐
          │      Executado         │
          │ proxima_data += freq   │──────────► volta para Aguardando
          └────────────┬───────────┘
                       │ ativo=False
                       ▼
          ┌────────────────────────┐
          │       Inativo          │◄──── botão "Reativar" ──────────┐
          └────────────────────────┘                                  │
                                    ──── reativar ─────────────────────┘
```

---

## 12. Plano de Testes

### 12.1 Testes Funcionais do Bot

| ID | Caso de Teste | Entrada | Resultado Esperado |
|----|---------------|---------|-------------------|
| T001 | Registro produção texto simples | "Joana 22 litros" | Estado CONFIRMANDO, dados={animal:Joana, leite:22} |
| T002 | Produção com erro ortográfico | "joaninha deu 20 litro" | Identifica animal mais próximo, coleta confirmação |
| T003 | Produção múltipla texto | "Joana 22, Moreninha 18, Pintada 15" | PRODUCAO_MULTIPLA com 3 itens |
| T004 | Foto quadro produção (CASO A) | [imagem: 3 vacas e litros] | Classifica [PRODUCAO DO DIA], extrai animais e litros |
| T005 | Foto tabela mensal (CASO B) | [imagem: 1 vaca / 30 datas] | Classifica [TABELA MENSAL], pede nome do animal |
| T006 | Nome na tabela ≠ animal cadastrado | Cabeçalho "Fobinha" (produtor) | Não assume como animal, usa "Rebanho" |
| T007 | Compra de ração por áudio | [áudio: "comprei 5 sacos de ração por 300"] | Transcreve, extrai produto/qtd/valor |
| T008 | Foto nota fiscal | [imagem: NF com 3 itens] | Extrai fornecedor, 3 itens com qtd e valor |
| T009 | Consulta produção semanal | "quanto produzi essa semana?" | Resposta com litros dos últimos 7 dias |
| T010 | Agenda do dia | "o que tenho pra fazer hoje?" | Lista ordenhas pendentes, secagens, partos |
| T011 | Cancelamento | "cancelar" em qualquer estado | Estado reset para idle |
| T012 | Timeout 2h | conversa sem resposta > 2h | Reset automático ao receber próxima mensagem |
| T013 | Duplicata pós-salvar | "usei todos em abril" após compra salva | NÃO registra de novo, usa contexto ultimo_salvo |
| T014 | Compra multi-item | "comprei milho 60kg R$180 e soja 40kg R$120" | 2 lançamentos separados no estoque |
| T015 | Animal não cadastrado | "Margarida 18L" (animal inexistente) | Avisa que animal não existe, pergunta se cadastra |

### 12.2 Testes de Persistência

| ID | Caso de Teste | Resultado Esperado |
|----|---------------|--------------------|
| T020 | Custo médio ponderado no estoque | Entrada: 10kg@2,00 + 10kg@3,00 → custo_medio=2,50 |
| T021 | Cálculo de data prevista de parto | IA em 01/01/2026 → parto previsto em 10/10/2026 (283 dias) |
| T022 | Data de secagem prevista | Parto 10/10 → secar em 11/08 (60 dias antes) |
| T023 | Isolamento multi-tenant | Dados de fazenda_A não visíveis para fazenda_B |
| T024 | Protocolo execução atualiza data | Protocolo freq=180d executado hoje → proxima_data=hoje+180 |

### 12.3 Testes de Interface

| ID | Caso de Teste | Resultado Esperado |
|----|---------------|--------------------|
| T030 | Dashboard BI — sem dados | Mensagem informativa sem erros Python |
| T031 | Exportação Excel | Arquivo .xlsx baixado com dados do período |
| T032 | Exportação PDF | Arquivo .pdf baixado com relatório formatado |
| T033 | Calendário — filtro por tipo | Somente eventos do tipo selecionado exibidos |
| T034 | Heatmap — período sem dados | Heatmap vazio sem erro |
| T035 | Protocolo vencido | Badge vermelho exibido, botão "Executar" disponível |

### 12.4 Testes de Segurança

| ID | Caso de Teste | Resultado Esperado |
|----|---------------|--------------------|
| T040 | JWT expirado | GET /api/v1/dashboard → 401 Unauthorized |
| T041 | JWT inválido (tampered) | GET /api/v1/dashboard → 401 Unauthorized |
| T042 | PIN incorreto no mobile | POST /auth/login → 401 "PIN incorreto" |
| T043 | Tel não cadastrado | POST /auth/login → 404 "Número não cadastrado" |
| T044 | firebase_key.json no git | Verificar .gitignore inclui firebase_key.json |

### 12.5 Testes de Integração

| ID | Caso de Teste | Resultado Esperado |
|----|---------------|--------------------|
| T050 | GitHub Actions deploy | Push em main → Actions verde → bot reiniciado no VPS |
| T051 | Evolution webhook recebe e responde | Envio real pelo WhatsApp → resposta < 5s |
| T052 | Fallback Groq → Gemini | Simular falha do Groq → Gemini responde |
| T053 | Transcrição áudio real | Envio de áudio .ogg pelo WhatsApp → transcrição correta |

---

## 13. Telas do Sistema

### 13.1 Estrutura de Navegação

```
gestor.py (Home / Login)
├── 1_📊_BI_e_Inteligência.py
│   ├── Tab: Dashboard Geral
│   ├── Tab: Raio-X Individual
│   ├── Tab: Relatório Comparativo
│   ├── Tab: Rankings
│   ├── Tab: Curva de Lactação
│   ├── Tab: Previsão
│   └── Tab: Heatmap
├── 2_🧬_Veterinária.py
│   ├── Tab: Reprodução (registro de eventos)
│   └── Tab: Histórico Reprodutivo
├── 3_💉_Sanidade.py
│   ├── Tab: Registros Sanitários
│   └── Tab: Histórico
├── 4_👶_Berçário.py
│   ├── Tab: Bezerros Ativos
│   ├── Tab: Registros de Desenvolvimento
│   └── Tab: Alertas do Berçário
├── 5_💰_Financeiro_360.py
│   ├── Tab: Lançamentos
│   ├── Tab: Resumo Mensal
│   └── Tab: Venda de Leite
├── 6_📦_Armazém.py
│   ├── Tab: Estoque Atual
│   └── Tab: Movimentações
├── 7_🐄_Rebanho_Geral.py
│   ├── Tab: Lista de Animais
│   ├── Tab: Cadastrar Animal
│   └── Tab: Score de Saúde do Rebanho
├── 8_📅_Calendário.py
│   └── Calendário mensal com filtros
├── 9_🥛_Controle_de_Ordenha.py
│   ├── Tab: Registrar Ordenha
│   ├── Tab: Histórico
│   └── Tab: Análise por Animal
├── 10_⚙️_Configurações.py
│   ├── Tab: Fazenda (nome, preço leite, etc.)
│   ├── Tab: Bot IA (cadastro de tel, iniciar/parar)
│   └── Tab: Sistema (backup, reset)
├── 11_📱_Painel_Mobile.py
│   └── KPIs compactos + alertas (layout centered)
└── 12_🔬_Protocolos_Sanitários.py
    ├── Tab: Protocolos Ativos
    ├── Tab: Novo Protocolo
    └── Tab: Histórico de Execuções
```

### 13.2 Padrão Visual das Telas

Todas as telas seguem o padrão dark theme definido em `apply_theme()` no `utils.py`:

- **Fundo:** `#0f172a` (azul muito escuro)
- **Cards:** `rgba(255,255,255,0.04)` com borda sutil
- **Texto principal:** `#f1f5f9`
- **Texto secundário:** `#94a3b8`
- **Acento azul:** `#3b82f6`
- **Sucesso/verde:** `#4ade80`
- **Atenção/amarelo:** `#fbbf24`
- **Crítico/vermelho:** `#f87171`
- **Fonte:** Inter (Google Fonts)

### 13.3 Componentes Reutilizáveis

| Componente | Função | Exemplo de Uso |
|------------|--------|---------------|
| `page_banner(icon, title, sub)` | Cabeçalho com gradiente e subtítulo | Todas as páginas |
| `st.metric(label, value, delta)` | KPI card nativo Streamlit | Dashboards |
| `st.dataframe(df, use_container_width=True)` | Tabela de dados responsiva | Históricos |
| `st.plotly_chart(fig, use_container_width=True)` | Gráficos interativos Plotly | BI |
| Badges HTML | Tags coloridas de status | Protocolos, alertas |
| `st.expander` | Seções colapsáveis | Inativos, detalhes |

### 13.4 Tela — Dashboard BI (Raio-X Individual)

```
┌──────────────────────────────────────────────────────────────────┐
│ MilkShow | BI e Inteligência                        [📊 logo]    │
├──────────────────────────────────────────────────────────────────┤
│ [Dashboard Geral] [Raio-X Individual] [Rankings] [Curva] [...]  │
├──────────────────────────────────────────────────────────────────┤
│ Animal: [Joana ▼]   Período: [01/01/2026] a [30/04/2026]       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ 820 L    │ │ R$2,50/L │ │ R$2.050  │ │ R$430    │           │
│  │ Produção │ │ Preço/L  │ │ Receita  │ │ Custo    │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│                                                                   │
│  ┌──────────┐ ┌──────────┐                                       │
│  │ R$0,52/L │ │ R$1,98/L │                                       │
│  │ Custo/L  │ │ Lucro/L  │  ✅ Margem: 79%                      │
│  └──────────┘ └──────────┘                                       │
│                                                                   │
│  ═══════════════ Leite vs Ração (área) ════════════════          │
│  │                                                    │           │
│  │  🔵 Leite (eixo esq)  🟢 Ração (eixo dir)         │           │
│  │  [gráfico de áreas sobrepostas com gradiente]      │           │
│  │                                                    │           │
│  ═══════════════════════════════════════════════════════         │
└──────────────────────────────────────────────────────────────────┘
```

### 13.5 Tela — Protocolos Sanitários

```
┌──────────────────────────────────────────────────────────────────┐
│ MilkShow | Protocolos Sanitários                  [🔬 logo]      │
├──────────────────────────────────────────────────────────────────┤
│ [Protocolos Ativos] [Novo Protocolo] [Histórico de Execuções]   │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Vacina Aftosa         [Vacina]                                  │
│  ● Próxima: 2026-05-10 [HOJE 🔴]    A cada 180d | Rebanho todo  │
│  [Executar]                                                       │
│  ─────────────────────────────────────────────────────           │
│  Vermifugação          [Vermífugo]                               │
│  ● Próxima: 2026-05-28 [em 22d 🟡]  A cada 90d | Rebanho todo  │
│  [Executar]                                                       │
│  ─────────────────────────────────────────────────────           │
│  Casqueamento Joana    [Casqueamento]                            │
│  ● Próxima: 2026-07-01 [em 56d 🟢]  A cada 120d | Joana        │
│  [Executar]                                                       │
│                                                                   │
│  ▼ Inativos (2)                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 13.6 Tela — Painel Mobile

```
┌─────────────────────────────────┐
│  Bom dia! 👋                    │
│  Fazenda São João — 06/05/2026  │
│  ─────────────────────────────  │
│  Hoje                           │
│  ┌──────┐ ┌──────┐ ┌────────┐  │
│  │ 350L │ │ 8/10 │ │ R$875  │  │
│  │Litros│ │Orden.│ │Receita │  │
│  └──────┘ └──────┘ └────────┘  │
│  ─────────────────────────────  │
│  Semana                         │
│  Total 7d: 2.450 L  Média: 350L │
│  ─────────────────────────────  │
│  Mês Atual                      │
│  Receitas: R$10.500             │
│  Despesas: R$7.200              │
│  Saldo:    R$3.300 ↑            │
│  ─────────────────────────────  │
│  Alertas                        │
│  🔴 URGENTE                     │
│  2 vacas não ordenhadas hoje    │
│  ─────────────────────────────  │
│  Top Vacas — Hoje               │
│  Joana    ████████████ 38L      │
│  Moreninha ████████    30L      │
│  Pintada   ██████      22L      │
│  ─────────────────────────────  │
│  [    Atualizar dados    ]      │
└─────────────────────────────────┘
```

### 13.7 Tela — Bot WhatsApp (exemplo de diálogo)

```
┌────────────────────────────────────────────────────────┐
│  WhatsApp — MilkShow Bot                               │
├────────────────────────────────────────────────────────┤
│                                                         │
│  Produtor:                                              │
│  ┌─────────────────────────────────────────────────┐  │
│  │ "Joana 22 litros, Moreninha 18, Pintada 15"     │  │
│  └─────────────────────────────────────────────────┘  │
│                                                         │
│  MilkShow Bot:                            ✓✓           │
│  ┌─────────────────────────────────────────────────┐  │
│  │ Confirma? 3 vacas — 55L total                   │  │
│  │ • Joana: 22L                                    │  │
│  │ • Moreninha: 18L                                │  │
│  │ • Pintada: 15L                                  │  │
│  └─────────────────────────────────────────────────┘  │
│                                                         │
│  Produtor:                                              │
│  ┌─────────────────────────────────────────────────┐  │
│  │ "sim"                                           │  │
│  └─────────────────────────────────────────────────┘  │
│                                                         │
│  MilkShow Bot:                            ✓✓           │
│  ┌─────────────────────────────────────────────────┐  │
│  │ ✅ 3 registros salvos! (55L no total)           │  │
│  └─────────────────────────────────────────────────┘  │
│                                                         │
└────────────────────────────────────────────────────────┘
```

---

## Apêndice A — Coleções do Firebase

| Coleção | Escopo | Campos Principais |
|---------|--------|-------------------|
| `registros_tel/{phone}` | Global | fazenda_id, nome, ativo, pin_hash, permissoes |
| `conversas_bot/{tel}` | Global | historico, estado, dados, tipo, itens, ultimo_salvo, ts |
| `sugestoes_bot` | Global | fazenda_id, pergunta, ts |
| `config/ngrok_url` | Global | url |
| `fazendas/{id}/animais` | Por fazenda | nome, raca, sexo, data_nasc, data_entrada, mae, status, obs |
| `fazendas/{id}/producao` | Por fazenda | data, id_animal, nome_animal, leite, racao, turno, obs |
| `fazendas/{id}/financeiro` | Por fazenda | data, descricao, cat, valor, tipo, animal |
| `fazendas/{id}/sanitario` | Por fazenda | data, tipo, prod, modo, animal, custo, obs |
| `fazendas/{id}/estoque` | Por fazenda | item, qtd, un, custo_unit, custo_medio, atualizado_em |
| `fazendas/{id}/config` | Por fazenda | preco_leite, custo_racao, nome_fazenda, ... |
| `fazendas/{id}/protocolos_sanitarios` | Por fazenda | nome, tipo, frequencia_dias, proxima_data, ultima_data, alvo, custo_estimado, ativo |
| `fazendas/{id}/protocolos_execucoes` | Por fazenda | protocolo_id, protocolo_nome, data, obs |

---

## Apêndice B — Variáveis de Ambiente

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `ANTHROPIC_API_KEY` | Sim | Chave Claude Haiku (fallback de IA) |
| `GROQ_API_KEY` | Sim | Chave Groq LLaMA + Whisper (IA principal) |
| `GOOGLE_API_KEY` | Sim | Chave Gemini 2.0 Flash (IA secundária) |
| `NGROK_AUTHTOKEN` | Sim (dev) | Token para tunnel ngrok local |
| `EVOLUTION_URL` | Recomendado | URL do servidor Evolution API |
| `EVOLUTION_KEY` | Recomendado | API Key do Evolution API |
| `EVOLUTION_INSTANCE` | Recomendado | Nome da instância Evolution |
| `ZAPI_INSTANCE` | Opcional | Instância Z-API (backup) |
| `ZAPI_TOKEN` | Opcional | Token Z-API |
| `ZAPI_CLIENT_TOKEN` | Opcional | Client token Z-API |
| `TWILIO_ACCOUNT_SID` | Opcional | Account SID Twilio (último recurso) |
| `TWILIO_AUTH_TOKEN` | Opcional | Auth Token Twilio |
| `TWILIO_FROM` | Opcional | Número Twilio (ex: `whatsapp:+14155238886`) |
| `BOT_ADMIN_TOKEN` | Recomendado | Secret para assinatura JWT do app mobile |

---

## Apêndice C — Constantes de Negócio

| Constante | Valor | Descrição |
|-----------|-------|-----------|
| `DIAS_PVE` | 45 | Período Voluntário de Espera pós-parto |
| `DIAS_DIAGNOSTICO` | 30 | Dias para diagnóstico de prenhez pós-IA |
| `DIAS_SECAGEM` | 60 | Período de secagem antes do parto |
| `GESTACAO` | 283 | Dias de gestação bovina |
| `DIAS_DESMAME` | 90 | Dias de vida até o desmame do bezerro |
| `PRECO_PADRAO_LEITE` | 2.50 | Preço padrão R$/L (quando não configurado) |
| `DENSIDADE_LEITE` | 1.032 | Densidade do leite (kg/L) |
| `BASE_PASTO_LITROS` | 4.0 | Produção base de pasto (L/dia) |
| `FATOR_CONVERSAO` | 3.0 | kg de ração por litro produzido acima da base |
| `MAXIMO_POR_REFEICAO` | 6.0 | kg máximo de ração por refeição |
| `CACHE_TTL_SEGUNDOS` | 60 | Intervalo de recarga dos dados do Firebase |

---

*Documento gerado em Maio de 2026 para o projeto MilkShow.*  
*Toda a documentação reflete o estado atual do código em produção.*

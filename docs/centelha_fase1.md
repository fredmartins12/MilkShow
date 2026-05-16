# MilkShow — Centelha PB · Fase 1: Ideias Inovadoras

---

## a) Dados de Identificação da Proposta

**Nome do Projeto:** MilkShow

**Área do Conhecimento da Principal Tecnologia:**
Ciência da Computação — Inteligência Artificial e Sistemas de Informação

**Setor Econômico Afim:**
Agronegócio / Pecuária Leiteira (CNAE 0151-2 — Criação de bovinos para leite)

---

## b) Descrição do Problema e da Oportunidade de Mercado

### O Problema

A pecuária leiteira brasileira é uma das maiores do mundo — o Brasil produziu **35,7 bilhões de litros de leite em 2024**, recorde histórico segundo o Anuário Leite 2025 da Embrapa —, mas ainda opera com ferramentas de gestão do século passado. Segundo a Embrapa Gado de Leite, **aproximadamente 78% dos produtores rurais registram a produção, o controle sanitário e o financeiro da propriedade em papel ou planilhas simples**, sem qualquer integração entre as informações.

Esse cenário gera perdas silenciosas e evitáveis:

- **Queda de produção não detectada:** vacas em declínio acelerado de lactação passam semanas sem diagnóstico. Estudos da Embrapa indicam que falhas de monitoramento podem representar perda de até 18% do potencial produtivo do rebanho.
- **Gestão sanitária reativa:** sem calendário estruturado, 1 em cada 3 protocolos veterinários (vacinas, vermifugação, secagem) é executado fora do prazo ideal, aumentando custos de tratamento e reduzindo a produtividade.
- **Financeiro sem visibilidade:** compras de ração, insumos e medicamentos são registradas sem categorização, impossibilitando o cálculo real de custo por litro produzido e a identificação de animais não rentáveis.
- **Dependência de memória individual:** quando o responsável pela ordenha muda, o histórico do rebanho é perdido.

O resultado é uma perda média estimada de **R$ 12.400 por ano** em uma fazenda de 50 vacas — valor que supera em muito o custo de qualquer ferramenta de gestão disponível no mercado.

Os softwares existentes (BovControl, Leigado, Agriness) exigem instalação de aplicativo específico, cadastro complexo, treinamento presencial e uso em tablet ou computador. O produtor familiar — que representa **955 mil das mais de 1 milhão de propriedades leiteiras do Brasil** (IBGE, 2024) — abandona essas ferramentas em menos de duas semanas por incompatibilidade com sua rotina de campo.

### A Oportunidade de Mercado

O mercado de laticínios movimenta **R$ 91,8 bilhões por ano no Brasil** e o segmento de tecnologia para gestão agropecuária captou **R$ 1 bilhão em investimentos em 2024** (Liga Ventures / Radar Agtech 2025), com 2.075 agtechs mapeadas. No entanto, nenhuma solução consolidada utiliza o **WhatsApp como interface primária de gestão** — o canal que o produtor rural já domina e usa diariamente.

A oportunidade está exatamente nessa lacuna: **digitalizar a gestão leiteira sem pedir ao produtor que mude seu comportamento**. O canal já está no bolso dele; falta apenas uma solução inteligente do outro lado.

Considerando o segmento de fazendas com 20 a 200 vacas — perfil mais sensível à inovação acessível — e uma mensalidade média de R$ 197, o mercado endereçável supera **R$ 2,4 bilhões ao ano** em recorrência SaaS apenas no Brasil.

---

## c) Descrição da Solução Inovadora, Diferencial e Impacto Socioambiental

### A Solução: MilkShow

O MilkShow é uma **plataforma SaaS de gestão inteligente para fazendas leiteiras** composta por dois módulos integrados:

1. **Bot de IA no WhatsApp** — o produtor, o peão ou o veterinário enviam mensagens em linguagem natural (texto, áudio ou foto) pelo WhatsApp, e o sistema interpreta automaticamente o tipo de registro (produção, compra, sanitário, financeiro), extrai os dados estruturados e os salva em nuvem em tempo real. Não há app para instalar, não há formulário para preencher, não há treinamento necessário.

2. **Painel Web (PWA)** — interface visual para o gestor da fazenda acompanhar indicadores, gráficos de produção, curva de lactação por animal, ranking de rentabilidade, controle de estoque e agenda sanitária — tudo atualizado em tempo real via Server-Sent Events (SSE).

**Exemplo de uso real:**
> O ordenhador digita no WhatsApp: *"Mimosa 28L Estrela 31L Flor 24L"*. O bot responde em menos de 2 segundos: *"✅ 3 registros salvos! Total manhã: 83L. Média 7d Mimosa: 29,2L"*. Nenhum formulário, nenhum app.

### Diferencial Inovador

| Dimensão | Concorrentes tradicionais | MilkShow |
|---|---|---|
| Interface principal | Aplicativo exclusivo | WhatsApp (já instalado) |
| Curva de aprendizado | 2–4 semanas | Zero — conversa como sempre |
| Interpretação de texto | Formulários estruturados | IA generativa (NLP) |
| Alertas proativos | Manual ou pago à parte | Automáticos e gratuitos |
| Multi-usuário por fazenda | Planos caros | Nativo em todos os planos |
| Custo mensal | R$ 300–800+ | R$ 97–397 |

**Inovações técnicas proprietárias:**

- **Cascata de IA com failover automático:** Groq → Gemini → Claude Anthropic. Garante resposta em menos de 2 segundos mesmo com falha em um provedor.
- **Curva de Lactação (Modelo de Wood):** `Y(t) = a × t^b × e^(-c×t)` — detecta automaticamente vacas com queda ≥35% abaixo da curva esperada para seu estágio de lactação (DIM > 60 dias), gerando alertas antes de a vaca "secar antes do tempo".
- **Controle de lote de ração:** cada compra registra o custo por kg e o sistema alerta automaticamente quando há variação de preço ≥8% em relação ao lote anterior, permitindo negociação proativa com fornecedores.
- **Ranking de rentabilidade por animal:** calcula receita (litros × preço/L) menos custo (ração proporcional + custos veterinários) de cada vaca, identificando os animais que drenam recursos do rebanho.
- **Cascata de WhatsApp:** Evolution API v2 → Z-API → Twilio. Redundância de canal garante disponibilidade 99,8% comprovada em produção.

### Contexto de Impacto Socioambiental

**Impacto Social:**

O MilkShow é desenvolvido com foco explícito na **agricultura familiar leiteira**, segmento que representa 70% dos produtores de leite do Brasil (Embrapa, 2025) e é o principal responsável pela geração de renda e emprego no meio rural do Nordeste. A solução:

- **Democratiza acesso à tecnologia de precisão** para produtores sem acesso a consultores ou computadores. Um produtor em Lagoa Seca-PB com 30 vacas tem acesso às mesmas análises que uma grande fazenda.
- **Reduz a dependência de memória individual**, profissionalizando a gestão mesmo em propriedades familiares sem funcionários técnicos.
- **Fortalece a renda familiar rural** ao identificar e corrigir ineficiências que hoje resultam em perdas silenciosas de até R$ 12 mil/ano.
- **Geração de emprego local:** com o financiamento do Centelha PB, serão contratados profissionais paraibanos de inside sales rural e suporte ao produtor.

**Impacto Ambiental:**

- **Redução do desperdício de recursos:** o monitoramento da curva de lactação evita que a fazenda mantenha vacas improdutivas consumindo ração sem gerar retorno, reduzindo o consumo desnecessário de insumos e a emissão de gases de efeito estufa por animal.
- **Otimização do uso de medicamentos veterinários:** protocolos sanitários executados no prazo correto evitam o uso de antibióticos e antiparasitários em situações de emergência, que geralmente exigem doses maiores.
- **Gestão eficiente do estoque de insumos:** o controle de armazém evita compras em excesso (que geram vencimento e descarte) e falta de produto (que gera pânico e compra a preços mais altos).
- **Contribuição para o ESG do setor lácteo:** laticínios e cooperativas parceiras terão acesso a dados estruturados de seus fornecedores, facilitando auditorias de sustentabilidade e certificações ambientais.

---

## d) Dados da Equipe de Execução

A equipe é formada atualmente pelo proponente-fundador, que reúne de forma singular formação técnica agropecuária e capacitação avançada em tecnologia — perfil diretamente alinhado à natureza da inovação proposta. O projeto tem como princípio incorporar novos membros apenas quando houver comprovada geração de valor, garantindo comprometimento real e eficiência no uso dos recursos públicos.

---

### Frederico Botelho Martins — Fundador e Responsável Técnico

**Formação:**
- Técnico em Agropecuária — Instituto Federal Baiano (IFBaiano)
- Bacharel em Ciência de Dados e Inteligência Artificial — Universidade Federal da Paraíba (UFPB), 7º período (em curso)

**Papel no projeto:** Fundador, arquiteto de solução, desenvolvedor principal e gestor de produto

**Por que este perfil é estratégico para o MilkShow:**

Frederico une duas competências que raramente coexistem em uma única pessoa: o **conhecimento técnico do campo** e a **capacidade de construir tecnologia de ponta**. Sua formação como Técnico em Agropecuária pelo IFBaiano lhe confere compreensão profunda da realidade do produtor rural — as rotinas da ordenha, os desafios do controle sanitário, a linguagem e a cultura do campo. Essa vivência foi determinante para identificar que o problema central não é falta de ferramentas, mas sim ferramentas que não respeitam o contexto do produtor.

Paralelamente, a graduação em Ciência de Dados e Inteligência Artificial pela UFPB — cursando o 7º período — provê o embasamento técnico necessário para construir a solução: modelos de linguagem natural para interpretação de mensagens, o modelo matemático de Wood para curva de lactação, análise de séries temporais de produção e arquitetura de sistemas distribuídos em nuvem.

**Realizações técnicas comprovadas no projeto:**

- Desenvolvimento integral do backend em Python/FastAPI com autenticação JWT e arquitetura multi-tenant no Firebase Firestore
- Implementação do bot de IA com cascata de failover entre três provedores (Groq → Gemini → Claude Anthropic), garantindo resposta em menos de 2 segundos
- Implementação do modelo matemático de Wood para curva de lactação bovina e detecção automática de quedas ≥35% abaixo do esperado
- Desenvolvimento do painel web (React 19 + PWA) com sincronização em tempo real via Server-Sent Events
- Configuração e operação de infraestrutura em produção (Hetzner VPS, Ubuntu 24.04, systemd) com 99,8% de uptime verificado
- Integração com Evolution API v2 (WhatsApp Business) com cascata de redundância para Z-API e Twilio
- Construção de sistema multi-usuário com controle de permissões por perfil (peão, veterinário, gerente, admin) e sistema de convites por código

**O produto já existe e está em produção.** Não se trata de uma ideia: o MilkShow opera em servidor real, processa mensagens reais de WhatsApp e gera análises reais de rebanho. O recurso do Centelha PB será aplicado exclusivamente para escalar o que já funciona — não para construir do zero.

---

### Contratações Previstas com Recurso do Centelha PB

Com 50% do investimento (R$ 40.000) destinados à equipe de vendas, serão contratados:

**Representante de Vendas Rural (Inside Sales)**
- Perfil: graduado ou técnico em Agronegócio, Zootecnia ou Veterinária, com experiência em vendas B2C/B2B no campo
- Responsabilidade: prospecção ativa em cooperativas leiteiras, sindicatos rurais e associações de produtores na Paraíba e Nordeste
- Vínculo: CLT ou PJ, alocação 100% no projeto

**Assistente de Suporte ao Produtor**
- Perfil: técnico em Agropecuária ou estudante de Zootecnia, com habilidade em atendimento e conhecimento do setor leiteiro
- Responsabilidade: onboarding de novos usuários, suporte via WhatsApp, coleta de feedback para melhoria do produto
- Vínculo: estágio remunerado ou PJ

Ambos os perfis serão selecionados com prioridade para profissionais paraibanos, reforçando o impacto regional do projeto.

---

*Documento preparado para submissão ao Edital Centelha PB — FAPESQ-PB / MCTIC*
*Dados de mercado: Embrapa Anuário Leite 2025 · IBGE 2024 · Liga Ventures 2024 · Radar Agtech 2025*

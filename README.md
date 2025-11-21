🐮 MilkShow - Gestão Leiteira Enterprise

O MilkShow é uma solução completa de gestão para propriedades leiteiras, desenvolvida para transformar dados do campo em decisões estratégicas. O sistema opera 100% na nuvem, integrando controle zootécnico, financeiro e de estoque em uma interface ágil e visual.

🚀 Funcionalidades Principais

O sistema é dividido em módulos estratégicos:

📊 BI & Inteligência: Dashboards com KPIs de Custo/Litro, Margem de Lucro, Preço Médio Realizado e Curvas de Produção.

🧬 Veterinária & Reprodução: "Robô Veterinário" que gera alertas automáticos para diagnósticos, inseminação, secagem e partos previstos.

💰 Financeiro 360: Fluxo de caixa com regime de competência (vínculo de receita de leite por período de produção) e relatórios de margem por animal.

📦 Armazém Avançado: Controle de estoque com cálculo automático de preço médio ponderado e baixa de insumos.

👶 Berçário: Gestão completa de bezerros, colostragem e desmame.

📅 Calendário Visual: Agenda de manejo inteligente integrada automaticamente aos eventos do rebanho.

🐄 Rebanho Cloud: Cadastro unificado com filtros avançados e histórico na nuvem.

🛠️ Tecnologias Utilizadas

Frontend/Backend: Streamlit (Python)

Banco de Dados: Google Firebase (Firestore) - NoSQL em Tempo Real

Análise de Dados: Pandas & Plotly

Infraestrutura: Cloud-Ready (Deploy contínuo)

📦 Instalação e Execução Local

Clone o repositório:

git clone [https://github.com/seu-usuario/MilkShow.git](https://github.com/seu-usuario/MilkShow.git)
cd MilkShow


Crie um ambiente virtual e instale as dependências:

python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt


Configure a chave do Firebase:

Adicione seu arquivo firebase_key.json na raiz do projeto.

Execute a aplicação:

streamlit run gestor.py


☁️ Deploy (Streamlit Cloud)

Este projeto está configurado para deploy automático via Streamlit Community Cloud, utilizando Secrets para gerenciamento seguro das credenciais do Firebase.

Desenvolvido para modernizar o agronegócio. 🥛

# MilkShow — Deploy na Oracle Cloud

## Passo 1 — Criar conta Oracle Cloud

1. Acesse https://oracle.com/cloud/free
2. Crie a conta (exige cartão de crédito, mas **não cobra nada**)
3. Confirme o e-mail e acesse o Console

---

## Passo 2 — Criar a VM (Always Free)

1. No Console, clique em **Create a VM Instance**
2. Configure:
   - **Name:** milkshow-bot
   - **Image:** Canonical Ubuntu 22.04
   - **Shape:** Ampere A1 (ARM) — selecione **4 OCPUs + 24 GB RAM** (gratuito)
   - **SSH keys:** gere ou cole sua chave pública SSH
3. Clique em **Create**
4. Aguarde a VM ficar com status **Running**
5. Anote o **IP público** mostrado na tela

---

## Passo 3 — Abrir portas no firewall da Oracle

1. Na VM criada, clique em **Subnet** → **Security Lists** → **Default Security List**
2. Clique em **Add Ingress Rules** e adicione:

| Source CIDR | Protocol | Port |
|---|---|---|
| 0.0.0.0/0 | TCP | 80 |
| 0.0.0.0/0 | TCP | 443 |

(A porta 22 já vem aberta por padrão)

---

## Passo 4 — Conectar ao servidor

```bash
ssh ubuntu@IP_DO_SERVIDOR
```

---

## Passo 5 — Preparar o .env no servidor

Antes de rodar o setup, crie o arquivo de configuração:

```bash
sudo mkdir -p /opt/milkshow
sudo chown ubuntu:ubuntu /opt/milkshow
nano /opt/milkshow/.env
```

Cole o conteúdo do `.env.example` preenchido com suas chaves de API.

Copie também o `firebase_key.json`:
```bash
# No seu computador (Windows):
scp firebase_key.json ubuntu@IP_DO_SERVIDOR:/opt/milkshow/firebase_key.json
```

---

## Passo 6 — Rodar o setup

```bash
# No seu computador, envie a pasta deploy para o servidor:
scp -r deploy/ ubuntu@IP_DO_SERVIDOR:~/

# No servidor:
chmod +x ~/deploy/setup.sh ~/deploy/update.sh
bash ~/deploy/setup.sh SEU_DOMINIO_OU_IP
```

Se não tiver domínio ainda, use o IP público direto:
```bash
bash ~/deploy/setup.sh 123.456.789.0
```

---

## Passo 7 — Conectar o número WhatsApp

1. Acesse: `http://SEU_IP/manager`
2. Use a chave que você definiu em `EVOLUTION_KEY`
3. Clique em **Create Instance** → nome: `milkshow`
4. Clique em **Connect** → aparece o QR Code
5. No celular com o número do WhatsApp Business:
   - Abra WhatsApp → 3 pontos → **Aparelhos conectados** → **Conectar aparelho**
   - Escaneie o QR Code

O número está conectado. O bot já responde automaticamente.

---

## Passo 8 — Cadastrar usuários no app

1. Abra o app Streamlit (rode local ou Streamlit Cloud)
2. Vá em **Configurações → Bot IA**
3. Cadastre o número do cliente no formato: `5511999999999`

---

## Atualizar o código depois

```bash
# No seu computador:
scp -r . ubuntu@IP_DO_SERVIDOR:/tmp/milkshow_update/
ssh ubuntu@IP_DO_SERVIDOR "bash ~/deploy/update.sh"
```

Ou mais simples, do servidor:
```bash
bash ~/deploy/update.sh
```

---

## Comandos úteis no servidor

```bash
# Ver logs em tempo real
sudo journalctl -u milkshow-bot -f

# Reiniciar bot
sudo systemctl restart milkshow-bot

# Status do bot
sudo systemctl status milkshow-bot

# Ver containers Docker (Evolution API)
docker ps
docker logs milkshow_evolution -f

# Reiniciar Evolution API
docker-compose -f /opt/milkshow/docker-compose.yml restart
```

---

## Custos finais

| Item | Custo |
|---|---|
| Oracle VM (4 OCPUs, 24 GB) | **R$ 0/mês** |
| Evolution API (Docker) | **R$ 0/mês** |
| Chip WhatsApp | **~R$ 30/mês** |
| Domínio (opcional) | **~R$ 40/ano** |
| Groq + Gemini (IA) | **R$ 0/mês** (gratuito) |
| Firebase (até 50k reads/dia) | **R$ 0/mês** |
| **Total** | **~R$ 30/mês fixo** |

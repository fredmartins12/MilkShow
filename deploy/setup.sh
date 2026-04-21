#!/bin/bash
# =============================================================
# MilkShow — Setup completo para Oracle Cloud (Ubuntu 22.04)
# Uso: bash setup.sh SEU_DOMINIO_OU_IP
# Exemplo: bash setup.sh app.milkshow.com.br
# =============================================================
set -e

DOMINIO="${1:-$(curl -s ifconfig.me)}"
APP_DIR="/opt/milkshow"
LOG_DIR="/var/log/milkshow"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "================================================="
echo " MilkShow Setup — servidor: $DOMINIO"
echo "================================================="

# ── 1. Sistema ────────────────────────────────────
echo "[1/8] Atualizando sistema..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
    python3.11 python3.11-venv python3-pip \
    nginx certbot python3-certbot-nginx \
    git curl wget unzip ufw

# ── 2. Docker ─────────────────────────────────────
echo "[2/8] Instalando Docker..."
if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker ubuntu
fi
if ! command -v docker-compose &>/dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# ── 3. Diretórios e logs ──────────────────────────
echo "[3/8] Criando diretórios..."
sudo mkdir -p "$APP_DIR" "$LOG_DIR"
sudo chown ubuntu:ubuntu "$APP_DIR" "$LOG_DIR"

# ── 4. Código da aplicação ────────────────────────
echo "[4/8] Copiando código..."
# Copia todos os arquivos do projeto (exceto deploy/ e arquivos sensíveis)
rsync -av --exclude='deploy/' --exclude='__pycache__' --exclude='*.pyc' \
    --exclude='.git' --exclude='bot_log.txt' \
    "$SCRIPT_DIR/../" "$APP_DIR/"

# ── 5. Ambiente Python ────────────────────────────
echo "[5/8] Instalando dependências Python..."
python3.11 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --quiet --upgrade pip
"$APP_DIR/venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"

# ── 6. Evolution API (Docker) ─────────────────────
echo "[6/8] Iniciando Evolution API..."
cd "$APP_DIR/deploy" || cd "$SCRIPT_DIR"

# Cria .env para docker-compose se não existir
if [ ! -f "$APP_DIR/.env" ]; then
    echo "ATENCAO: Crie o arquivo $APP_DIR/.env antes de continuar."
    echo "Use deploy/.env.example como base."
    exit 1
fi

# Carrega variáveis para o docker-compose
set -a; source "$APP_DIR/.env"; set +a

# Sobe Evolution API
cp "$SCRIPT_DIR/docker-compose.yml" "$APP_DIR/docker-compose.yml"
docker-compose -f "$APP_DIR/docker-compose.yml" up -d

# ── 7. Systemd — bot ──────────────────────────────
echo "[7/8] Configurando serviço systemd..."
sudo mkdir -p "$LOG_DIR"
sudo chown ubuntu:ubuntu "$LOG_DIR"

sudo cp "$SCRIPT_DIR/milkshow-bot.service" /etc/systemd/system/milkshow-bot.service
sudo systemctl daemon-reload
sudo systemctl enable milkshow-bot
sudo systemctl restart milkshow-bot

# ── 8. Nginx + HTTPS ──────────────────────────────
echo "[8/8] Configurando Nginx..."
sudo cp "$SCRIPT_DIR/nginx.conf" /etc/nginx/sites-available/milkshow
sudo sed -i "s/SEU_DOMINIO/$DOMINIO/g" /etc/nginx/sites-available/milkshow
sudo ln -sf /etc/nginx/sites-available/milkshow /etc/nginx/sites-enabled/milkshow
sudo rm -f /etc/nginx/sites-enabled/default

# Testa config do nginx
sudo nginx -t

# Firewall Oracle Cloud (abre portas necessárias)
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# HTTPS via Let's Encrypt (só funciona com domínio real, não com IP)
if [[ "$DOMINIO" =~ \. ]] && [[ ! "$DOMINIO" =~ ^[0-9] ]]; then
    echo "Domínio detectado. Gerando certificado SSL..."
    sudo certbot --nginx -d "$DOMINIO" --non-interactive --agree-tos \
        --email "admin@$DOMINIO" --redirect || true
else
    echo "IP detectado — pulando SSL. Configure um domínio depois e rode:"
    echo "  sudo certbot --nginx -d SEU_DOMINIO"
    # Nginx sem SSL por enquanto
    sudo sed -i 's/listen 443 ssl;/listen 80;/' /etc/nginx/sites-available/milkshow
    sudo sed -i '/ssl_certificate/d' /etc/nginx/sites-available/milkshow
    sudo sed -i '/ssl_dhparam/d' /etc/nginx/sites-available/milkshow
    sudo sed -i '/include.*options-ssl/d' /etc/nginx/sites-available/milkshow
fi

sudo systemctl restart nginx

# ── Resultado ─────────────────────────────────────
echo ""
echo "================================================="
echo " Setup concluído!"
echo "================================================="
echo ""
echo "Próximos passos:"
echo ""
echo "1. Acesse o painel Evolution API:"
echo "   http://$DOMINIO/manager"
echo "   Chave: valor de EVOLUTION_KEY no .env"
echo ""
echo "2. Crie uma instância e escaneie o QR Code"
echo "   com o celular que tem o número do WhatsApp"
echo ""
echo "3. Teste o bot enviando 'oi' para o número conectado"
echo ""
echo "Logs do bot:"
echo "   sudo journalctl -u milkshow-bot -f"
echo "   tail -f $LOG_DIR/bot.log"
echo ""
echo "Reiniciar o bot:"
echo "   sudo systemctl restart milkshow-bot"
echo ""
echo "Atualizar o código:"
echo "   bash $SCRIPT_DIR/update.sh"
echo ""

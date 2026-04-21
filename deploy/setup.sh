#!/bin/bash
# =============================================================
# MilkShow — Setup completo (Ubuntu 22.04 / 24.04)
# Uso: bash setup.sh SEU_DOMINIO_OU_IP
# Exemplo: bash setup.sh 178.104.252.193
# =============================================================
set -e

DOMINIO="${1:-$(curl -s ifconfig.me)}"
APP_DIR="/opt/milkshow"
LOG_DIR="/var/log/milkshow"

# Detecta versão do Python disponível
PYTHON=$(command -v python3.12 2>/dev/null || command -v python3.11 2>/dev/null || command -v python3)

echo "================================================="
echo " MilkShow Setup — servidor: $DOMINIO"
echo " Python: $PYTHON"
echo "================================================="

# ── 1. Sistema ────────────────────────────────────
echo "[1/8] Atualizando sistema..."
apt-get update -qq
apt-get install -y -qq \
    python3 python3-venv python3-pip \
    nginx certbot python3-certbot-nginx \
    git curl wget unzip ufw rsync

# ── 2. Docker ─────────────────────────────────────
echo "[2/8] Instalando Docker..."
if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | sh
fi
if ! command -v docker-compose &>/dev/null; then
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# ── 3. Diretórios ─────────────────────────────────
echo "[3/8] Criando diretórios..."
mkdir -p "$APP_DIR" "$LOG_DIR"

# ── 4. Código do GitHub ───────────────────────────
echo "[4/8] Baixando código do GitHub..."
if [ -d "$APP_DIR/.git" ]; then
    git -C "$APP_DIR" pull
else
    git clone https://github.com/fredmartins12/MilkShow.git "$APP_DIR"
fi

# ── 5. Ambiente Python ────────────────────────────
echo "[5/8] Instalando dependências Python..."
$PYTHON -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --quiet --upgrade pip
"$APP_DIR/venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"

# ── 6. Evolution API (Docker) ─────────────────────
echo "[6/8] Iniciando Evolution API..."
if [ ! -f "$APP_DIR/.env" ]; then
    echo "ATENCAO: Crie o arquivo $APP_DIR/.env antes de continuar."
    echo "Use $APP_DIR/deploy/.env.example como base."
    exit 1
fi

set -a; source "$APP_DIR/.env"; set +a
docker-compose -f "$APP_DIR/deploy/docker-compose.yml" up -d

# ── 7. Systemd ────────────────────────────────────
echo "[7/8] Configurando serviço systemd..."
cp "$APP_DIR/deploy/milkshow-bot.service" /etc/systemd/system/milkshow-bot.service
systemctl daemon-reload
systemctl enable milkshow-bot
systemctl restart milkshow-bot

# ── 8. Nginx ──────────────────────────────────────
echo "[8/8] Configurando Nginx..."
cp "$APP_DIR/deploy/nginx.conf" /etc/nginx/sites-available/milkshow
sed -i "s/SEU_DOMINIO/$DOMINIO/g" /etc/nginx/sites-available/milkshow
ln -sf /etc/nginx/sites-available/milkshow /etc/nginx/sites-enabled/milkshow
rm -f /etc/nginx/sites-enabled/default

ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# SSL só com domínio real
if [[ "$DOMINIO" =~ \. ]] && [[ ! "$DOMINIO" =~ ^[0-9] ]]; then
    certbot --nginx -d "$DOMINIO" --non-interactive --agree-tos \
        --email "admin@$DOMINIO" --redirect || true
else
    sed -i 's/listen 443 ssl;/listen 80;/' /etc/nginx/sites-available/milkshow
    sed -i '/ssl_certificate/d' /etc/nginx/sites-available/milkshow
    sed -i '/ssl_dhparam/d' /etc/nginx/sites-available/milkshow
    sed -i '/include.*options-ssl/d' /etc/nginx/sites-available/milkshow
fi

nginx -t && systemctl restart nginx

echo ""
echo "================================================="
echo " Setup concluído!"
echo " Bot: http://$DOMINIO"
echo " Evolution: http://$DOMINIO/manager"
echo "================================================="
echo ""
echo "PRÓXIMO PASSO: crie o .env com suas chaves:"
echo "  nano $APP_DIR/.env"
echo ""
echo "Logs: journalctl -u milkshow-bot -f"

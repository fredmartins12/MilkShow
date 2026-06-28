#!/bin/bash
# =============================================================
# MilkShow — Atualiza código e reinicia (uso diário)
# Uso: bash /opt/milkshow/deploy/update.sh
# =============================================================
set -e

APP_DIR="/opt/milkshow"
DEPLOY_DIR="$APP_DIR/deploy"
FRONTEND_DIR="$APP_DIR/mobile"

echo "================================================="
echo " MilkShow — Atualizando"
echo "================================================="

echo "[1/5] Código mais recente do GitHub..."
git -C "$APP_DIR" pull

echo "[2/5] Dependências Python..."
"$APP_DIR/venv/bin/pip" install --quiet --upgrade pip
"$APP_DIR/venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"

echo "[3/5] Build do frontend React..."
if [ -d "$FRONTEND_DIR" ]; then
    cd "$FRONTEND_DIR"
    # Instala dependências Node se necessário
    if ! command -v node &>/dev/null; then
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt-get install -y nodejs
    fi
    npm ci --silent
    npm run build
    echo "   Frontend compilado em $FRONTEND_DIR/dist/"
else
    echo "   AVISO: pasta $FRONTEND_DIR não encontrada, pulando build do frontend"
fi

echo "[4/5] Reiniciando Evolution API..."
cd "$DEPLOY_DIR" && docker compose pull --quiet && docker compose up -d 2>/dev/null || true

echo "[5/5] Reiniciando bot..."
systemctl restart milkshow-bot
sleep 2
systemctl is-active --quiet milkshow-bot && echo "   Bot OK" || journalctl -u milkshow-bot -n 10 --no-pager

echo ""
echo "================================================="
echo " Atualizado!"
echo " App: http://$(curl -s ifconfig.me 2>/dev/null)/app/"
echo " Logs: journalctl -u milkshow-bot -f"
echo "================================================="

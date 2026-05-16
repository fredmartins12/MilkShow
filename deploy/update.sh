#!/bin/bash
# =============================================================
# MilkShow — Atualiza código e reinicia (uso diário)
# Uso: bash /opt/milkshow/deploy/update.sh
# Para setup inicial ou trocar Evolution v1→v2, use migrate_to_v2.sh
# =============================================================
set -e

APP_DIR="/opt/milkshow"
DEPLOY_DIR="$APP_DIR/deploy"

echo "================================================="
echo " MilkShow — Atualizando"
echo "================================================="

echo "[1/3] Código mais recente do GitHub..."
git -C "$APP_DIR" pull

echo "[2/3] Dependências Python..."
"$APP_DIR/venv/bin/pip" install --quiet --upgrade pip
"$APP_DIR/venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"

echo "[3/3] Reiniciando serviços..."
# Atualiza imagem da Evolution se necessário
cd "$DEPLOY_DIR" && docker compose pull --quiet && docker compose up -d 2>/dev/null || true

# Reinicia o bot
systemctl restart milkshow-bot
sleep 2
systemctl is-active --quiet milkshow-bot && echo "   Bot OK" || journalctl -u milkshow-bot -n 10 --no-pager

echo ""
echo "================================================="
echo " Atualizado! Logs: journalctl -u milkshow-bot -f"
echo "================================================="

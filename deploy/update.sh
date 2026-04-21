#!/bin/bash
# =============================================================
# MilkShow — Atualiza código no servidor
# Uso: bash /opt/milkshow/deploy/update.sh
# =============================================================
set -e

APP_DIR="/opt/milkshow"

echo "================================================="
echo " MilkShow — Atualizando servidor"
echo "================================================="

echo "[1/4] Baixando código novo do GitHub..."
git -C "$APP_DIR" pull

echo "[2/4] Atualizando dependências Python..."
"$APP_DIR/venv/bin/pip" install --quiet --upgrade pip
"$APP_DIR/venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"

echo "[3/4] Atualizando Evolution API..."
cp "$APP_DIR/.env" "$APP_DIR/deploy/.env"
cd "$APP_DIR/deploy" && docker compose pull --quiet && docker compose up -d

echo "[4/4] Reiniciando bot..."
systemctl restart milkshow-bot
sleep 2
systemctl status milkshow-bot --no-pager

echo ""
echo "================================================="
echo " Atualização concluída!"
echo "================================================="

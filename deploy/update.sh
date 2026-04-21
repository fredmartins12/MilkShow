#!/bin/bash
# =============================================================
# MilkShow — Atualiza código no servidor sem derrubar o serviço
# Uso: bash update.sh
# =============================================================
set -e

APP_DIR="/opt/milkshow"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Atualizando código..."
rsync -av --exclude='deploy/' --exclude='__pycache__' --exclude='*.pyc' \
    --exclude='.git' --exclude='bot_log.txt' --exclude='.env' \
    --exclude='firebase_key.json' \
    "$SCRIPT_DIR/../" "$APP_DIR/"

echo "Reinstalando dependências (se mudou requirements.txt)..."
"$APP_DIR/venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"

echo "Reiniciando bot..."
sudo systemctl restart milkshow-bot

echo "Pronto! Status:"
sudo systemctl status milkshow-bot --no-pager

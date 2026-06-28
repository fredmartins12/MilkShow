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

echo "[3/5] Frontend — recebe dist via GitHub Actions (não builda no servidor)"
# O dist é enviado pela pipeline CI/CD local via tar — não precisa de Node aqui.
# Se o dist não existir ou estiver corrompido, avisa mas não bloqueia.
if [ ! -f "$FRONTEND_DIR/dist/index.html" ]; then
    echo "   AVISO: $FRONTEND_DIR/dist/index.html não encontrado."
    echo "   Execute o deploy local para enviar o frontend atualizado."
fi
# Garante permissões corretas (evita 403)
if [ -d "$FRONTEND_DIR/dist" ]; then
    find "$FRONTEND_DIR/dist" -type d -exec chmod 755 {} \;
    find "$FRONTEND_DIR/dist" -type f -exec chmod 644 {} \;
    echo "   Permissões do dist OK"
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

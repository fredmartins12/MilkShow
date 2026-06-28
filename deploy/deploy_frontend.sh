#!/bin/bash
# =============================================================
# MilkShow — Deploy do frontend (roda no Windows via Git Bash)
# Uso: bash deploy/deploy_frontend.sh
# =============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
MOBILE_DIR="$PROJECT_DIR/mobile"
KEY="$SCRIPT_DIR/milkshow_ssh.key"
SERVER="root@178.104.252.193"
REMOTE_DIST="/opt/milkshow/mobile/dist"

echo "================================================="
echo " MilkShow — Deploy Frontend"
echo "================================================="

# 1. Build
echo "[1/3] Build React..."
cd "$MOBILE_DIR"
npm run build
echo "   Build OK → dist/ gerado"

# 2. Empacotar em tar com -C (não usa cd — evita bug de path com caracteres especiais)
echo "[2/3] Empacotando..."
tar czf /tmp/milkshow_dist.tar.gz -C "$MOBILE_DIR/dist" .
echo "   Pacote: $(du -sh /tmp/milkshow_dist.tar.gz | cut -f1)"

# 3. Enviar e extrair no servidor
echo "[3/3] Enviando para o servidor..."
scp -i "$KEY" -o StrictHostKeyChecking=no /tmp/milkshow_dist.tar.gz "$SERVER":/tmp/
ssh -i "$KEY" -o StrictHostKeyChecking=no "$SERVER" "
  rm -rf $REMOTE_DIST/*
  tar xzf /tmp/milkshow_dist.tar.gz -C $REMOTE_DIST/
  find $REMOTE_DIST -type d -exec chmod 755 {} \;
  find $REMOTE_DIST -type f -exec chmod 644 {} \;
  rm /tmp/milkshow_dist.tar.gz
  echo 'Servidor: dist atualizado OK'
"

echo ""
echo "================================================="
echo " Frontend deployado com sucesso!"
echo " Acesse: https://milshow.com.br/app/"
echo "================================================="

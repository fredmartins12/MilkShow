#!/bin/bash
# =============================================================
# MilkShow — Migra Evolution v1 → v2 (roda UMA VEZ no servidor)
# Uso: bash /opt/milkshow/deploy/migrate_to_v2.sh
# =============================================================
set -e

APP_DIR="/opt/milkshow"

echo "================================================="
echo " MilkShow — Migração Evolution v1 → v2"
echo "================================================="

# 1. Para e remove containers antigos (v1)
echo "[1/4] Parando Evolution v1..."
docker stop milkshow_evolution 2>/dev/null || true
docker rm   milkshow_evolution 2>/dev/null || true
# Remove imagem v1 para liberar espaço
docker rmi  evolution-api:v1.8.7 2>/dev/null || true

# 2. Garante que POSTGRES_PASSWORD está no .env
if ! grep -q "POSTGRES_PASSWORD" "$APP_DIR/.env"; then
    echo "   Adicionando POSTGRES_PASSWORD ao .env..."
    echo "" >> "$APP_DIR/.env"
    echo "# PostgreSQL para Evolution API v2" >> "$APP_DIR/.env"
    echo "POSTGRES_PASSWORD=milkshow2024pg" >> "$APP_DIR/.env"
fi

# 3. Garante que BOT_URL está correto (endereço do host dentro do Docker)
if ! grep -q "BOT_URL" "$APP_DIR/.env"; then
    echo "   Adicionando BOT_URL ao .env..."
    echo "BOT_URL=http://172.17.0.1:8000" >> "$APP_DIR/.env"
fi

# 4. Sobe Evolution v2 + PostgreSQL + Redis
echo "[2/4] Iniciando Evolution v2 com PostgreSQL..."
cp "$APP_DIR/.env" "$APP_DIR/deploy/.env"
cd "$APP_DIR/deploy"
docker compose pull
docker compose up -d

echo "   Aguardando PostgreSQL + Evolution iniciarem..."
sleep 15

echo "[3/4] Verificando status dos containers..."
docker compose ps

echo "[4/4] Pronto! Agora execute:"
echo "  bash /opt/milkshow/deploy/update.sh"
echo "  (vai criar a instância e gerar o QR para escanear)"

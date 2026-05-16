#!/bin/bash
# =============================================================
# MilkShow — Instala/atualiza Evolution API v2 completo
# Uso: bash /opt/milkshow/deploy/migrate_to_v2.sh
# Pode ser rodado mais de uma vez sem problema
# =============================================================
set -e

APP_DIR="/opt/milkshow"
DEPLOY_DIR="$APP_DIR/deploy"

# ── Carrega .env do bot ───────────────────────────────────────
set -a; source "$APP_DIR/.env" 2>/dev/null || true; set +a

INSTANCE="${EVOLUTION_INSTANCE:-milkshow}"
EV_KEY="${EVOLUTION_KEY:-milkshow2024}"
PG_PASS="${POSTGRES_PASSWORD:-milkshow2024pg}"

echo "================================================="
echo " MilkShow — Setup Evolution API v2"
echo " Instância : $INSTANCE"
echo " Servidor  : $(curl -s ifconfig.me 2>/dev/null || echo 'desconhecido')"
echo "================================================="

# ── 1. Garante dependências ───────────────────────────────────
echo ""
echo "[1/7] Verificando Docker..."
if ! command -v docker &>/dev/null; then
    echo "   Instalando Docker..."
    curl -fsSL https://get.docker.com | sh
fi

# ── 2. Para e remove containers antigos ──────────────────────
echo "[2/7] Parando containers antigos..."
docker stop milkshow_evolution milkshow_postgres milkshow_redis 2>/dev/null || true
docker rm   milkshow_evolution milkshow_postgres milkshow_redis 2>/dev/null || true

# ── 3. Garante variáveis no .env do bot ──────────────────────
echo "[3/7] Atualizando .env do bot..."
if ! grep -q "^POSTGRES_PASSWORD" "$APP_DIR/.env"; then
    echo ""                                    >> "$APP_DIR/.env"
    echo "# PostgreSQL — Evolution API v2"     >> "$APP_DIR/.env"
    echo "POSTGRES_PASSWORD=$PG_PASS"          >> "$APP_DIR/.env"
    echo "   POSTGRES_PASSWORD adicionado"
fi
if ! grep -q "^BOT_URL" "$APP_DIR/.env"; then
    echo "BOT_URL=http://172.17.0.1:8000"      >> "$APP_DIR/.env"
    echo "   BOT_URL adicionado (Docker bridge → host)"
fi

# Recarrega com os novos valores
set -a; source "$APP_DIR/.env"; set +a
PG_PASS="${POSTGRES_PASSWORD:-milkshow2024pg}"
IP_PUB=$(curl -s ifconfig.me 2>/dev/null || echo "178.104.252.193")

# ── 4. Gera deploy/.env (para postgres no docker-compose) ────
echo "[4/7] Gerando arquivos de configuração..."
echo "POSTGRES_PASSWORD=$PG_PASS" > "$DEPLOY_DIR/.env"

# ── 5. Gera evolution.env (lido pelo container via env_file) ──
cat > "$DEPLOY_DIR/evolution.env" << ENVEOF
# ── Gerado por migrate_to_v2.sh — NÃO editar manualmente ──
# Regenere executando: bash /opt/milkshow/deploy/migrate_to_v2.sh

SERVER_URL=http://${IP_PUB}:8080

AUTHENTICATION_API_KEY=${EV_KEY}
AUTHENTICATION_EXPOSE_IN_FETCH_INSTANCES=true

DATABASE_PROVIDER=postgresql
DATABASE_CONNECTION_URI=postgresql://evolution:${PG_PASS}@postgres:5432/evolution?schema=public
DATABASE_CONNECTION_CLIENT_NAME=milkshow_client
DATABASE_SAVE_DATA_INSTANCE=true
DATABASE_SAVE_DATA_NEW_MESSAGE=true
DATABASE_SAVE_MESSAGE_UPDATE=true
DATABASE_SAVE_DATA_CONTACTS=true
DATABASE_SAVE_DATA_CHATS=true
DATABASE_SAVE_DATA_LABELS=true
DATABASE_SAVE_DATA_HISTORIC=true

CACHE_REDIS_ENABLED=true
CACHE_REDIS_URI=redis://redis:6379/6
CACHE_REDIS_TTL=604800
CACHE_LOCAL_ENABLED=false

WEBHOOK_GLOBAL_ENABLED=true
WEBHOOK_GLOBAL_URL=http://172.17.0.1:8000/webhook/evolution
WEBHOOK_GLOBAL_WEBHOOK_BY_EVENTS=false
WEBHOOK_EVENTS_MESSAGES_UPSERT=true
WEBHOOK_EVENTS_MESSAGES_UPDATE=false
WEBHOOK_EVENTS_SEND_MESSAGE=false
WEBHOOK_EVENTS_QRCODE_UPDATED=false
WEBHOOK_EVENTS_CONNECTION_UPDATE=false

CONFIG_SESSION_PHONE_CLIENT=MilkShow
CONFIG_SESSION_PHONE_NAME=Chrome
WA_BUSINESS_TOKEN_WEBHOOK=false

DEL_INSTANCE=false
STORE_CLEANING_INTERVAL=7200
ENVEOF

echo "   evolution.env gerado"

# ── 6. Sobe containers ────────────────────────────────────────
echo "[5/7] Iniciando PostgreSQL + Redis + Evolution API v2..."
cd "$DEPLOY_DIR"
docker compose pull --quiet 2>&1 | tail -3
docker compose up -d

echo ""
echo "   Aguardando Evolution API inicializar (até 90s)..."
READY=0
for i in $(seq 1 30); do
    CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8080/" 2>/dev/null || echo "000")
    if [ "$CODE" != "000" ]; then
        echo "   Evolution pronto (HTTP $CODE) após ${i}0s aprox."
        READY=1
        break
    fi
    printf "   %ds..." "$((i * 3))"
    sleep 3
done

if [ "$READY" = "0" ]; then
    echo ""
    echo "   AVISO: Evolution não respondeu após 90s. Verificando logs..."
    docker logs milkshow_evolution --tail 20 2>/dev/null || true
    echo ""
    echo "   Aguarde mais 30s e re-execute o script."
    exit 1
fi

sleep 5  # tempo extra para banco de dados migrar

# ── 7. Cria instância e gera QR ──────────────────────────────
echo "[6/7] Configurando instância WhatsApp..."

# Verifica se já existe
INST_JSON=$(curl -s "http://localhost:8080/instance/fetchInstances" \
    -H "apikey: $EV_KEY" 2>/dev/null || echo "[]")
COUNT=$(echo "$INST_JSON" | python3 -c \
    "import sys,json; d=json.load(sys.stdin); print(len(d) if isinstance(d,list) else 0)" 2>/dev/null || echo "0")

if [ "$COUNT" = "0" ]; then
    echo "   Criando instância '$INSTANCE'..."
    CREATE=$(curl -s -X POST "http://localhost:8080/instance/create" \
        -H "apikey: $EV_KEY" \
        -H "Content-Type: application/json" \
        -d "{\"instanceName\":\"$INSTANCE\",\"qrcode\":true,\"integration\":\"WHATSAPP-BAILEYS\"}" \
        2>/dev/null || echo "{}")
    echo "   Criação: $(echo "$CREATE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('instance',{}).get('state','?'))" 2>/dev/null || echo 'resposta inválida')"
    sleep 5
else
    echo "   Instância '$INSTANCE' já existe"
fi

echo "[7/7] Gerando QR code para conexão WhatsApp..."
sleep 3
QR_JSON=$(curl -s "http://localhost:8080/instance/connect/$INSTANCE" \
    -H "apikey: $EV_KEY" 2>/dev/null || echo "{}")

python3 << PYEOF
import sys, json, base64

raw = """$QR_JSON"""
try:
    data = json.loads(raw)
except:
    data = {}

state  = (data.get("instance") or {}).get("state") or data.get("state") or data.get("status") or ""
qr_b64 = data.get("base64", "")

if state in ("open", "connected", "online"):
    print("")
    print("========================================")
    print("  WhatsApp JA CONECTADO! Estado: " + state)
    print("========================================")
elif qr_b64:
    try:
        img = base64.b64decode(qr_b64.split(",")[-1])
        with open("/tmp/qr_milkshow.png", "wb") as f:
            f.write(img)
        print("")
        print("========================================")
        print("  QR salvo em /tmp/qr_milkshow.png")
        print("  Copie para seu PC e escaneie:")
        print("  scp root@${IP_PUB}:/tmp/qr_milkshow.png .")
        print("")
        print("  No WhatsApp iPhone:")
        print("  Ajustes > Dispositivos vinculados")
        print("  > Adicionar dispositivo > Escanear QR")
        print("========================================")
    except Exception as e:
        print("Erro ao salvar QR: " + str(e))
else:
    print("Estado atual: " + str(state) or str(data))
    print("")
    print("Se Evolution ainda esta iniciando, aguarde 15s e execute:")
    print("  curl -s http://localhost:8080/instance/connect/$INSTANCE -H 'apikey: $EV_KEY' | python3 -m json.tool")
PYEOF

# ── 8. Reinicia o bot ────────────────────────────────────────
echo ""
echo "Reiniciando bot MilkShow..."
systemctl restart milkshow-bot 2>/dev/null && sleep 2 && \
    systemctl is-active --quiet milkshow-bot && echo "   Bot OK" || echo "   Verifique: journalctl -u milkshow-bot -n 20"

echo ""
echo "================================================="
echo " Pronto! Próximos passos:"
echo " 1. Copie o QR:  scp root@${IP_PUB}:/tmp/qr_milkshow.png ."
echo " 2. Escaneie no WhatsApp (Dispositivos vinculados)"
echo " 3. Teste enviando 'oi' para o número do bot"
echo ""
echo " Logs do bot:       journalctl -u milkshow-bot -f"
echo " Logs do Evolution: docker logs milkshow_evolution -f"
echo "================================================="

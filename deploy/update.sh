#!/bin/bash
# =============================================================
# MilkShow — Atualiza código e reinicia tudo no servidor
# Uso: bash /opt/milkshow/deploy/update.sh
# =============================================================
set -e

APP_DIR="/opt/milkshow"

# Carrega variáveis do .env
set -a; source "$APP_DIR/.env"; set +a

INSTANCE="${EVOLUTION_INSTANCE:-milkshow}"
EV_KEY="${EVOLUTION_KEY:-milkshow2024}"
EV_LOCAL="http://localhost:8080"

echo "================================================="
echo " MilkShow — Atualizando servidor"
echo "================================================="

echo "[1/5] Baixando código novo do GitHub..."
git -C "$APP_DIR" pull

echo "[2/5] Atualizando dependências Python..."
"$APP_DIR/venv/bin/pip" install --quiet --upgrade pip
"$APP_DIR/venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"

echo "[3/5] Atualizando Evolution API (Docker)..."
cp "$APP_DIR/.env" "$APP_DIR/deploy/.env"
cd "$APP_DIR/deploy"
docker compose pull --quiet
docker compose up -d

echo "   Aguardando Evolution API inicializar..."
for i in $(seq 1 30); do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$EV_LOCAL/" 2>/dev/null || echo "000")
    if [ "$STATUS" = "200" ] || [ "$STATUS" = "404" ]; then
        echo "   Evolution OK (status $STATUS)"
        break
    fi
    echo "   Tentativa $i/30 — aguardando..."
    sleep 3
done

echo "[4/5] Configurando instância Evolution..."
# Verifica se instância existe
INSTANCES=$(curl -s "$EV_LOCAL/instance/fetchInstances" \
    -H "apikey: $EV_KEY" 2>/dev/null || echo "[]")
COUNT=$(echo "$INSTANCES" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d) if isinstance(d,list) else 0)" 2>/dev/null || echo "0")

if [ "$COUNT" = "0" ]; then
    echo "   Criando instância '$INSTANCE'..."
    curl -s -X POST "$EV_LOCAL/instance/create" \
        -H "apikey: $EV_KEY" \
        -H "Content-Type: application/json" \
        -d "{\"instanceName\": \"$INSTANCE\", \"qrcode\": true, \"integration\": \"WHATSAPP-BAILEYS\"}" \
        | python3 -m json.tool 2>/dev/null || true
    sleep 3
else
    echo "   Instância '$INSTANCE' já existe ($COUNT encontrada(s))"
fi

# Configura webhook para o bot
BOT_WEBHOOK="${BOT_URL:-http://172.17.0.1:8000}/webhook/evolution"
echo "   Configurando webhook → $BOT_WEBHOOK"
curl -s -X POST "$EV_LOCAL/webhook/set/$INSTANCE" \
    -H "apikey: $EV_KEY" \
    -H "Content-Type: application/json" \
    -d "{
        \"url\": \"$BOT_WEBHOOK\",
        \"webhook_by_events\": false,
        \"webhook_base64\": false,
        \"events\": [\"MESSAGES_UPSERT\"]
    }" | python3 -m json.tool 2>/dev/null || true

echo "[5/5] Gerando QR code..."
QR_RESPONSE=$(curl -s "$EV_LOCAL/instance/connect/$INSTANCE" \
    -H "apikey: $EV_KEY" 2>/dev/null || echo "{}")

echo "$QR_RESPONSE" | python3 -c "
import sys, json, base64

data = json.load(sys.stdin)
qr_b64 = data.get('base64', '')
state  = data.get('state', data.get('status', ''))

if state in ('open', 'connected'):
    print('WhatsApp JA CONECTADO! Estado: ' + state)
elif qr_b64:
    img_data = base64.b64decode(qr_b64.split(',')[-1])
    path = '/tmp/qr_milkshow.png'
    with open(path, 'wb') as f:
        f.write(img_data)
    print('QR salvo em ' + path)
    print('Para copiar: scp root@178.104.252.193:/tmp/qr_milkshow.png .')
    print('Escaneie no WhatsApp: Dispositivos vinculados > Vincular dispositivo')
else:
    print('Estado atual: ' + state)
    print('Se a instancia ainda esta iniciando, aguarde 10s e execute:')
    print('  curl -s http://localhost:8080/instance/connect/$INSTANCE -H apikey:$EV_KEY')
" 2>/dev/null || echo "$QR_RESPONSE"

echo "[bot] Reiniciando serviço MilkShow..."
systemctl restart milkshow-bot
sleep 2
systemctl status milkshow-bot --no-pager

echo ""
echo "================================================="
echo " Atualização concluída!"
echo " Logs: journalctl -u milkshow-bot -f"
echo "================================================="

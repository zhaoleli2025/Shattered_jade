#!/usr/bin/env bash
# Public-URL tunnel for the web prototype — the cpolar format, like your other
# game at *.cpolar.io. Serves battles AND the world map over one https URL.
#
# One-time setup (token from https://dashboard.cpolar.com → 验证 → authtoken):
#     /data/zhaoleli/opt/cpolar/cpolar authtoken <你的token>
#
# Usage:  bash tools/tunnel.sh [port]      (default 8765)
#         bash tools/tunnel.sh stop
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CPOLAR=/data/zhaoleli/opt/cpolar/cpolar
PORT="${1:-8765}"
LOG=/tmp/cpolar_sj.log

if [ "$1" = "stop" ]; then
  pkill -f "cpolar http" 2>/dev/null && echo "tunnel stopped" || echo "no tunnel running"
  pkill -f "tools/serve.py" 2>/dev/null && echo "server stopped" || true
  exit 0
fi

if [ ! -f "$HOME/.cpolar/cpolar.yml" ]; then
  echo "one-time setup needed — paste your authtoken (dashboard.cpolar.com):"
  echo "  $CPOLAR authtoken <你的token>"
  exit 1
fi

# the no-cache dev server, if not already listening
if ! ss -tln 2>/dev/null | grep -q ":$PORT "; then
  nohup python3 "$ROOT/tools/serve.py" "$PORT" >/tmp/serve_sj.log 2>&1 &
  sleep 1
fi

pkill -f "cpolar http" 2>/dev/null || true
# try the reserved name first (paid plans, like the ntw one); fall back to random
SUB="${SJ_SUBDOMAIN:-shatteredjade}"
nohup "$CPOLAR" http -subdomain="$SUB" "$PORT" -log=stdout -log-level=info >"$LOG" 2>&1 &
printf "tunnelling"
URL=""
for i in $(seq 1 25); do
  URL=$(grep -oE "https://[a-z0-9-]+\.[a-z0-9]+\.cpolar\.(io|top|cn)" "$LOG" | head -1)
  [ -n "$URL" ] && break
  if [ "$i" = 8 ] && grep -qiE "error|failed|not allowed" "$LOG"; then
    pkill -f "cpolar http" 2>/dev/null || true
    : >"$LOG"
    nohup "$CPOLAR" http "$PORT" -log=stdout -log-level=info >>"$LOG" 2>&1 &
  fi
  printf "."
  sleep 1
done
echo
if [ -n "$URL" ]; then
  echo "公网地址 public URL:"
  echo "  battles:  $URL/"
  echo "  the map:  $URL/world.html"
  echo "(free-tier subdomain rotates each restart — rerun this to get the new one;"
  echo " stop with: bash tools/tunnel.sh stop)"
else
  echo "no URL after 25s — check $LOG (token not set? network?)"
  exit 1
fi

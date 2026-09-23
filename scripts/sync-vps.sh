#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env.vps}"

load_env_file() {
  local file="$1"
  local line key value
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    [[ "$line" != *=* ]] && continue
    key="${line%%=*}"
    value="${line#*=}"
    key="${key#"${key%%[![:space:]]*}"}"
    key="${key%"${key##*[![:space:]]}"}"
    value="${value#"${value%%[![:space:]]*}"}"
    if [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
      printf -v "$key" '%s' "$value"
      export "$key"
    fi
  done < "$file"
}

if [[ -f "$ENV_FILE" ]]; then
  load_env_file "$ENV_FILE"
fi

DEPLOY_HOST="${DEPLOY_HOST:-45.32.63.217}"
DEPLOY_USER="${DEPLOY_USER:-root}"
DEPLOY_PORT="${DEPLOY_PORT:-22}"
DEPLOY_PATH="${DEPLOY_PATH:-/root/mtips5s_deepseek_harness}"

SSH_TARGET="${DEPLOY_USER}@${DEPLOY_HOST}"
SSH_OPTS=(-p "$DEPLOY_PORT" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15)
RSYNC_SSH="ssh -p $DEPLOY_PORT -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15"

echo "=== [Sync to VPS] ==="
echo "Local source: ${ROOT_DIR}/"
echo "Remote target: ${SSH_TARGET}:${DEPLOY_PATH}/"

# 1. Connectivity check
echo "[1/3] Testing SSH connectivity..."
ssh "${SSH_OPTS[@]}" "$SSH_TARGET" "mkdir -p '$DEPLOY_PATH'"
echo "Connected and ensured remote directory exists."

# 2. Rsync transfer
echo "[2/3] Syncing files via rsync..."
rsync -avz --delete \
  -e "$RSYNC_SSH" \
  --exclude '.git/' \
  --exclude '.env' \
  --exclude '.env.vps' \
  --exclude 'node_modules/' \
  --exclude '.DS_Store' \
  --exclude 'dist/' \
  --exclude 'tmp/' \
  --exclude '*.log' \
  "$ROOT_DIR/" "$SSH_TARGET:$DEPLOY_PATH/"

# 3. Remote Verification
echo "[3/3] Verifying sync on remote VPS..."
ssh "${SSH_OPTS[@]}" "$SSH_TARGET" "
  echo 'Remote files in $DEPLOY_PATH:'
  ls -la '$DEPLOY_PATH/.agents/skills/jev-usage-router'
  ls -la '$DEPLOY_PATH/.jev'
  echo ''
  echo 'Running JEV router smoke test on VPS:'
  python3 '$DEPLOY_PATH/.agents/skills/jev-usage-router/scripts/smoke_test.py'
"

echo "=== Sync to VPS Complete Successfully! ==="

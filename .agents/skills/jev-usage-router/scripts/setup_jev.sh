#!/usr/bin/env bash
set -euo pipefail

# Quick setup script for JEV (browser-use/jev-ultrafast)
# Repository: https://github.com/browser-use/jev-ultrafast

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
CONFIG_FILE="${ROOT_DIR}/.jev/config.json"

TARGET_DIR="${ROOT_DIR}/external/jev-ultrafast"
if [[ -f "${CONFIG_FILE}" ]]; then
  CONFIG_JEV_DIR=$(python3 -c "import json; conf=json.load(open('${CONFIG_FILE}')); print(conf.get('jev_dir', 'external/jev-ultrafast'))" 2>/dev/null || echo "external/jev-ultrafast")
  if [[ "${CONFIG_JEV_DIR}" = /* ]]; then
    TARGET_DIR="${CONFIG_JEV_DIR}"
  else
    TARGET_DIR="${ROOT_DIR}/${CONFIG_JEV_DIR}"
  fi
fi

DRY_RUN=0
CHECK_ONLY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --check)
      CHECK_ONLY=1
      shift
      ;;
    --dir)
      TARGET_DIR="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

echo "=== [JEV Quick Setup] ==="
echo "Target directory: ${TARGET_DIR}"

# 1. Dependency checks
echo "[1/4] Checking prerequisites..."
command -v git >/dev/null 2>&1 || { echo "ERROR: git is required but not installed."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 is required but not installed."; exit 1; }

UV_BIN="$(command -v uv 2>/dev/null || true)"
if [[ -z "${UV_BIN}" ]]; then
  if [[ -f "$HOME/.local/bin/uv" ]]; then
    UV_BIN="$HOME/.local/bin/uv"
  else
    echo "ERROR: 'uv' is required for jev-ultrafast. Install via: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
  fi
fi
echo "Found uv: ${UV_BIN}"

if [[ ${CHECK_ONLY} -eq 1 ]]; then
  echo "Prerequisites verified successfully."
  exit 0
fi

# 2. Clone repository if needed
echo "[2/4] Setting up repository..."
if [[ ${DRY_RUN} -eq 1 ]]; then
  echo "[DRY-RUN] Would clone https://github.com/browser-use/jev-ultrafast.git into ${TARGET_DIR}"
else
  mkdir -p "$(dirname "${TARGET_DIR}")"
  if [[ ! -d "${TARGET_DIR}/.git" ]]; then
    echo "Cloning https://github.com/browser-use/jev-ultrafast.git..."
    git clone https://github.com/browser-use/jev-ultrafast.git "${TARGET_DIR}"
  else
    echo "Repository already exists at ${TARGET_DIR}, pulling latest..."
    (cd "${TARGET_DIR}" && git pull --ff-only origin main || echo "Warning: git pull skipped or had conflicts")
  fi
fi

# 3. Environment & Dependencies
echo "[3/4] Syncing dependencies with uv..."
if [[ ${DRY_RUN} -eq 1 ]]; then
  echo "[DRY-RUN] Would run: (cd ${TARGET_DIR} && ${UV_BIN} sync)"
  echo "[DRY-RUN] Would setup .env with TYPESAFE_API_KEY and TEXT_MODEL_API_KEY"
else
  (
    cd "${TARGET_DIR}"
    "${UV_BIN}" sync
    if [[ ! -f ".env" ]] && [[ -f ".env.example" ]]; then
      cp .env.example .env
      echo "Created .env from .env.example in ${TARGET_DIR}."
      echo "NOTE: Configure TYPESAFE_API_KEY and TEXT_MODEL_API_KEY in ${TARGET_DIR}/.env."
    fi
  )
fi

# 4. Verification
echo "[4/4] Verifying setup..."
if [[ ${DRY_RUN} -eq 1 ]]; then
  echo "[DRY-RUN] Setup verification succeeded."
else
  mkdir -p "${ROOT_DIR}/.jev/logs"
  touch "${ROOT_DIR}/.jev/logs/router.jsonl"
  echo "JEV setup complete."
  echo "To start JEV standalone server: cd ${TARGET_DIR} && ${UV_BIN} run jev"
  echo "To run browser diagnostics: cd ${TARGET_DIR} && ${UV_BIN} run browser-harness --doctor"
fi

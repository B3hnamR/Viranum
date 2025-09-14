#!/usr/bin/env bash
set -Eeuo pipefail

# Viranum updater: pull latest from GitHub, rebuild/restart Docker, follow logs
# Usage:
#   bash u.sh [branch] [service]
#   - branch: git branch to pull (default: current branch)
#   - service: docker compose service to tail (default: bot)
#
# Notes:
# - Requires: git, docker with compose v2 (docker compose), bash
# - Reads project .env and reports provider-related settings (ENABLED_PROVIDERS, PROVIDERS_DISPLAY, FIVESIM_API_KEY)
# - On Windows, run via Git Bash or WSL: `bash u.sh`

log() { echo -e "\033[1;34m[U]\033[0m $*"; }
err() { echo -e "\033[1;31m[U-ERROR]\033[0m $*" >&2; }

BRANCH_INPUT=${1:-}
SERVICE_TO_TAIL=${2:-bot}

get_current_branch() {
  git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main"
}

trap 'err "An error occurred. Check the output above."' ERR

if ! command -v git >/dev/null 2>&1; then err "git not found"; exit 1; fi
if ! command -v docker >/dev/null 2>&1; then err "docker not found"; exit 1; fi

if ! docker compose version >/dev/null 2>&1; then
  err "docker compose v2 not available. Please install Docker Compose V2."
  exit 1
fi

BRANCH=${BRANCH_INPUT:-$(get_current_branch)}

log "Git: fetching origin..."
 git fetch origin

log "Git: switching to branch ${BRANCH}..."
 git checkout "${BRANCH}"

log "Git: pulling latest (rebase) from origin/${BRANCH}..."
 git pull --rebase origin "${BRANCH}"

log "Docker: building images (pull base layers)..."
 docker compose build --pull

log "Docker: (re)starting services..."
 docker compose up -d --remove-orphans

log "Docker: services status:"
 docker compose ps

# Report provider-related env (if present)
if [ -f .env ]; then
  ENABLED_PROVIDERS_VAL=$(grep -E '^ENABLED_PROVIDERS=' .env | sed 's/^ENABLED_PROVIDERS=//') || true
  PROVIDERS_DISPLAY_VAL=$(grep -E '^PROVIDERS_DISPLAY=' .env | sed 's/^PROVIDERS_DISPLAY=//') || true
  FIVESIM_API_KEY_VAL=$(grep -E '^FIVESIM_API_KEY=' .env | sed 's/^FIVESIM_API_KEY=//') || true

  if [ -n "$ENABLED_PROVIDERS_VAL" ]; then
    log "Providers enabled: $ENABLED_PROVIDERS_VAL"
  else
    log "Providers enabled: (default) numberland"
  fi

  if [ -n "$PROVIDERS_DISPLAY_VAL" ]; then
    log "Providers display: $PROVIDERS_DISPLAY_VAL"
  else
    log "Providers display: numberland:Numberland (default)"
  fi

  if [ -n "$FIVESIM_API_KEY_VAL" ]; then
    log "5SIM key: set"
  else
    log "5SIM key: not set"
  fi
fi

# If network or containers were previously named under the old project, ensure compose picks new names
# (Optional clean-up can be added here if needed)

log "Following logs for service: ${SERVICE_TO_TAIL} (Ctrl+C to stop)"
 docker compose logs -f "${SERVICE_TO_TAIL}"

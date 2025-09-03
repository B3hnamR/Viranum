#!/usr/bin/env bash
# Viranum bootstrapper: Provision a fresh Linux server and run the bot
# - Installs Git, Docker (with Compose v2), and prerequisites
# - Clones/updates the repository into /opt/viranum (or uses current repo)
# - Configures .env (interactive prompt) if missing
# - Builds and starts Docker services
# - Follows bot logs
#
# Usage examples:
#   sudo bash setup.sh "https://github.com/USERNAME/Viranum.git" main
#   sudo bash setup.sh                              # if already inside repo, will use it
#
# ENV overrides:
#   REPO_URL, BRANCH, APP_DIR, SERVICE_TAIL, NON_INTERACTIVE, BOT_TOKEN, NUMBERLAND_API_KEY, ADMIN_IDS

set -Eeuo pipefail

# ----------------------------- Config -----------------------------
REPO_URL=${REPO_URL:-${1:-}}
BRANCH=${BRANCH:-${2:-main}}
APP_DIR=${APP_DIR:-/opt/viranum}
SERVICE_TAIL=${SERVICE_TAIL:-bot}
NON_INTERACTIVE=${NON_INTERACTIVE:-0}

COLOR_INFO="\033[1;34m"
COLOR_ERR="\033[1;31m"
COLOR_OK="\033[1;32m"
COLOR_END="\033[0m"

info() { echo -e "${COLOR_INFO}[INFO]${COLOR_END} $*"; }
ok()   { echo -e "${COLOR_OK}[ OK ]${COLOR_END} $*"; }
err()  { echo -e "${COLOR_ERR}[FAIL]${COLOR_END} $*" >&2; }

require_root() {
  if [ "$(id -u)" -ne 0 ]; then
    err "Please run as root (use sudo)."; exit 1;
  fi
}

install_prereqs() {
  info "Installing prerequisites (curl, git, ca-certificates)..."
  if command -v apt-get >/dev/null 2>&1; then
    apt-get update -y
    apt-get install -y curl git ca-certificates
  elif command -v dnf >/dev/null 2>&1; then
    dnf install -y curl git ca-certificates
  elif command -v yum >/dev/null 2>&1; then
    yum install -y curl git ca-certificates
  elif command -v zypper >/dev/null 2>&1; then
    zypper install -y curl git ca-certificates
  else
    err "Unsupported distribution. Install curl and git manually."; exit 1
  fi
}

install_docker() {
  if command -v docker >/dev/null 2>&1; then
    ok "Docker already installed: $(docker --version)"
  else
    info "Installing Docker using get.docker.com..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm -f get-docker.sh
    systemctl enable docker
    systemctl start docker
    ok "Docker installed."
  fi

  if docker compose version >/dev/null 2>&1; then
    ok "Docker Compose v2 available: $(docker compose version)"
  else
    info "Installing Docker Compose v2 plugin..."
    if command -v apt-get >/dev/null 2>&1; then
      apt-get update -y || true
      apt-get install -y docker-compose-plugin || true
    fi
    if ! docker compose version >/dev/null 2>&1; then
      info "Falling back to manual plugin install..."
      mkdir -p /usr/local/lib/docker/cli-plugins
      curl -L "https://github.com/docker/compose/releases/download/v2.27.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/lib/docker/cli-plugins/docker-compose
      chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
    fi
    docker compose version >/dev/null 2>&1 && ok "Docker Compose installed." || { err "Failed to install docker compose"; exit 1; }
  fi

  # Add current (sudo) user to docker group if applicable
  local target_user=${SUDO_USER:-}
  if [ -n "$target_user" ]; then
    if id -nG "$target_user" | grep -qw docker; then
      ok "User $target_user already in docker group"
    else
      info "Adding $target_user to docker group"
      usermod -aG docker "$target_user" || true
      info "You may need to re-login for group changes to take effect."
    fi
  fi
}

prepare_repo() {
  # If running inside a git repo and REPO_URL not provided, use current directory
  if git rev-parse --is-inside-work-tree >/dev/null 2>&1 && [ -z "$REPO_URL" ]; then
    ok "Detected existing git repository at $(pwd). Using current directory."
    APP_DIR=$(pwd)
    return
  fi

  if [ -z "$REPO_URL" ]; then
    err "REPO_URL not provided and not inside a repository. Usage: setup.sh <repo_url> [branch]"; exit 1
  fi

  info "Cloning/updating repository at $APP_DIR (branch: $BRANCH)"
  if [ -d "$APP_DIR/.git" ]; then
    cd "$APP_DIR"
    git fetch origin
    git checkout "$BRANCH"
    git pull --rebase origin "$BRANCH"
  else
    mkdir -p "$APP_DIR"
    git clone -b "$BRANCH" "$REPO_URL" "$APP_DIR"
    cd "$APP_DIR"
  fi
}

configure_env() {
  if [ -f .env ]; then
    ok ".env already exists. Skipping creation."
    return
  fi
  if [ ! -f .env.example ]; then
    err ".env.example not found. Cannot prepare environment."; exit 1
  fi
  info "Creating .env from .env.example"
  cp .env.example .env

  if [ "$NON_INTERACTIVE" = "1" ]; then
    ok "NON_INTERACTIVE=1: skipping prompts; ensure env vars are set externally."
    return
  fi

  echo ""
  read -r -p "Enter BOT_TOKEN: " BOT_TOKEN_INPUT
  read -r -p "Enter NUMBERLAND_API_KEY: " NUMBERLAND_API_KEY_INPUT
  read -r -p "Enter ADMIN_IDS (comma-separated, e.g., 123,456): " ADMIN_IDS_INPUT

  # Update .env keys in place
  sed -i "s|^BOT_TOKEN=.*|BOT_TOKEN=${BOT_TOKEN_INPUT}|" .env
  sed -i "s|^NUMBERLAND_API_KEY=.*|NUMBERLAND_API_KEY=${NUMBERLAND_API_KEY_INPUT}|" .env
  sed -i "s|^ADMIN_IDS=.*|ADMIN_IDS=${ADMIN_IDS_INPUT}|" .env

  ok ".env configured."
}

compose_up() {
  info "Building Docker images (pulling base layers)"
  docker compose build --pull

  info "Starting services (detached)"
  docker compose up -d --remove-orphans

  info "Services status"
  docker compose ps

  ok "Bot should be running. Following logs (Ctrl+C to stop):"
  docker compose logs -f "$SERVICE_TAIL"
}

main() {
  require_root
  install_prereqs
  install_docker
  prepare_repo
  configure_env
  compose_up
}

main "$@"

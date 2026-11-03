#!/usr/bin/env bash
# Recreate all local dev containers so mounted code + .env changes take effect.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

export COMPOSE_PROJECT_NAME=coneshare

BUILD=0
MALWARE=0

usage() {
  cat <<'EOF'
Usage: ./restart-docker-dev.sh [options]

  (no options)   Force-recreate every service (frontend, backend, core, workers, …)
  --build        Rebuild images first (use after package.json / Dockerfile / requirements changes)
  --malware      Include clamav profile (same as make up.malware)
  -h, --help     Show this help

Examples:
  ./restart-docker-dev.sh
  ./restart-docker-dev.sh --build
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --build) BUILD=1; shift ;;
    --malware) MALWARE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

COMPOSE=(docker-compose)
if [[ "$MALWARE" -eq 1 ]]; then
  COMPOSE+=(--profile malware)
fi

echo "==> Recreating Coneshare dev stack (COMPOSE_PROJECT_NAME=$COMPOSE_PROJECT_NAME)..."

if [[ "$BUILD" -eq 1 ]]; then
  echo "==> Building images..."
  "${COMPOSE[@]}" build
fi

echo "==> Starting services (force-recreate)..."
"${COMPOSE[@]}" up -d --force-recreate --remove-orphans

echo "==> Compiling backend translation catalogs (if backend is up)..."
"${COMPOSE[@]}" exec -T backend python compile_po.py 2>/dev/null || true

echo ""
echo "Done. Quick checks:"
echo "  Frontend  http://localhost:5173"
echo "  API       http://localhost:8000/api/v1/"
echo "  Portal    http://localhost:3000"
echo "  Logs      COMPOSE_PROJECT_NAME=coneshare docker-compose logs -f"

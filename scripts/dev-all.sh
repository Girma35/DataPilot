#!/usr/bin/env bash
# Run DataPilot FastAPI + Next.js together (Ctrl+C stops both).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -f .venv/bin/activate ]]; then
  # shellcheck source=/dev/null
  source .venv/bin/activate
fi

if ! command -v uvicorn >/dev/null 2>&1; then
  echo "Install deps: pip install -r requirements.txt" >&2
  exit 1
fi

if [[ ! -d "$ROOT/web/node_modules" ]]; then
  echo "Install web deps: (cd web && npm install)" >&2
  exit 1
fi

cleanup() {
  kill "${API_PID:-}" "${WEB_PID:-}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting API http://0.0.0.0:8000 ..."
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000 &
API_PID=$!

echo "Starting web http://localhost:3000 ..."
( cd "$ROOT/web" && npm run dev ) &
WEB_PID=$!

echo ""
echo "  API:  http://localhost:8000/docs"
echo "  Web:  http://localhost:3000"
echo "  Stop: Ctrl+C"
echo ""

wait

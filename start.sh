#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  X Bulk Blocker — one-click launcher (macOS / Linux)
#  Double-click this file or run:  bash start.sh
# ─────────────────────────────────────────────────────────────
set -e

if ! command -v docker &>/dev/null; then
  echo "❌  Docker is not installed."
  echo "    Download Docker Desktop from https://www.docker.com/products/docker-desktop/"
  read -p "Press Enter to exit…"
  exit 1
fi

echo "🔨  Building & starting X Bulk Blocker…"
docker compose up --build -d

echo ""
echo "✅  Running!  Opening http://localhost:7070 in your browser…"
sleep 1.5

# Try to open browser (macOS / Linux)
if command -v open &>/dev/null; then
  open "http://localhost:7070"
elif command -v xdg-open &>/dev/null; then
  xdg-open "http://localhost:7070"
fi

echo ""
echo "To stop:  docker compose down"

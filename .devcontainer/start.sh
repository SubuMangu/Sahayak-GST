#!/usr/bin/env bash
# Start (or restart) the app each time the Codespace starts. Runs uvicorn in the background
# so the lifecycle command returns; FastAPI serves both the built UI and the API on port 8000.
set -euo pipefail
cd "$(dirname "$0")/.."/backend

. .venv/bin/activate

# development => OTP is echoed in the UI / logs (fixed 123456) and SQLite is used (zero config).
export ENVIRONMENT=development
export DATABASE_URL="sqlite+aiosqlite:///./sahayak.db"

# Stop any previous instance, then launch detached.
pkill -f "uvicorn app.main:app" 2>/dev/null || true
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/sahayak.log 2>&1 &

echo "Sahayak GST is starting on port 8000 — open the forwarded URL (ends in -8000.app.github.dev)."

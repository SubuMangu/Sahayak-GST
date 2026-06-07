#!/usr/bin/env bash
# One-time setup for the Codespace: install backend deps, build the frontend.
# The frontend is built with a RELATIVE API base so the SPA talks to the same origin
# (the single forwarded port 8000), which avoids CORS and localhost issues on mobile.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> Installing backend dependencies"
cd backend
python -m venv .venv
. .venv/bin/activate
pip install --upgrade pip >/dev/null
pip install -r requirements.txt
cd ..

echo "==> Building frontend (single-origin: VITE_API_BASE_URL=/api/v1)"
cd frontend
npm install
VITE_API_BASE_URL=/api/v1 npm run build
cd ..

echo "==> Setup complete. The app will start automatically on port 8000."

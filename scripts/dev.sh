#!/usr/bin/env bash
set -e

# Function to clean up background processes on exit
cleanup() {
    echo -e "\nStopping frontend development server..."
    kill "$FRONTEND_PID" 2>/dev/null || true
    exit 0
}

# Trap termination signals
trap cleanup EXIT INT TERM

echo -e "\033[1;36mStarting Admin frontend dev server (Vite)...\033[0m"
npm run dev -w apps/admin-react &
FRONTEND_PID=$!

echo -e "\033[1;32mStarting API backend server (Uvicorn)...\033[0m"
bash ./scripts/dev-server.sh

#!/bin/sh
set -eu

PORT="${AIVIDEO_PORT:-4180}"

uv sync

existing_pid="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | head -n 1 || true)"

if [ -n "$existing_pid" ]; then
  existing_cmd="$(ps -o command= -p "$existing_pid" 2>/dev/null || true)"
  case "$existing_cmd" in
    *aivideo-web*|*ai_video_control.webapp*|*uvicorn*)
      echo "AI Video Studio Console is already running on http://127.0.0.1:$PORT (pid $existing_pid)"
      exit 0
      ;;
    *)
      echo "Port $PORT is already in use by: $existing_cmd"
      echo "If that is the console service, run 'npm run stop' first."
      exit 1
      ;;
  esac
fi

exec uv run aivideo-web

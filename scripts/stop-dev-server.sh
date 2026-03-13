#!/bin/sh
set -eu

PORT="${AIVIDEO_PORT:-4180}"
stopped="0"

for pid in $(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true); do
  cmd="$(ps -o command= -p "$pid" 2>/dev/null || true)"
  case "$cmd" in
    *aivideo-web*|*ai_video_control.webapp*|*uvicorn*)
      kill "$pid" || true
      echo "Stopped AI Video Studio Console (pid $pid)"
      stopped="1"
      ;;
  esac
done

if [ "$stopped" = "1" ]; then
  attempts=0
  while lsof -tiTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; do
    attempts=$((attempts + 1))
    if [ "$attempts" -ge 20 ]; then
      break
    fi
    sleep 0.2
  done

  for pid in $(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true); do
    cmd="$(ps -o command= -p "$pid" 2>/dev/null || true)"
    case "$cmd" in
      *aivideo-web*|*ai_video_control.webapp*|*uvicorn*)
        kill -9 "$pid" || true
        echo "Force stopped AI Video Studio Console (pid $pid)"
        ;;
    esac
  done
fi

if [ "$stopped" = "0" ]; then
  echo "No AI Video Studio Console process is listening on port $PORT"
fi

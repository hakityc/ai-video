#!/usr/bin/env bash
set -eu

PORT="${AIVIDEO_PORT:-4180}"

uv sync

existing_pid="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | head -n 1 || true)"

if [ -n "$existing_pid" ]; then
  existing_cmd="$(ps -o command= -p "$existing_pid" 2>/dev/null || true)"
  case "$existing_cmd" in
    *aivideo-web*|*ai_video_control.webapp*|*uvicorn*)
      echo "AI Video Studio Console is already running on http://127.0.0.1:$PORT (pid $existing_pid)"
      echo "What would you like to do?"
      
      options=("skip" "restart")
      selected=0

      tput civis >/dev/tty 2>/dev/null || true
      trap 'tput cnorm >/dev/tty 2>/dev/null || true' EXIT INT TERM

      echo ""
      echo ""

      print_menu() {
          printf "\033[2A" >/dev/tty
          for i in "${!options[@]}"; do
              if [ $i -eq $selected ]; then
                  printf "❯ \033[36m%s\033[0m\033[K\n" "${options[$i]}" >/dev/tty
              else
                  printf "  %s\033[K\n" "${options[$i]}" >/dev/tty
              fi
          done
      }
      print_menu

      while read -rsn1 key </dev/tty || true; do
          if [[ $key == $'\x1b' ]]; then
              read -rsn2 key2 </dev/tty || true
              if [[ $key2 == '[A' ]]; then
                  ((selected--))
                  [ $selected -lt 0 ] && selected=1
                  print_menu
              elif [[ $key2 == '[B' ]]; then
                  ((selected++))
                  [ $selected -gt 1 ] && selected=0
                  print_menu
              fi
          elif [[ $key == "" ]]; then
              break
          fi
      done

      tput cnorm >/dev/tty 2>/dev/null || true
      trap - EXIT INT TERM
      echo "" >/dev/tty

      if [ $selected -eq 0 ]; then
          exit 0
      else
          echo "Restarting service..."
          bash ./scripts/stop-dev-server.sh
      fi
      ;;
    *)
      echo "Port $PORT is already in use by: $existing_cmd"
      echo "If that is the console service, run 'npm run stop' first."
      exit 1
      ;;
  esac
fi

exec uv run --project apps/api aivideo-web

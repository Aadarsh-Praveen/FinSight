#!/bin/bash
# Starts the MCP Toolbox (internal-only, port 5000) and adk web (public, $PORT) in one
# container. Fails loudly and exits non-zero if the toolbox never becomes ready, or if either
# process dies later -- Cloud Run should see a crashed/unhealthy container, never a silently
# tool-less app. See FinSight's deploy notes in PROGRESS.md for why this is one container
# rather than two Cloud Run services or a swap to ADK's built-in BigQuery toolset.
set -uo pipefail

TOOLBOX_PORT=5000
TOOLBOX_READY_TIMEOUT_SECONDS=30
APP_PORT="${PORT:-8080}"

cd /app/mcp-toolbox
toolbox --config tools.yaml --port "$TOOLBOX_PORT" --address 127.0.0.1 &
TOOLBOX_PID=$!

echo "entrypoint: waiting for MCP Toolbox (pid $TOOLBOX_PID) on port $TOOLBOX_PORT..."
elapsed=0
until curl -sf -o /dev/null "http://127.0.0.1:${TOOLBOX_PORT}/"; do
  if ! kill -0 "$TOOLBOX_PID" 2>/dev/null; then
    echo "FATAL: MCP Toolbox process died during startup." >&2
    exit 1
  fi
  elapsed=$((elapsed + 1))
  if [ "$elapsed" -ge "$TOOLBOX_READY_TIMEOUT_SECONDS" ]; then
    echo "FATAL: MCP Toolbox did not become ready within ${TOOLBOX_READY_TIMEOUT_SECONDS}s." >&2
    kill "$TOOLBOX_PID" 2>/dev/null || true
    exit 1
  fi
  sleep 1
done
echo "entrypoint: MCP Toolbox is ready after ${elapsed}s."

cd /app
adk web --host 0.0.0.0 --port "$APP_PORT" /app/finsight &
APP_PID=$!
echo "entrypoint: adk web (pid $APP_PID) starting on 0.0.0.0:${APP_PORT}."

# If either process dies, tear down the other and exit non-zero so Cloud Run marks the
# container failed instead of continuing to serve with a dead dependency.
wait -n "$TOOLBOX_PID" "$APP_PID"
exit_code=$?
echo "entrypoint: a child process exited (code $exit_code); shutting down the other."
kill "$TOOLBOX_PID" "$APP_PID" 2>/dev/null || true
exit "$exit_code"

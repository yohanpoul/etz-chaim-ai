#!/bin/sh
# Etz Chaim — Claude CLI stub (container-side).
#
# Drop-in replacement for `claude` inside the Docker container. Forwards
# arguments and stdin to the host bridge (server.py running on the Mac),
# which executes the real `claude` CLI with OAuth Max auth and returns
# stdout/stderr/exit_code over HTTP.
#
# Mounted as /usr/local/bin/claude in app + daemon containers. The CLI
# expectation : args after the binary, prompt text on stdin, JSON on
# stdout, regular exit codes.
set -eu

BRIDGE_URL="${ETZ_CHAIM_CLAUDE_BRIDGE_URL:-http://host.docker.internal:11435/exec}"

# Read stdin (the prompt) into a temp file — POST body needs to embed it
STDIN_FILE="$(mktemp)"
trap 'rm -f "$STDIN_FILE" "$RESP_FILE"' EXIT
cat > "$STDIN_FILE"
RESP_FILE="$(mktemp)"

# Build JSON request : { "args": [...], "stdin": "..." }
# Use python3 (always present in our app image) to safely escape strings
PAYLOAD="$(python3 - "$STDIN_FILE" "$@" <<'PY'
import json, sys
stdin_path = sys.argv[1]
args = sys.argv[2:]
with open(stdin_path, "r", encoding="utf-8", errors="replace") as f:
    stdin = f.read()
print(json.dumps({"args": args, "stdin": stdin}))
PY
)"

# POST to bridge — fail loudly if bridge unreachable
HTTP_CODE="$(printf '%s' "$PAYLOAD" \
  | curl -sS -m 605 -o "$RESP_FILE" -w '%{http_code}' \
         -H 'Content-Type: application/json' --data-binary @- "$BRIDGE_URL" \
  || echo 000)"

if [ "$HTTP_CODE" = "000" ]; then
  echo "[claude-stub] bridge unreachable at $BRIDGE_URL" >&2
  exit 127
fi

if [ "$HTTP_CODE" != "200" ]; then
  echo "[claude-stub] bridge HTTP $HTTP_CODE :" >&2
  cat "$RESP_FILE" >&2
  exit 1
fi

# Decode response : print stdout to fd1, stderr to fd2, exit with returned code
python3 - "$RESP_FILE" <<'PY'
import json, sys
with open(sys.argv[1], "r", encoding="utf-8", errors="replace") as f:
    r = json.load(f)
sys.stdout.write(r.get("stdout", ""))
sys.stderr.write(r.get("stderr", ""))
sys.exit(int(r.get("exit_code", 1)))
PY

#!/usr/bin/env bash
# Tests for bin/pi-ecc. Runs against a throwaway HOME and a stub `pi`, so it never
# touches the real config or launches a session.
#
#   bash pi-ecc.test.sh
set -uo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
cmd="$here/pi-ecc"
fails=0
passes=0

setup() {
  TMP="$(mktemp -d)"
  export HOME="$TMP/home"
  export PI_ECC_HOME="$TMP/room"
  export PI_ECC_SOURCE_AGENT_DIR="$TMP/src"
  export PI_BIN="$TMP/stub-pi"
  mkdir -p "$HOME" "$PI_ECC_SOURCE_AGENT_DIR"
  printf '{"auth":"x"}\n' > "$PI_ECC_SOURCE_AGENT_DIR/auth.json"
  printf '{"models":[]}\n' > "$PI_ECC_SOURCE_AGENT_DIR/models.json"
  cat > "$PI_BIN" <<'STUB'
#!/usr/bin/env bash
echo "AGENT_DIR=${PI_CODING_AGENT_DIR:-unset}"
echo "ARGS=$*"
STUB
  chmod +x "$PI_BIN"
}

teardown() { rm -rf "$TMP"; }

check() { # name expected_actual_comparison...
  local name="$1" expected="$2" actual="$3"
  if [ "$expected" = "$actual" ]; then
    passes=$((passes + 1))
    printf '✔ %s\n' "$name"
  else
    fails=$((fails + 1))
    printf '✖ %s\n  expected: %s\n  actual:   %s\n' "$name" "$expected" "$actual"
  fi
}

contains() { # name needle haystack
  local name="$1" needle="$2" haystack="$3"
  case "$haystack" in
    *"$needle"*) passes=$((passes + 1)); printf '✔ %s\n' "$name" ;;
    *) fails=$((fails + 1)); printf '✖ %s\n  missing: %s\n  in:      %s\n' "$name" "$needle" "$haystack" ;;
  esac
}

# --- 1. first run provisions the room ---------------------------------------
setup
out="$("$cmd" --print hello 2>&1)"
check "passes PI_CODING_AGENT_DIR to pi" "AGENT_DIR=$PI_ECC_HOME" "$(printf '%s\n' "$out" | head -1)"
contains "passes arguments through" "ARGS=--print hello" "$out"
[ -f "$PI_ECC_HOME/settings.json" ] && check "settings.json created" ok ok || check "settings.json created" ok missing
contains "pi-ecc package declared" "EricMarcantonio/pi-ecc" "$(cat "$PI_ECC_HOME/settings.json")"
contains "pi-subagents package declared" "pi-subagents" "$(cat "$PI_ECC_HOME/settings.json")"
[ -L "$PI_ECC_HOME/auth.json" ] && check "auth.json symlinked" ok ok || check "auth.json symlinked" ok missing
[ -L "$PI_ECC_HOME/models.json" ] && check "models.json symlinked" ok ok || check "models.json symlinked" ok missing
teardown

# --- 2. off / on ------------------------------------------------------------
setup
"$cmd" --print init >/dev/null 2>&1
out="$("$cmd" off 2>&1)"
contains "off says what happened" "off" "$out"
cat_settings="$(cat "$PI_ECC_HOME/settings.json")"
case "$cat_settings" in
  *EricMarcantonio/pi-ecc*) check "off removes the ECC entry" removed still-present ;;
  *) check "off removes the ECC entry" removed removed ;;
esac
contains "off keeps pi-subagents" "pi-subagents" "$cat_settings"

out="$("$cmd" status 2>&1)"
contains "status reports off" "off" "$out"

"$cmd" on >/dev/null 2>&1
contains "on restores the ECC entry" "EricMarcantonio/pi-ecc" "$(cat "$PI_ECC_HOME/settings.json")"
out="$("$cmd" status 2>&1)"
contains "status reports on" "on" "$out"
teardown

# --- 3. idempotent, and does not clobber an existing settings file ----------
setup
mkdir -p "$PI_ECC_HOME"
printf '{"defaultModel":"keep-me","defaultProvider":"ollama","packages":[]}\n' > "$PI_ECC_HOME/settings.json"
"$cmd" on >/dev/null 2>&1
"$cmd" on >/dev/null 2>&1
settings="$(cat "$PI_ECC_HOME/settings.json")"
contains "user settings preserved" "keep-me" "$settings"
count="$(printf '%s' "$settings" | grep -o "EricMarcantonio/pi-ecc" | wc -l | tr -d ' ')"
check "no duplicate entries after two runs" "1" "$count"
teardown

# --- 4. refuses to invent credentials --------------------------------------
setup
rm -f "$PI_ECC_SOURCE_AGENT_DIR/auth.json"
out="$("$cmd" --print hi 2>&1)"; rc=$?
check "missing auth is a hard error" "1" "$rc"
contains "missing auth explains itself" "auth.json" "$out"
teardown

# --- 5. usage ---------------------------------------------------------------
setup
out="$("$cmd" help 2>&1)"
contains "help documents on" "on" "$out"
contains "help documents off" "off" "$out"
teardown

printf '\n%s passed, %s failed\n' "$passes" "$fails"
[ "$fails" -eq 0 ]

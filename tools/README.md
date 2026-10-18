# tools

Local commands kept next to the config that owns them. `~/.local/bin` symlinks into here so they
are on `PATH` without a `.zshrc` edit.

## pi-ecc

`pi-ecc` starts pi in a **clean room**: a separate config dir (`~/.pi-ecc-agent`) whose only packages
are `pi-ecc` and `pi-subagents`. Your real setup — superpowers, caveman, graft, searxng,
claude-bridge — never loads there, and nothing there can flip ECC on in your normal sessions.

```bash
pi-ecc                      # session with only the ECC bundle
pi-ecc --print "…"          # anything after the command goes to pi
pi-ecc on | off             # add / remove the ECC bundle in the room
pi-ecc status               # on/off
pi-ecc where                # room dir + settings path
pi-ecc update               # update the room's packages
```

The room is provisioned on first run: `auth.json`, `models.json` and `models-store.json` are
**symlinked** from `$PI_CODING_AGENT_DIR` (one source of truth, no re-login), and `defaultProvider` /
`defaultModel` are copied from its settings when the room has none.

Why a separate config dir and not a settings toggle: pi has no settings-write API and no
`--no-packages` flag, and package resource filters cannot disable subagents. A different
`PI_CODING_AGENT_DIR` is the only switch that turns the whole bundle off at once, including the six
agents.

Known behaviour worth remembering:

- Turning ECC off leaves `pi-subagents` in place, so the room still runs.
- Loose skills in `~/.agents/skills` (caveman, herdr, NYU, excalidraw) still load — that is a
  user-level skill directory, not a package, and pi offers no switch for it.
- The room keeps its own clone under `~/.pi-ecc-agent/git/…`; run `pi-ecc update` after pushing
  changes to pi-ecc.
- `pi-ecc` with ECC off is a hard error, not a silent re-enable.

Tests: `bash tools/pi-ecc.test.sh` — runs against a throwaway `HOME` and a stub `pi`, so it never
launches a session or touches real config.

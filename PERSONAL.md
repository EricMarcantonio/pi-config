# Personal extras (eric branch)

This branch adds my machine-specific setup on top of `main`. Rebase it onto `main` after changing
the base:

```bash
git switch main && git pull && git switch eric && git rebase main
```

What this branch adds:

- MCP servers `home-assistant`, `freecad`, `homedepot` and `blender` in `mcp.json`. They point at
  paths on my Mac.
- The full `EricMarcantonio/skills` package (woodbuild, freecad, homedepot and the rest), not
  filtered to clean-code.
- `@blazer2k/searxng-suite` and `pi-searxng-suite.json`, backed by my SearXNG via `SEARXNG_URL`.
- `extensions/herdr-agent-state.ts`, installed and managed by herdr.

The notes below are the original setup notes for those extras.

## Setup notes

- **Home Depot MCP**: `mcp.json` points at `mcp-servers/mcp_homedepot/dist/index.js`, which is a machine-local clone and is gitignored. To restore on a new machine:
  ```bash
  git clone https://github.com/sstepanovvl/mcp_homedepot.git ~/.pi/agent/mcp-servers/mcp_homedepot
  cd ~/.pi/agent/mcp-servers/mcp_homedepot && npm install && npm run build
  ```
  Pinned to upstream commit `8ef0178`. Its tools are `hd_search`, `hd_product`, `hd_store_availability`, `hd_stores`; `HD_DEFAULT_STORE=7011` is set in `mcp.json`.
- **Skills**: none are bundled here. The skills this config used to carry now live in a
  plugin marketplace, published as a pi package:
  [github.com/EricMarcantonio/skills](https://github.com/EricMarcantonio/skills). pi
  installs it from `settings.json`'s `packages` entry:

  ```bash
  pi install git:github.com/EricMarcantonio/skills
  ```

  The clone lands in `git/github.com/EricMarcantonio/skills/` (this directory is
  gitignored), and the skills load from `plugins/*/skills/`. Engine tests, run from the
  clone:

  ```bash
  python3 -m unittest discover \
    -s plugins/woodbuild/skills/woodbuild-engine/scripts/tests \
    -t plugins/woodbuild/skills/woodbuild-engine/scripts
  ```

  Because the entry is shared in `settings.json`, a colleague who clones this config
  gets the author's public plugin package cloned and loaded by pi on first start;
  `PI_OFFLINE=1` skips it.
- **Subagents**: [pi-subagents](https://github.com/nicobailon/pi-subagents) provides the
  `subagent` tool and the builtin agents `scout`, `researcher`, `evidence-auditor`,
  `worker`, `reviewer`, `oracle`, `delegate`. This config used to carry a local
  `extensions/subagent/` implementation with its own `chain` API; that is gone —
  pi-subagents removed legacy `chain`/`tasks`/`parallel` in favour of `workflowScript`
  (`runs.run` / `runs.all`), so the three `prompts/*.md` templates were rewritten.
  Only `agents/planner.md` remains local (no builtin equivalent); `scout`/`worker`/
  `reviewer` model pins now live in `settings.json` under `subagents.agentOverrides`
  so the upstream builtin prompts win. `subagents.modelScope` restricts subagents to
  `ollama/deepseek-v4.1-flash:cloud` alone (`enforce: true`, `strict: true`), so an
  out-of-scope model — including an inherited session model — is rejected before
  launch rather than silently used. Model scope is policy, not selection: it rejects,
  it does not pick a cheaper model. Superpowers ships no agent definitions of its
  own — its `Subagent (general-purpose):` templates map onto the `delegate` builtin.
  Tune with `/subagents-doctor`, `/subagents-guide`, `/subagents-fleet`, or JSON at
  `extensions/subagent/config.json` (present, holding `asyncByDefault`; note that
  `asyncByDefault` is a **config.json** key, not a `subagents.*` settings key).
- **Offline archive**: the packages installed from `settings.json` `packages` are
  mirrored to a private repo, `EricMarcantonio/pi-vendor-archive`
  (cloned at `~/pi-vendor-archive`), so a package vanishing upstream cannot make this
  config unrebuildable. A `pi-vendor` skill in
  [EricMarcantonio/skills](https://github.com/EricMarcantonio/skills) reports drift and
  refreshes it; the archive rebuilds itself
  without the skill via `restore.sh`. That repo has independent history and is **never
  merged into this one**. Not covered: the pi CLI
  itself, `~/blender_mcp`, `mcp_homedepot`, and `uvx freecad-mcp`.
- **Build workspaces**: a build's `spec.json`, price cache, `decisions.md` and
  `out/` live outside this repo in `~/Documents/woodbuild/<slug>/` (the convention
  `building-from-reference` owns). Not versioned.
- **Ollama models**: `models.json` points at `http://127.0.0.1:11434/v1` with `apiKey: "ollama"`. Change `baseUrl` if your Ollama isn't local. All model ids use the `:cloud` suffix.
- **Costs** are USD per 1M tokens, off-peak rates only (pi has no time-of-day pricing; Ollama peak, Mon–Fri 12–18 UTC, is ~2×).
- **Context windows** come from `ollama show <model>`.
- **Web tools**: `@blazer2k/searxng-suite` provides `web_search` and `web_extract`, backed by a local SearXNG instance. `SEARXNG_URL` is set to `http://localhost:8080` in `~/.zshrc` (Docker setup lives in `~/searxng`). Ollama is used only for reasoning; the former `@ollama/pi-web-search` package is intentionally not used.
- **Vision / image input**: pi only forwards image attachments to models whose `models.json` entry lists `"input": ["text", "image"]`. Without it the model silently receives text only. Verified by an image probe (prompt tokens 31 → 340 when an image is attached): image-capable are `deepseek-v4.1-flash:cloud` and `kimi-k3:cloud`; `deepseek-v4-flash:cloud` and `deepseek-v4-pro:cloud` reject images with HTTP 400. Regenerating `models.json` can drop the `input` field, so re-add it if attachments stop reaching the model.
- **MCP servers**: `mcp.json` configures MCP servers for pi's built-in MCP support (global scope, applies to all projects; no extension package needed). Five stdio servers: `home-assistant`, `freecad`, `homedepot`, `blender`, `playwright`. Servers connect at session start; a slow server's tools appear once it connects. `freecad` (`uvx freecad-mcp`) bridges to a running FreeCAD instance over its RPC socket (default port 9875); tools register as `mcp__freecad__*` (17: `create_document`, `create_object`, `edit_object`, `delete_object`, `execute_code`, `execute_code_async`, `execute_code_headless`, `get_async_status`, `get_view`, `insert_part_from_library`, `get_objects`, `get_object`, `get_parts_list`, `reload_document`, `list_documents`, `get_rpc_status`, `run_fem_analysis`); inspect with `/mcp` or `pi mcp list`.
  `homedepot` is reached by the engine through the
  `plugins/homedepot/skills/homedepot-catalogue/scripts/homedepot_adapter.py` inside
  the installed package clone (`--adapter`); without it the engine prices from the
  cache only and reports tax as zero.
  `blender` runs `uv --directory ~/blender_mcp/mcp run blender-mcp` against a
  machine-local clone (gitignored, not in this repo) and needs the Blender addon
  side running inside Blender:
  ```bash
  git clone https://projects.blender.org/lab/blender_mcp.git ~/blender_mcp
  ```
- **MCP config path**: pi reads the global MCP config from `<config dir>/mcp.json`, i.e. `PI_CODING_AGENT_DIR/mcp.json`, falling back to `~/.pi/agent/mcp.json`. Since this setup symlinks both `~/.cache/pi-ts/mcp.json` and `~/.pi/agent/mcp.json` into this repo, edit `~/pi-config/mcp.json` and it is picked up either way:
  ```bash
  ln -sfn ~/pi-config/mcp.json ~/.pi/agent/mcp.json
  ln -sfn ~/pi-config/mcp.json "$PI_CODING_AGENT_DIR/mcp.json"
  ```
  Restore them on any machine, or MCP servers silently do not load.
- **FreeCAD MCP install** (two halves — MCP server + in-FreeCAD addon):
  ```bash
  brew install uv                       # provides uvx; freecad-mcp is fetched on demand
  git clone --depth 1 https://github.com/neka-nat/freecad-mcp.git /tmp/fc-mcp-src
  mkdir -p ~/Library/Application\ Support/FreeCAD/v1-1/Mod
  cp -r /tmp/fc-mcp-src/addon/FreeCADMCP ~/Library/Application\ Support/FreeCAD/v1-1/Mod/
  ```
  Then restart FreeCAD. The RPC server also needs to be running: either pick the **MCP Addon** workbench and click **Start RPC Server**, or pre-seed auto-start by writing `~/Library/Application Support/FreeCAD/v1-1/freecad_mcp_settings.json`:
  ```json
  { "remote_enabled": false, "allowed_ips": "127.0.0.1", "auto_start_rpc": true }
  ```
  FreeCAD 1.1 user dir is `.../FreeCAD/v1-1/` (1.0 uses `v1-0/`). Launching FreeCAD via `open -a FreeCAD` right after adding the addon did not bring the RPC port up; launching the binary directly did, and later launches were fine. Verify with `nc -z 127.0.0.1 9875`.
- **No secrets** are stored here (`apiKey` is the literal `"ollama"`).
- **Wordy footer**: `extensions/wordy-footer.ts` replaces pi's symbol footer (`↑ ↓ R W CH`) with words (`input`, `output`, `cache-read`, `cache-hit`, `cost`, `context`). When subagents have run it splits cost into `chat` / `subagent` / `total` (child cost comes from the `subagent` tool result's `details.totalCost`, which already includes nested children); `context` is a bare percentage of the model window, with `/1M` window size omitted. Toggle at runtime with `/footer-words`; the choice is saved to `settings.json` as `"wordyFooter"`, so it syncs across machines. Delete the extension file to restore the default footer permanently.

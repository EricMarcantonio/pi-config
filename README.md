# pi-config

A developer setup for the [pi](https://github.com/earendil-works/pi-coding-agent) coding agent:
Ollama cloud models with pricing and context windows, a Claude Code-style experience, and a small
set of development skills.

This branch (`main`) is the shareable base. My own extras live on the `eric` branch, on top of this
one.

## What's in here

| path | what |
|---|---|
| `settings.json` | default model and provider, theme, packages |
| `models.json` | custom `ollama` provider: cloud models with `cost` (USD per 1M tokens) and `contextWindow` |
| `mcp.json` | MCP servers: `excalidraw` (diagram canvas), run from a Docker image built from its mirror |
| `services/` | Docker Compose services shared by every pi session: SearXNG and the excalidraw canvas |
| `extensions/wordy-footer.ts` | replaces the symbol footer with words |
| `caveman.json` | settings for the terse-reply package |
| `.github/` | weekly mirror-pin bump workflow and Dependabot config |

Packages installed from `settings.json`. Third-party packages come from mirrors in my `marcantonio-dev` org, pinned to a
commit (see [Mirrors](#mirrors)):

- [`pi-code`](https://github.com/EricMarcantonio/pi-code): the Claude Code experience. It reads
  your `.claude` config (rules, commands, skills, hooks, output styles, MCP, agents) and adds todo,
  checkpoints, memory, web search and subagents
- [`pi-claude-code`](https://github.com/earendil-works/pi-claude-code), mirrored as
  [`marcantonio-dev/pi-claude-code`](https://github.com/marcantonio-dev/pi-claude-code): a pi
  provider that runs on your Claude Code subscription
- [`ECC`](https://github.com/affaan-m/ECC), forked as
  [`marcantonio-dev/ECC`](https://github.com/marcantonio-dev/ECC) (Everything Claude Code): skills, commands, engineering
  rules and session hooks through its Pi adapter. Run `/ecc-doctor` to check it loaded
- [`pi-caveman`](https://github.com/jonjonrankin/pi-caveman), forked as
  [`marcantonio-dev/pi-caveman`](https://github.com/marcantonio-dev/pi-caveman): terse replies. Turn it off with
  `/caveman off`, or remove it from `packages`
- [`EricMarcantonio/skills`](https://github.com/EricMarcantonio/skills), filtered to the
  `clean-code` skill only
- [`agent-browser`](https://github.com/vercel-labs/agent-browser), mirrored as
  [`marcantonio-dev/agent-browser`](https://github.com/marcantonio-dev/agent-browser), and
  [`playwright-cli`](https://github.com/microsoft/playwright-cli), mirrored as
  [`marcantonio-dev/playwright-cli`](https://github.com/marcantonio-dev/playwright-cli): only their
  skills, which teach agents to drive a browser and look at frontend apps. The CLIs themselves
  come from npm (see [Browser tools](#browser-tools))

Not included, because pi regenerates them: `npm/`, `git/`, `bin/`, `auth.json`,
`models-store.json`, `sessions/`.

## Install

You need [pi](https://github.com/earendil-works/pi-coding-agent) and
[Ollama](https://ollama.com), signed in for `:cloud` models.

### Option A: use this repo as your config folder

```bash
git clone https://github.com/EricMarcantonio/pi-config ~/pi-config
echo 'export PI_CODING_AGENT_DIR=~/pi-config' >> ~/.zshrc   # or ~/.bashrc
```

Start pi. It installs the packages listed in `settings.json` on first start. Then set up the
[services](#services) and the [browser tools](#browser-tools).

### Option B: copy into your existing config

```bash
cp settings.json models.json mcp.json caveman.json ~/.pi/agent/
cp -r extensions services ~/.pi/agent/
```

Merge by hand instead if you already have your own `settings.json` or `mcp.json`.

## Services

`services/compose.yml` runs local services in Docker under one project, `pi-services`. The
container names are fixed, so every pi session shares the same containers. Everything listens on
`127.0.0.1` only. You need Docker running.

```bash
cd ~/.pi/agent   # or wherever this repo lives
docker compose -f services/compose.yml --profile build-only build   # excalidraw images, from the mirror
docker compose -f services/compose.yml up -d searxng excalidraw-canvas
```

- **SearXNG** (`pi-searxng`, http://127.0.0.1:8888) backs `web_search`. DuckDuckGo blocks scrapers,
  and a local SearXNG searches from this machine's own IP. `settings.json` points pi-code at it with
  `webSearch.searxngUrl`. If it isn't running, pi-code runs `webSearch.startCommand` in the background
  when a session loads or a search fails, so you rarely have to start it by hand. The image is pinned
  by digest; `services/searxng/settings.yml` turns on the JSON API.
- **Excalidraw canvas** (`pi-excalidraw-canvas`, http://127.0.0.1:3000) is the live canvas the
  `excalidraw` MCP server draws on. Both images are built from
  [`marcantonio-dev/mcp_excalidraw`](https://github.com/marcantonio-dev/mcp_excalidraw) at a pinned
  commit with its lockfile (`npm ci`). `mcp.json` runs the MCP server with `docker run --pull never`,
  so it only ever uses the local build. After a `Bump mirror pins` PR moves the commit, rebuild.

No web tool spends model tokens: `webFetch.prompt` is off, so `web_fetch` returns pages as
markdown, and search goes to SearXNG rather than a paid search API.

## Browser tools

The `agent-browser` and `playwright-cli` skills call CLIs that come from npm, not from the mirrors.
Mirroring the git repos doesn't protect a published npm package, so install exact versions that
match the pinned skills and have been out for at least a week:

```bash
npm install -g --before="$(date -v-7d +%F)" agent-browser@0.41.2 @playwright/cli@0.1.23
agent-browser install            # downloads Chrome for Testing
```

`--before` makes npm choose every dependency as it was a week ago. When a `Bump mirror pins` PR
moves either skill, bump these versions to the matching release. agent-browser's npm package
ships its native binaries, so npm's integrity check covers them. Recent npm skips its postinstall
(which would otherwise download the binary from GitHub) unless you allow it; it isn't needed.

## Notes

- **Models**: `models.json` points at `http://127.0.0.1:11434/v1` with `apiKey: "ollama"`. Change
  `baseUrl` if Ollama isn't local. Every model id uses the `:cloud` suffix.
- **Costs** are USD per 1M tokens at off-peak rates. pi has no time-of-day pricing; Ollama's peak
  (Mon–Fri 12–18 UTC) is about 2×.
- **Context windows** come from `ollama show <model>`.
- **Images**: pi only sends image attachments to models whose `models.json` entry lists
  `"input": ["text", "image"]`. Here that's `deepseek-v4.1-flash:cloud` and `kimi-k3:cloud`.
  Regenerating `models.json` can drop the field.
- **ECC** is large (hundreds of skills and commands). Its hooks can be tuned with
  `ECC_HOOK_PROFILE` and `ECC_DISABLED_HOOKS`; see its `.pi/README.md`.
- **Footer**: toggle the wordy footer with `/footer-words`; the choice is saved to
  `settings.json` as `wordyFooter`. Delete the extension to restore the default footer.
- **No secrets** are stored here.

## Mirrors

Third-party packages are a supply-chain risk, so they never load straight from upstream. They come
from forks in the [`marcantonio-dev`](https://github.com/marcantonio-dev) org, pinned to a full
commit SHA on each mirror's `vetted` branch.

[`mirror-control`](https://github.com/marcantonio-dev/mirror-control) syncs every mirror from
upstream each week. It never force-pushes, and it moves `vetted` only after a commit has waited a
week. `.github/workflows/bump-mirror-pins.yml` then calls mirror-control's shared `bump-pins`
workflow, which opens a `Bump mirror pins` PR here. It only fast-forwards pins and runs with this
repo's own token, so no third-party app is involved. Nothing changes until that PR is merged.
Dependabot keeps the pinned workflow reference current.

To add a package: fork it into the org (see the `mirror-control` README), then add it to
`settings.json` as `git:github.com/marcantonio-dev/<repo>@<full sha on vetted>`.

My own repos (`pi-code`, `skills`) aren't mirrored or pinned and load from their default branch.

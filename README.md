# pi-config

A developer setup for the [pi](https://github.com/earendil-works/pi-coding-agent) coding agent:
Ollama cloud models with pricing and context windows, subagents, planning prompts, a todo tool and a
readable footer.

This branch (`main`) is the shareable base. My own extras (home automation, FreeCAD, Blender, wood
building skills) live on the `eric` branch, on top of this one.

## What's in here

| path | what |
|---|---|
| `settings.json` | default model and provider, theme, subagent model pins, packages |
| `models.json` | custom `ollama` provider: cloud models with `cost` (USD per 1M tokens) and `contextWindow` |
| `mcp.json` | MCP servers: `playwright` (browser automation) and `excalidraw` (diagram canvas) |
| `agents/planner.md` | a read-only planning subagent |
| `prompts/` | `/implement`, `/scout-and-plan` and `/implement-and-review` |
| `extensions/todo.ts` | a todo list tool |
| `extensions/wordy-footer.ts` | replaces the symbol footer with words |
| `extensions/subagent/config.json` | runs subagents async by default |
| `caveman.json` | settings for the terse-reply package |

Packages installed from `settings.json`:

- [`pi-subagents`](https://github.com/nicobailon/pi-subagents): the `subagent` tool and builtin
  agents (`scout`, `worker`, `reviewer` and others)
- [`superpowers`](https://github.com/obra/superpowers): brainstorming, planning, TDD and review
  workflows
- [`pi-caveman`](https://www.npmjs.com/package/pi-caveman): terse replies. Turn it off with
  `/caveman off`, or remove it from `packages`
- [`EricMarcantonio/skills`](https://github.com/EricMarcantonio/skills), filtered to the
  `clean-code` skill only

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

Start pi. It installs the packages listed in `settings.json` on first start.

### Option B: copy into your existing config

```bash
cp settings.json models.json mcp.json caveman.json ~/.pi/agent/
cp -r agents prompts extensions ~/.pi/agent/
```

Merge by hand instead if you already have your own `settings.json` or `mcp.json`.

## Notes

- **Models**: `models.json` points at `http://127.0.0.1:11434/v1` with `apiKey: "ollama"`. Change
  `baseUrl` if Ollama isn't local. Every model id uses the `:cloud` suffix.
- **Costs** are USD per 1M tokens at off-peak rates. pi has no time-of-day pricing; Ollama's peak
  (Mon–Fri 12–18 UTC) is about 2×.
- **Context windows** come from `ollama show <model>`.
- **Images**: pi only sends image attachments to models whose `models.json` entry lists
  `"input": ["text", "image"]`. Here that's `deepseek-v4.1-flash:cloud` and `kimi-k3:cloud`.
  Regenerating `models.json` can drop the field.
- **Subagents**: `settings.json` pins `scout`, `worker` and `reviewer` to
  `deepseek-v4.1-flash:cloud` and restricts subagents to that model (`modelScope` with
  `enforce` and `strict`). An out-of-scope model is rejected before launch, not swapped. Tune with
  `/subagents-doctor` or `extensions/subagent/config.json`.
- **More skills**: to load other skills from the skills package, add their paths to the `skills`
  filter in `settings.json`. See that repo's README.
- **Footer**: toggle the wordy footer with `/footer-words`; the choice is saved to
  `settings.json` as `wordyFooter`. Delete the extension to restore the default footer.
- **No secrets** are stored here.

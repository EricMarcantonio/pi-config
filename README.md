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
| `mcp.json` | MCP servers: `playwright` (browser automation) and `excalidraw` (diagram canvas) |
| `extensions/wordy-footer.ts` | replaces the symbol footer with words |
| `caveman.json` | settings for the terse-reply package |

Packages installed from `settings.json`:

- [`pi-code`](https://github.com/EricMarcantonio/pi-code): the Claude Code experience. It reads
  your `.claude` config (rules, commands, skills, hooks, output styles, MCP, agents) and adds todo,
  checkpoints, memory, web search and subagents
- [`ECC`](https://github.com/affaan-m/ECC) (Everything Claude Code): skills, commands, engineering
  rules and session hooks through its Pi adapter. Run `/ecc-doctor` to check it loaded
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
cp -r extensions ~/.pi/agent/
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
- **ECC** is large (hundreds of skills and commands). Its hooks can be tuned with
  `ECC_HOOK_PROFILE` and `ECC_DISABLED_HOOKS`; see its `.pi/README.md`.
- **Footer**: toggle the wordy footer with `/footer-words`; the choice is saved to
  `settings.json` as `wordyFooter`. Delete the extension to restore the default footer.
- **No secrets** are stored here.

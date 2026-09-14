# Design: move the skills out of the shared config into a published plugin repo

Date: 2026-09-13
Status: approved (design), pending implementation plan

## Problem

`~/pi-config` is a public, shareable agent config (`PI_CODING_AGENT_DIR=/Users/eric/pi-config`)
that currently ships nine personal skills in `skills/`, including a Python wood-build
engine. Because `getSettingsPath()` resolves to `<agentDir>/settings.json`, any pi-side
reference to those skills has to live in the shared config: a `skills` array entry, a
symlink inside the repo, or a package install. Colleagues who clone the config therefore
either read the skills or fail on paths that do not exist on their machine.

The user also maintains `~/Documents/GitHub Projects/skills`
(`git@github.com:EricMarcantonio/skills.git`, public), a Claude Code plugin marketplace:
`plugins/<plugin>/.claude-plugin/plugin.json` plus `plugins/<plugin>/skills/<skill>/SKILL.md`,
indexed by `.claude-plugin/marketplace.json`, with the layout documented in `CLAUDE.md`.

## Goal

The nine skills live in the plugin marketplace repo, in that repo's own format. `~/pi-config`
contains no skills and no pointer to them in its file tree. The user installs the marketplace
repo as a pi package, which is what brings the skills back.

## Non-goals

- No symlink, no `skills` array entry, no vendored copy inside `pi-config`.
- No change to the skills' behaviour: the engine, the adapter seam, the boundary guard's
  guarantee and the 152-test suite all keep their semantics.
- No change to `mcp.json`, `agents/`, `extensions/`, `prompts/`, models or auth.
- `docs/superpowers/` stays in `pi-config`; it documents that repo's own history.
- No new skills, no skill merges or splits. The seven-skill split from
  `2026-09-13-skill-split-design.md` is the input, unchanged.

## Decisions

### D1 — Three plugins, grouped by dependency, not by name

| plugin | skills | why this group |
|---|---|---|
| `woodbuild` | `building-from-reference`, `wood-framing`, `sheet-and-board-nesting`, `build-pricing`, `freecad-model-to-spec`, `woodbuild-engine` | one self-contained capability: it owns the engine, and its members import the engine. `freecad-model-to-spec` belongs here, not with the other FreeCAD skills, because it produces build specs and depends on `woodbuild/from_model.py` |
| `freecad` | `freecad-model-hygiene`, `freecad-render-views` | pure FreeCAD authoring knowledge with no engine dependency, useful to anyone |
| `homedepot` | `homedepot-catalogue` | the only store-aware skill; it owns the only file that names a store |

A plugin is both the unit the marketplace installs and toggles, and the unit of internal
dependency, so those two must coincide. Nine skills, three plugins, no plugin depending on
another plugin's internals.

### D2 — The marketplace keeps its own format

Every addition follows `CLAUDE.md`'s six steps, so the repo stays a valid Claude Code
marketplace:

- `plugins/<plugin>/.claude-plugin/plugin.json` — `name`, `version`, `description`, `tags`, `author`
- `plugins/<plugin>/README.md`
- an entry per plugin in `.claude-plugin/marketplace.json` under `"plugins"`, with `source: "plugins/<plugin>"`
- a row per plugin in the repo `README.md` table

The existing four plugins are not renamed, reformatted or moved.

### D3 — `package.json` is the pi bridge

pi has no marketplace concept. Its nearest equivalent to "install from the marketplace" is a
package install, and pi reads skills from `pi.skills` globs or a conventional `skills/`
directory. The marketplace layout is neither, so the repo gains a `package.json`:

```json
{
  "name": "@ericmarcantonio/skills",
  "version": "1.0.0",
  "private": true,
  "keywords": ["pi-package"],
  "pi": { "skills": ["plugins/*/skills"] }
}
```

No dependencies, so pi's post-clone `npm install` is a no-op. Claude Code ignores the file.

### D4 — Install mechanics and where the clone lands

`pi install git:github.com/EricMarcantonio/skills` clones to
`<agentDir>/git/github.com/EricMarcantonio/skills`, i.e.
`~/pi-config/git/github.com/EricMarcantonio/skills`, which `pi-config/.gitignore` already
ignores (`git/`). The install writes one `packages` entry into `~/pi-config/settings.json`.

**This entry is shared** — accepted: the plugins are public on GitHub, and the user wants a
colleague who clones the config to be able to get them the same way. The consequence is
recorded rather than hidden: cloning the shared config auto-installs the author's plugins
into the colleague's agent.

### D5 — Prose refers to the skills repo, not to a machine path

Skill and README text uses `<skills-repo>` as the placeholder:

```
<skills-repo>/plugins/woodbuild/skills/woodbuild-engine/scripts/woodbuild.py
```

`pi-config/README.md` and the engine skill spell out the concrete resolution
(`~/pi-config/git/github.com/EricMarcantonio/skills/…` after a git install, or the working
copy under `~/Documents/GitHub Projects/skills/` when developing the plugins).

### D6 — The guard moves with the tree and learns the new root

`tests/test_boundaries.py` currently resolves its scan root as `parents[4] / "skills"`. In
the new tree the equivalent root is `plugins/*/skills`, so the guard:

- scans every `plugins/*/skills/**/*.py` and `*.md` for the store's identity tokens,
  exempting the owner plugin (`homedepot`) and the same two seam test files;
- keeps the tax-table check pointed at the engine package;
- keeps the frontmatter, hidden-skill and "the split's owned skills name the engine" checks,
  with `ENGINE_USERS` listing the six visible skills of the `woodbuild` plugin;
- adds the two pre-existing-FreCAD-skills exemption test unchanged in intent.
- Its canonical command becomes
  `python3 -m unittest discover -s plugins/woodbuild/skills/woodbuild-engine/scripts/tests -t plugins/woodbuild/skills/woodbuild-engine/scripts`.

### D7 — Order of operations, and the one window with no skills

1. Move the nine skill directories into the three plugin trees; add plugin metadata, the repo
   `package.json`, marketplace entries and README rows.
2. Rework the guard, the `<skills-repo>` prose and the documented test command inside the
   moved tree; the suite must be green at 152 tests, run from the new path.
3. Commit and push the plugin repo; merge there.
4. On a branch in `pi-config`: delete `skills/`, update its README. Do not merge yet.
5. `pi install git:github.com/EricMarcantonio/skills`; verify the clone path is gitignored,
   `settings.json` has exactly one new entry, and a fresh pi session lists all nine skills.
6. Merge the `pi-config` branch only after step 5 verifies. Rollback if it does not: the
   branch keeps `skills/`, and nothing is lost.

Between steps 4 and 5 the live pi has no skills. The plugin repo's history is the only source
until step 5 succeeds, which is why step 6 waits.

### D8 — Two repo hygiene items found during recon

- The plugin repo has no `.gitignore`; 5 `.idea/` files are untracked. Add a `.gitignore`
  with `.idea/` only.
- 24 untracked files sit under `plugins/clean-code/skills/clean-code-workspace/` (eval
  benchmark and grading output). They are the user's own scratch data, are not touched, and
  are not part of this design — recorded only because they live inside the `plugins/*/skills`
  glob root that pi will scan.

## Interfaces

- **Repo → pi:** `package.json` `pi.skills` = `["plugins/*/skills"]`; no other manifest.
- **Skill → engine:** `<skills-repo>/plugins/woodbuild/skills/woodbuild-engine/scripts/…`;
  the engine imports no skill.
- **Skill → store:** `<skills-repo>/plugins/homedepot/skills/homedepot-catalogue/scripts/homedepot_adapter.py`,
  passed to the engine CLI as `--adapter`.
- **pi-config file tree:** no `skills/`, no path to the plugin repo; `settings.json` gains one
  `packages` entry after step 5.
- Unchanged: cache schema, `mcp.json`, agent dir layout, the engine's stdlib-only rule.

## Testing

- Engine suite, run from the moved path: 152 tests, `OK (skipped=9)`.
- The reworked boundary guard is the check that the split survived the move: no store identity
  token outside the `homedepot` plugin, no tax table in the engine, valid frontmatter, one
  hidden skill.
- A hand check after step 5: a fresh pi session's skill list contains all nine names, and
  `/skill:woodbuild-engine` loads.
- A negative check for the sharing claim: `git ls-files` in `pi-config` contains no skill file
  and no reference to the plugin repo other than the intended `settings.json` package entry.

## Risks

- **The install is the only source after step 4.** Mitigated by the untaken step 6 merge and by
  pushing the plugin repo before deleting anything.
- **A shared package entry auto-installs the author's plugins for anyone cloning the config.**
  Accepted deliberately (D4); it is the price of the user's own install working from the same
  file, and it is visible in `settings.json` rather than implicit.
- **Cross-plugin path coupling.** `homedepot-catalogue` and the engine live in different
  plugins; if someone installs `woodbuild` without `homedepot`, `build-pricing` still works
  (the adapter is optional) and only live price lookups are unavailable. The dependency is
  documented in both skills.
- **Claude Code compatibility.** New plugins appear in that marketplace too. Nothing added is
  Claude-specific beyond the format the repo already uses; the Python is inert there.
- **Path churn.** Every documented command and the guard's scan root change once. D5 keeps the
  prose machine-independent so this does not recur.

# Skills Repo Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the nine skills out of `~/pi-config` into the public plugin marketplace at `~/Documents/GitHub Projects/skills`, publish it as a pi package, and delete the skills from the shared config.

**Architecture:** The marketplace repo keeps its Claude Code plugin format exactly (`plugins/<plugin>/.claude-plugin/plugin.json` + `plugins/<plugin>/skills/<skill>/SKILL.md`, indexed by `.claude-plugin/marketplace.json`, documented by `CLAUDE.md`). A new repo-root `package.json` declares `{"pi":{"skills":["plugins/*/skills"]}}`, which is how pi installs skills from a repo whose layout is not a bare `skills/` directory. The user then runs `pi install git:github.com/EricMarcantonio/skills`; the clone lands in `<agentDir>/git/…` (already gitignored by `pi-config/.gitignore`) and one `packages` entry appears in `settings.json`. `~/pi-config` ends with no `skills/` directory and no pointer to the plugin repo in its file tree.

**Tech Stack:** Python 3 standard library (engine unchanged), JSON manifests, git; pi's package/skill loader; `unittest`.

**Spec:** `docs/superpowers/specs/2026-09-13-skills-repo-migration-design.md`

## Global Constraints

- **Two repos, two branches.** Plugin work happens in `~/Documents/GitHub Projects/skills` on branch `woodbuild-plugins`; config work happens in `~/pi-config` on branch `drop-skills`. Neither merges to `main` until Task 8 verifies the install.
- **No behaviour change.** The engine, the adapter seam, the cache schema, the boundary guard's guarantee and every skill's instructions keep their current semantics. Only paths, packaging and registration change.
- **Stdlib only**; no new dependencies in either repo.
- **Store knowledge only under the `homedepot` plugin.** The guard enforces it; `homedepot-catalogue` keeps the identity tokens, the bare slug stays allowed everywhere.
- **Prose uses `<skills-repo>`**, never a machine-absolute path: `<skills-repo>/plugins/woodbuild/skills/woodbuild-engine/scripts`.
- **Suite count:** 152 tests today; Task 4 adds one guard test → **153 tests, `OK (skipped=9)`**. From Task 4 on, the canonical command is
  `python3 -m unittest discover -s plugins/woodbuild/skills/woodbuild-engine/scripts/tests -t plugins/woodbuild/skills/woodbuild-engine/scripts`
  run from the plugin repo root.
- **No symlink, no `skills` array entry, no vendored copy in `pi-config`.** The only trace after Task 7 is the `packages` entry that `pi install` writes in Task 8.
- **Commit style:** same as both repos already use — `skills: …`, `docs: …`, `chore: …`.
- **The one window with no skills** is between Task 7's commit and Task 8's successful install. Task 8 must verify before Task 7's branch merges.

## File Structure

### Plugin repo (`~/Documents/GitHub Projects/skills`, branch `woodbuild-plugins`)

```
package.json                                    # create (Task 3)
.gitignore                                      # create (Task 3)
README.md                                       # modify: +3 plugin rows, +1 missing row (Task 3)
.claude-plugin/marketplace.json                 # modify: +3 entries, +2 housekeeping (Task 3)
plugins/
├── woodbuild/                                  # create (Task 1)
│   ├── .claude-plugin/plugin.json
│   ├── README.md
│   └── skills/          ← git mv from pi-config/skills:
│       ├── building-from-reference/            # incl. reference/substitutions.md
│       ├── wood-framing/                       # incl. framing-rules.md
│       ├── sheet-and-board-nesting/
│       ├── build-pricing/
│       ├── freecad-model-to-spec/
│       └── woodbuild-engine/                    # SKILL.md + scripts/{woodbuild.py,woodbuild/*,tests/}
├── freecad/                                    # create (Task 2)
│   ├── .claude-plugin/plugin.json
│   ├── README.md
│   └── skills/{freecad-model-hygiene,freecad-render-views}/
└── homedepot/                                  # create (Task 2)
    ├── .claude-plugin/plugin.json
    ├── README.md
    └── skills/homedepot-catalogue/             # SKILL.md, stock-availability.md,
                                                # substitutions-hd.md, scripts/homedepot_adapter.py
```

### Config repo (`~/pi-config`, branch `drop-skills`)

```
skills/                                         # deleted entirely (Task 7)
README.md                                       # rewrite of the Skills section (Task 7)
settings.json                                   # untouched by hand; pi install writes it (Task 8)
docs/superpowers/                               # unchanged; keeps this spec and plan
```

---

### Task 1: Move `woodbuild`'s six skills into a plugin

**Files:**
- Create: `plugins/woodbuild/.claude-plugin/plugin.json`, `plugins/woodbuild/README.md`
- Move: six skill dirs from `~/pi-config/skills/` into `plugins/woodbuild/skills/`

**Interfaces:**
- Consumes: nothing.
- Produces: `plugins/woodbuild/skills/<skill>/` for `building-from-reference`, `wood-framing`, `sheet-and-board-nesting`, `build-pricing`, `freecad-model-to-spec`, `woodbuild-engine`. Later tasks edit those paths; Task 4's guard scans them.

- [ ] **Step 1: Branch the plugin repo**

```bash
cd "/Users/eric/Documents/GitHub Projects/skills"
git status --porcelain -uall | head        # note the untracked .idea/ and clean-code scratch; leave them
git checkout -b woodbuild-plugins
```

Expected: on a new branch from `f08b9ef`. The untracked files stay untracked; do not add or delete them.

- [ ] **Step 2: Move the six skill directories**

`git mv` cannot cross repositories, so move with the shell and let git notice the additions, or copy-then-delete in one commit. Use `cp -R` then `git add` (the pi-config side is deleted by Task 7, and this repo has no prior history of these files to preserve):

```bash
cd "/Users/eric/Documents/GitHub Projects/skills"
mkdir -p plugins/woodbuild/skills
for s in building-from-reference wood-framing sheet-and-board-nesting build-pricing \
         freecad-model-to-spec woodbuild-engine; do
  cp -R "/Users/eric/pi-config/skills/$s" "plugins/woodbuild/skills/$s"
done
find plugins/woodbuild -name '__pycache__' -prune -exec rm -rf {} +   # never commit caches
find plugins/woodbuild -type f | wc -l
```

Expected: the six dirs copied; the count matches `find /Users/eric/pi-config/skills -type f -not -path '*__pycache__*' | wc -l` for those six (the three freecad/homedepot skills are copied in Task 2, so compare per-skill if you want exactness).

- [ ] **Step 3: Write the plugin manifest**

Create `plugins/woodbuild/.claude-plugin/plugin.json` (matches the existing plugins' shape):

```json
{
  "name": "woodbuild",
  "version": "1.0.0",
  "description": "Turns a reference structure into a buildable wood version: build spec, framing, cutlist, nesting, bill of materials and a priced workbook",
  "tags": ["woodworking", "framing", "cutlist", "bill-of-materials", "freecad", "estimation"],
  "author": {
    "name": "Eric Marcantonio",
    "url": "https://github.com/EricMarcantonio"
  }
}
```

- [ ] **Step 4: Write the plugin README**

Create `plugins/woodbuild/README.md`, in the style of `plugins/car-manual-specs/README.md`:

```markdown
# woodbuild

Turns a reference structure — a product page, a photo, a drawing or a FreeCAD model —
into a buildable wood version with a cutlist, an optimised buy plan and a priced
deviations table.

## Overview

Seven steps, each owned by one skill: intake and invariants, reference-to-wood
translation, the build spec, framing derivation, sheet and board nesting, the bill of
materials, and product matching and pricing. The engine (`woodbuild-engine`) is
stdlib-only Python and ships inside this plugin; a test enforces that the skills stay
single-purpose and that no store name escapes the store plugin.

## Skills

| Skill | Job |
|-------|-----|
| `building-from-reference` | Orchestration: intake, invariants, translation, spec, verification |
| `wood-framing` | Studs, plates, corners, headers, rafters, blocking, panelisation |
| `sheet-and-board-nesting` | Kerf, offcuts, grain locking, sheet and board choice |
| `build-pricing` | The store-agnostic pricing method: judge, verify, provenance, honest `unpriced` |
| `freecad-model-to-spec` | Generic FreeCAD ingestion: envelope, openings, drift checks |
| `woodbuild-engine` | The engine itself (hidden from the model prompt) |

## Installation

```
/plugin install EricMarcantonio/skills/plugins/woodbuild
```

For pi, install the whole repo as a package (it declares `pi.skills` in `package.json`):

```
pi install git:github.com/EricMarcantonio/skills
```

## Running the engine's tests

From the repository root:

```
python3 -m unittest discover \
  -s plugins/woodbuild/skills/woodbuild-engine/scripts/tests \
  -t plugins/woodbuild/skills/woodbuild-engine/scripts
```
```

- [ ] **Step 5: Verify the move preserved everything**

```bash
cd "/Users/eric/Documents/GitHub Projects/skills"
diff -r "/Users/eric/pi-config/skills/woodbuild-engine" plugins/woodbuild/skills/woodbuild-engine -x __pycache__
for s in building-from-reference wood-framing sheet-and-board-nesting build-pricing freecad-model-to-spec; do
  diff -r "/Users/eric/pi-config/skills/$s" "plugins/woodbuild/skills/$s" -x __pycache__ && echo "ok $s"
done
```

Expected: no output from `diff` (identical trees), one `ok` line per skill.

- [ ] **Step 6: Commit**

```bash
cd "/Users/eric/Documents/GitHub Projects/skills"
git add plugins/woodbuild
git commit -m "plugins: add woodbuild with its six skills"
```

---

### Task 2: Add the `freecad` and `homedepot` plugins

**Files:**
- Create: `plugins/freecad/.claude-plugin/plugin.json`, `plugins/freecad/README.md`
- Create: `plugins/homedepot/.claude-plugin/plugin.json`, `plugins/homedepot/README.md`
- Move: `freecad-model-hygiene`, `freecad-render-views` → `plugins/freecad/skills/`; `homedepot-catalogue` → `plugins/homedepot/skills/`

**Interfaces:**
- Consumes: Task 1's layout convention.
- Produces: `plugins/freecad/skills/<skill>/`, `plugins/homedepot/skills/homedepot-catalogue/` (including `scripts/homedepot_adapter.py`, which Task 4's guard and every engine call site reference).

- [ ] **Step 1: Copy the three skills**

```bash
cd "/Users/eric/Documents/GitHub Projects/skills"
mkdir -p plugins/freecad/skills plugins/homedepot/skills
for s in freecad-model-hygiene freecad-render-views; do
  cp -R "/Users/eric/pi-config/skills/$s" "plugins/freecad/skills/$s"
done
cp -R "/Users/eric/pi-config/skills/homedepot-catalogue" plugins/homedepot/skills/homedepot-catalogue
find plugins/freecad plugins/homedepot -name '__pycache__' -prune -exec rm -rf {} +
diff -r "/Users/eric/pi-config/skills/homedepot-catalogue" \
        plugins/homedepot/skills/homedepot-catalogue -x __pycache__ && echo "ok homedepot"
```

Expected: `ok homedepot`; no `diff` output for the freecad pair either (check both).

- [ ] **Step 2: Write both plugin manifests**

`plugins/freecad/.claude-plugin/plugin.json`:

```json
{
  "name": "freecad",
  "version": "1.0.0",
  "description": "FreeCAD authoring hygiene and reliable view capture: disjoint-part modelling, silent boolean failures, the DAG-root overlap audit, and the 1.1 view API limits",
  "tags": ["freecad", "cad", "3d-modelling", "rendering", "screenshots"],
  "author": {
    "name": "Eric Marcantonio",
    "url": "https://github.com/EricMarcantonio"
  }
}
```

`plugins/homedepot/.claude-plugin/plugin.json`:

```json
{
  "name": "homedepot",
  "version": "1.0.0",
  "description": "Home Depot Canada sourcing and pricing for the woodbuild engine: store adapter, per-store SKUs and availability traps",
  "tags": ["home-depot", "pricing", "sourcing", "woodworking"],
  "author": {
    "name": "Eric Marcantonio",
    "url": "https://github.com/EricMarcantonio"
  }
}
```

- [ ] **Step 3: Write both plugin READMEs**

`plugins/freecad/README.md`:

```markdown
# freecad

Two skills for authoring and inspecting FreeCAD documents without the traps.

## Skills

| Skill | Job |
|-------|-----|
| `freecad-model-hygiene` | Disjoint-part modelling, the silent boolean failures, and the DAG-root overlap audit |
| `freecad-render-views` | FreeCAD 1.1 view API limits: per-document ActiveView, read-only viewPosition, late or stale captures, TechDraw pages breaking the MCP screenshot path |

## Installation

```
/plugin install EricMarcantonio/skills/plugins/freecad
```

Neither skill needs the woodbuild engine.
```

`plugins/homedepot/README.md`:

```markdown
# homedepot

Home Depot Canada sourcing and pricing for the woodbuild engine.

## Skills

| Skill | Job |
|-------|-----|
| `homedepot-catalogue` | The store adapter the engine takes via `--adapter`, the store id and provincial tax table, availability traps, and the search terms that actually work |

## Installation

```
/plugin install EricMarcantonio/skills/plugins/homedepot
```

Use it with the `woodbuild` plugin. Without this plugin the engine still runs: prices
come from the cache only and tax reports as 0.0.
```

- [ ] **Step 4: Commit**

```bash
cd "/Users/eric/Documents/GitHub Projects/skills"
git add plugins/freecad plugins/homedepot
git commit -m "plugins: add freecad and homedepot"
git status --porcelain -uall | grep -v '^??' | head
```

Expected: nothing modified and unstaged.

---

### Task 3: Register the plugins and give pi its manifest

**Files:**
- Create: `package.json`, `.gitignore`
- Modify: `.claude-plugin/marketplace.json`, `README.md`

**Interfaces:**
- Consumes: the three plugin dirs from Tasks 1-2.
- Produces: `package.json`'s `pi.skills = ["plugins/*/skills"]` — the contract Task 8's `pi install` depends on.

- [ ] **Step 1: Create `package.json`**

```json
{
  "name": "@ericmarcantonio/skills",
  "version": "1.0.0",
  "private": true,
  "description": "Claude Code plugins and pi skills by Eric Marcantonio",
  "keywords": ["pi-package", "claude-code-plugins"],
  "license": "MIT",
  "pi": {
    "skills": ["plugins/*/skills"]
  }
}
```

No `dependencies`, so pi's post-clone `npm install` is a no-op.

- [ ] **Step 2: Create `.gitignore`**

```gitignore
.idea/
node_modules/
```

The 24 untracked files under `plugins/clean-code/skills/clean-code-workspace/` are the
repo owner's eval output and are deliberately **not** ignored or touched.

- [ ] **Step 3: Register the new plugins in the marketplace index**

Add three entries to the `"plugins"` array in `.claude-plugin/marketplace.json`, in the
existing field order:

```json
    {
      "name": "woodbuild",
      "version": "1.0.0",
      "description": "Turns a reference structure into a buildable wood version: build spec, framing, cutlist, nesting, bill of materials and a priced workbook",
      "tags": ["woodworking", "framing", "cutlist", "bill-of-materials", "freecad", "estimation"],
      "author": {
        "name": "Eric Marcantonio",
        "url": "https://github.com/EricMarcantonio"
      },
      "source": "plugins/woodbuild"
    },
    {
      "name": "freecad",
      "version": "1.0.0",
      "description": "FreeCAD authoring hygiene and reliable view capture",
      "tags": ["freecad", "cad", "3d-modelling", "rendering"],
      "author": {
        "name": "Eric Marcantonio",
        "url": "https://github.com/EricMarcantonio"
      },
      "source": "plugins/freecad"
    },
    {
      "name": "homedepot",
      "version": "1.0.0",
      "description": "Home Depot Canada sourcing and pricing for the woodbuild engine",
      "tags": ["home-depot", "pricing", "sourcing", "woodworking"],
      "author": {
        "name": "Eric Marcantonio",
        "url": "https://github.com/EricMarcantonio"
      },
      "source": "plugins/homedepot"
    }
```

- [ ] **Step 4: Fix the index's existing drift**

Recon found the index lists only `clean-code` and `marketplace-listing` while four plugin
dirs exist, and `README.md` lists three. Register the two missing ones so the marketplace
matches the repo — `create-presentation` (dir exists, listed in README) and
`car-manual-specs` (dir exists, listed nowhere):

```bash
cd "/Users/eric/Documents/GitHub Projects/skills"
python3 - <<'PY'
import json, pathlib
p = pathlib.Path(".claude-plugin/marketplace.json")
d = json.loads(p.read_text())
have = {e["name"] for e in d["plugins"]}
add = [("car-manual-specs", "Extracts and saves key maintenance and torque specs from any car service manual PDF",
        ["car", "service-manual", "torque-specs", "pdf"]),
       ("create-presentation", "Builds animated, narrated video presentations with Remotion and Kokoro TTS",
        ["presentation", "video", "remotion", "tts"])]
for name, desc, tags in add:
    if name not in have:
        d["plugins"].append({"name": name, "version": "1.0.0", "description": desc,
                             "tags": tags,
                             "author": {"name": "Eric Marcantonio",
                                        "url": "https://github.com/EricMarcantonio"},
                             "source": "plugins/%s" % name})
p.write_text(json.dumps(d, indent=2) + "\n")
print([e["name"] for e in d["plugins"]])
PY
```

Expected: the printed name list contains all seven plugins (`clean-code`,
`marketplace-listing`, `create-presentation`, `car-manual-specs`, plus the three new ones).
Any that were already present are left alone, so the script is safe to re-run.

- [ ] **Step 5: Add the README table rows**

In the `## Available Plugins` table in `README.md`, append four rows — the three new plugins
plus the missing `car-manual-specs` — matching the existing row format exactly:

```markdown
| [woodbuild](plugins/woodbuild/) | Turns a reference structure into a buildable wood version: spec, framing, cutlist, nesting, BOM and a priced workbook | `/plugin install EricMarcantonio/skills/plugins/woodbuild` |
| [freecad](plugins/freecad/) | FreeCAD authoring hygiene and reliable view capture | `/plugin install EricMarcantonio/skills/plugins/freecad` |
| [homedepot](plugins/homedepot/) | Home Depot Canada sourcing and pricing for the woodbuild engine | `/plugin install EricMarcantonio/skills/plugins/homedepot` |
| [car-manual-specs](plugins/car-manual-specs/) | Extracts maintenance and torque specs from car service manual PDFs | `/plugin install EricMarcantonio/skills/plugins/car-manual-specs` |
```

Also add one line to the `## Installation` section noting the pi path:

```markdown
For pi, install the whole repository as a package — it declares its skills in
`package.json`:

```
pi install git:github.com/EricMarcantonio/skills
```
```

- [ ] **Step 6: Verify the manifests are valid and complete**

```bash
cd "/Users/eric/Documents/GitHub Projects/skills"
python3 - <<'PY'
import json, pathlib
m = json.loads(pathlib.Path(".claude-plugin/marketplace.json").read_text())
pkg = json.loads(pathlib.Path("package.json").read_text())
names = {e["name"] for e in m["plugins"]}
dirs = {p.name for p in pathlib.Path("plugins").iterdir() if p.is_dir()}
assert names == dirs, (sorted(names), sorted(dirs))
assert pkg["pi"]["skills"] == ["plugins/*/skills"]
assert "pi-package" in pkg["keywords"]
for e in m["plugins"]:
    assert pathlib.Path(e["source"], ".claude-plugin", "plugin.json").exists(), e["name"]
print("marketplace and package manifests agree with plugins/", sorted(names))
PY
```

Expected: one line listing all seven plugin names, no assertion error.

- [ ] **Step 7: Commit**

```bash
cd "/Users/eric/Documents/GitHub Projects/skills"
git add package.json .gitignore .claude-plugin/marketplace.json README.md
git commit -m "repo: declare pi skills, register every plugin, ignore .idea"
```

---

### Task 4: Rework the boundary guard for the plugin tree

**Files:**
- Modify: `plugins/woodbuild/skills/woodbuild-engine/scripts/tests/test_boundaries.py`

**Interfaces:**
- Consumes: the plugin layout from Tasks 1-3 (`plugins/<plugin>/skills/<skill>/…`).
- Produces: the canonical suite command that Tasks 5, 7 and 8 document and run:
  `python3 -m unittest discover -s plugins/woodbuild/skills/woodbuild-engine/scripts/tests -t plugins/woodbuild/skills/woodbuild-engine/scripts`

- [ ] **Step 1: Run the suite to see the guard fail on the new root**

```bash
cd "/Users/eric/Documents/GitHub Projects/skills"
python3 -m unittest discover \
  -s plugins/woodbuild/skills/woodbuild-engine/scripts/tests \
  -t plugins/woodbuild/skills/woodbuild-engine/scripts 2>&1 | tail -8
```

Expected: failures from `test_boundaries.py`. Its old `SKILLS = parents[4] / "skills"`
resolves to `plugins/woodbuild/skills` — which *exists*, so the guard silently narrows to
one plugin instead of failing loudly. Concretely: `test_the_store_adapter_is_loadable_and_offline_safe`
fails on a missing `homedepot-catalogue` path, and the store scan no longer covers
`freecad` or `homedepot` at all. Every other test file passes, because they only use
`woodbuild`. That silent narrowing is why this task exists.

- [ ] **Step 2: Replace the guard's root and path lookups**

In `plugins/woodbuild/skills/woodbuild-engine/scripts/tests/test_boundaries.py`, replace
the header constants and `skill_dirs()`:

```python
# This file lives at plugins/woodbuild/skills/woodbuild-engine/scripts/tests/, so
# parents[5] is already the plugins directory. The guard scans the whole plugins tree: a
# store name is a regression anywhere outside the homedepot plugin, and every plugin's
# skill dirs must be well formed.
PLUGINS = pathlib.Path(__file__).resolve().parents[5]
STORE_WORDS = ("Home Depot", "homedepot.ca", "homedepot.com", "hd_search",
               "hd_product", "HD_DEFAULT_STORE", "MicroPro")
# The plugin that owns the store's knowledge. The bare skill slug is allowed anywhere;
# the store's own names are not.
STORE_OWNER = "homedepot"
# The six visible skills of the woodbuild plugin. Every one of them must name the engine
# it uses. The freecad plugin's skills use no engine; they are only scanned for store
# knowledge.
ENGINE_USERS = {"building-from-reference", "wood-framing", "sheet-and-board-nesting",
                "build-pricing", "freecad-model-to-spec"}
# The two files whose job is to name the store in order to check the seam.
STORE_NAMING_ALLOWED = {"test_boundaries.py", "test_adapters.py"}
EXPECTED_PLUGINS = {"woodbuild", "freecad", "homedepot"}
ENGINE_SKILL = PLUGINS / "woodbuild" / "skills" / "woodbuild-engine"


def skill_dirs():
    return sorted(p for p in PLUGINS.glob("*/skills/*/SKILL.md"))


def plugin_dirs():
    return {p.name for p in PLUGINS.iterdir() if p.is_dir()}
```

Note `homedepot-catalogue` left `ENGINE_USERS`: it names the engine, but it lives in the
`homedepot` plugin, and the engine-usage rule is about the woodbuild plugin's own skills.
Task 5 still fixes its paths.

- [ ] **Step 3: Update the four store/tax tests**

```python
    def test_the_three_plugins_exist(self):
        missing = EXPECTED_PLUGINS - plugin_dirs()
        self.assertEqual(missing, set(), "missing plugin directories: %s" % sorted(missing))

    def test_no_other_plugin_or_engine_file_names_the_store(self):
        offenders = []
        for path in PLUGINS.rglob("*"):
            if not path.is_file() or path.suffix not in (".py", ".md"):
                continue
            if STORE_OWNER in path.parts or path.name in STORE_NAMING_ALLOWED:
                continue
            text = path.read_text(errors="ignore")
            for word in STORE_WORDS:
                if word in text:
                    offenders.append("%s contains %r" % (path, word))
        self.assertEqual(offenders, [], "store knowledge escaped its plugin")

    def test_only_the_two_seam_tests_are_exempt(self):
        exempt = sorted(p.name for p in PLUGINS.rglob("*") if p.name in STORE_NAMING_ALLOWED)
        self.assertEqual(exempt, ["test_adapters.py", "test_boundaries.py"])

    def test_the_engine_has_no_tax_numbers(self):
        offenders = []
        for path in (ENGINE_SKILL / "scripts" / "woodbuild").rglob("*.py"):
            text = path.read_text(errors="ignore")
            if "TAX_RATES" in text or "tax_rate_for" in text:
                offenders.append(str(path))
        self.assertEqual(offenders, [], "the engine must not carry a tax table")

    def test_the_store_adapter_is_loadable_and_offline_safe(self):
        path = (PLUGINS / STORE_OWNER / "skills" / "homedepot-catalogue"
                / "scripts" / "homedepot_adapter.py")
        adapter = load_adapter(str(path))
        self.assertFalse(adapter.is_candidate(adapter.source_product))
        self.assertGreater(adapter.tax_rate("ON"), 0.0)
```

- [ ] **Step 4: Update the shape tests**

```python
    def test_every_skill_this_split_owns_points_at_the_engine(self):
        for name in sorted(ENGINE_USERS):
            path = PLUGINS / "woodbuild" / "skills" / name / "SKILL.md"
            with self.subTest(skill=name):
                self.assertTrue(path.exists(), "missing skill %s" % name)
                self.assertIn("woodbuild-engine", path.read_text(),
                              "%s does not name the engine it depends on" % path)

    def test_the_unrelated_freecad_skills_are_left_out_of_the_engine_rule(self):
        for name in ("freecad-model-hygiene", "freecad-render-views"):
            path = PLUGINS / "freecad" / "skills" / name / "SKILL.md"
            self.assertTrue(path.exists())
            self.assertNotIn(name, ENGINE_USERS)
```

`test_every_skill_declares_its_own_name_and_a_usable_description` and
`test_only_the_engine_is_hidden` use `skill_dirs()` and need no change beyond the new
function body.

- [ ] **Step 5: Run the suite from the plugin repo root**

```bash
cd "/Users/eric/Documents/GitHub Projects/skills"
python3 -m unittest discover \
  -s plugins/woodbuild/skills/woodbuild-engine/scripts/tests \
  -t plugins/woodbuild/skills/woodbuild-engine/scripts 2>&1 | grep -E "^(Ran|OK|FAILED)"
```

Expected: `Ran 153 tests`, `OK (skipped=9)`.

- [ ] **Step 6: Prove the guard still bites**

```bash
cd "/Users/eric/Documents/GitHub Projects/skills"
printf '\nA sentence about Home Depot in the wrong place.\n' >> plugins/woodbuild/skills/wood-framing/SKILL.md
python3 -m unittest discover -s plugins/woodbuild/skills/woodbuild-engine/scripts/tests \
  -t plugins/woodbuild/skills/woodbuild-engine/scripts 2>&1 | grep -E "^(FAILED|OK)|contains" | head -3
git checkout -- plugins/woodbuild/skills/wood-framing/SKILL.md
```

Expected: a failure naming `wood-framing/SKILL.md` and the token, then the file restored.
If it passes, the guard is broken — stop and fix the guard, not the prose.

- [ ] **Step 7: Commit**

```bash
cd "/Users/eric/Documents/GitHub Projects/skills"
git add plugins/woodbuild/skills/woodbuild-engine/scripts/tests/test_boundaries.py
git commit -m "guard: scan the plugin tree"
```

---

### Task 5: Point every path at the plugin repo

**Files:**
- Modify: `plugins/woodbuild/skills/woodbuild-engine/SKILL.md`
- Modify: `plugins/woodbuild/skills/building-from-reference/SKILL.md`
- Modify: `plugins/woodbuild/skills/wood-framing/SKILL.md`
- Modify: `plugins/woodbuild/skills/build-pricing/SKILL.md`
- Modify: `plugins/homedepot/skills/homedepot-catalogue/SKILL.md`
- Modify: `plugins/homedepot/skills/homedepot-catalogue/scripts/homedepot_adapter.py`
- Modify: `plugins/freecad/skills/freecad-model-hygiene/SKILL.md`
- Modify: `plugins/freecad/skills/freecad-render-views/SKILL.md`

**Interfaces:**
- Consumes: `PLUGINS` layout (Task 4), the guard's `<skills-repo>` convention (spec D5).
- Produces: every documented command and path resolvable from any working directory.

- [ ] **Step 1: Replace the engine and adapter prefixes**

Run from the plugin repo root and apply these exact `file:line` replacements — the old
text is `<repo>/skills/…`, the new text is `<skills-repo>/plugins/…`:

| file:line | was | becomes |
|---|---|---|
| `woodbuild-engine/SKILL.md:69` | `[--adapter <repo>/skills/homedepot-catalogue/scripts/homedepot_adapter.py]` | `[--adapter <skills-repo>/plugins/homedepot/skills/homedepot-catalogue/scripts/homedepot_adapter.py]` |
| `woodbuild-engine/SKILL.md:82-83` | `-s skills/woodbuild-engine/scripts/tests \ -t skills/woodbuild-engine/scripts` | `-s plugins/woodbuild/skills/woodbuild-engine/scripts/tests \ -t plugins/woodbuild/skills/woodbuild-engine/scripts` |
| `building-from-reference/SKILL.md:68` | `E=<repo>/skills/woodbuild-engine/scripts` | `E=<skills-repo>/plugins/woodbuild/skills/woodbuild-engine/scripts` |
| `building-from-reference/SKILL.md:71` | `--adapter <repo>/skills/homedepot-catalogue/scripts/homedepot_adapter.py` | `--adapter <skills-repo>/plugins/homedepot/skills/homedepot-catalogue/scripts/homedepot_adapter.py` |
| `wood-framing/SKILL.md:20` | `E=<repo>/skills/woodbuild-engine/scripts` | `E=<skills-repo>/plugins/woodbuild/skills/woodbuild-engine/scripts` |
| `build-pricing/SKILL.md:17` | `E=<repo>/skills/woodbuild-engine/scripts` | `E=<skills-repo>/plugins/woodbuild/skills/woodbuild-engine/scripts` |
| `homedepot-catalogue/SKILL.md:13,19,23` | `<repo>/skills/…` | `<skills-repo>/plugins/homedepot/skills/homedepot-catalogue/scripts/…` and `E=<skills-repo>/plugins/woodbuild/skills/woodbuild-engine/scripts` |
| `homedepot-catalogue/scripts/homedepot_adapter.py:8` | `--adapter skills/homedepot-catalogue/scripts/homedepot_adapter.py` | `--adapter <skills-repo>/plugins/homedepot/skills/homedepot-catalogue/scripts/homedepot_adapter.py` |

- [ ] **Step 2: Fix the engine skill's own two path claims**

In `woodbuild-engine/SKILL.md`, the coupling paragraph and the Running block:

- Replace the sentence that says the other skills reach the engine as
  `../woodbuild-engine/scripts/...` with: the other skills reach it as
  `<skills-repo>/plugins/woodbuild/skills/woodbuild-engine/scripts/…`, which is why every
  documented command is absolute — a build workspace lives outside this repo.
- Replace the bare `python3 scripts/woodbuild.py …` in the Running block with
  `python3 <skills-repo>/plugins/woodbuild/skills/woodbuild-engine/scripts/woodbuild.py …`.

- [ ] **Step 3: Fix the two absolute machine paths in the freecad skills**

`freecad-model-hygiene/SKILL.md:24` and `freecad-render-views/SKILL.md:62` both contain a
hardcoded `/Users/eric/.pi/agent/skills/<skill>/scripts` in a `sys.path.insert` example.
Replace each with the plugin-repo form:

```python
import sys; sys.path.insert(0, "<skills-repo>/plugins/freecad/skills/<this-skill>/scripts")
```

- [ ] **Step 4: Fix the store skill's overstatement**

`homedepot-catalogue/SKILL.md:13` calls its adapter "the only file in the repository that
names a store". The README names it too and the guard only scans the plugins tree. Reword
to: the only file **in these plugins** that names a store — the guard fails if any other
file does.

- [ ] **Step 5: Verify no old path form survives**

```bash
cd "/Users/eric/Documents/GitHub Projects/skills"
grep -rn "<repo>/skills\|/Users/eric/\.pi/agent/skills\|\.\./woodbuild-engine" plugins/ || echo "no stale path forms"
grep -rn "skills-repo>" plugins/ | wc -l
```

Expected: `no stale path forms`, and a non-zero count of `<skills-repo>` uses.

- [ ] **Step 6: Run the suite and commit**

```bash
cd "/Users/eric/Documents/GitHub Projects/skills"
python3 -m unittest discover -s plugins/woodbuild/skills/woodbuild-engine/scripts/tests \
  -t plugins/woodbuild/skills/woodbuild-engine/scripts 2>&1 | grep -E "^(Ran|OK|FAILED)"
git add plugins
git commit -m "docs: point every path at the plugin repo"
```

Expected: `Ran 153 tests`, `OK (skipped=9)`.

---

### Task 6: Publish the plugin repo

**Files:** none (git only).

**Interfaces:**
- Consumes: Tasks 1-5, all committed on `woodbuild-plugins`.
- Produces: `main` in the plugin repo containing the plugins, and a clone-ready `main` on GitHub — the input to Task 8's install. **Task 7 must not run before this task is done.**

- [ ] **Step 1: Confirm the branch is complete and the working tree is sane**

```bash
cd "/Users/eric/Documents/GitHub Projects/skills"
git log --oneline main..HEAD
git status --porcelain -uall | grep -v '^??' | head
```

Expected: five commits from Tasks 1-5; no modified tracked files (untracked `.idea/` is now
ignored, and the `clean-code-workspace` scratch remains untracked by design).

- [ ] **Step 2: Push and open the PR**

```bash
cd "/Users/eric/Documents/GitHub Projects/skills"
git push -u origin woodbuild-plugins
gh pr create --base main --head woodbuild-plugins \
  --title "Add woodbuild, freecad and homedepot plugins; declare pi skills" \
  --body "Three new plugins matching the existing marketplace format, plus a repo-level \`package.json\` with a \`pi.skills\` manifest so pi can install the whole repo as a package. Also registers the two plugins that were missing from the marketplace index and ignores \`.idea/\`.

Engine suite: 153 tests, OK (skipped=9), run from \`plugins/woodbuild/skills/woodbuild-engine/scripts\`."
```

Expected: a PR URL. The repo is public, so the PR is public.

- [ ] **Step 3: Merge and update local `main`**

```bash
cd "/Users/eric/Documents/GitHub Projects/skills"
gh pr merge --merge
git checkout main
git pull --ff-only
git log --oneline -1
ls plugins
```

Expected: `main` contains the merge commit; `plugins/` lists seven dirs.

- [ ] **Step 4: Delete the remote branch**

```bash
cd "/Users/eric/Documents/GitHub Projects/skills"
git push origin --delete woodbuild-plugins
git branch -d woodbuild-plugins
```

---

### Task 7: Delete the skills from the shared config (do not merge yet)

**Files:**
- Delete: `~/pi-config/skills/` (all nine skill dirs)
- Modify: `~/pi-config/README.md` (the Skills section and the two adapter mentions)

**Interfaces:**
- Consumes: the published plugin repo (Task 6).
- Produces: a `pi-config` branch `drop-skills` whose merge is gated on Task 8.

- [ ] **Step 1: Branch, and confirm the plugin repo is safely published first**

```bash
cd /Users/eric/pi-config
git checkout main && git pull --ff-only
git log --oneline -1
git ls-remote --heads origin | grep -c main
cd "/Users/eric/Documents/GitHub Projects/skills" && git log --oneline -1 && git status -sb | head -1
cd /Users/eric/pi-config && git checkout -b drop-skills
```

Expected: plugin repo `main` is merged and pushed, on no branch of its own. If that is not
true, stop — do not delete the skills yet.

- [ ] **Step 2: Delete the skills directory**

```bash
cd /Users/eric/pi-config
git rm -r --quiet skills
git status --porcelain | grep -c '^D' 
ls skills 2>&1 | head -1
```

Expected: a large deletion count, and `ls: skills: No such file or directory`.

- [ ] **Step 3: Rewrite the README's Skills section**

Replace the whole `- **Skills**: …` bullet (currently `README.md:56-…`, ending with the
`freecad-render-views`/`freecad-model-hygiene` sentences) with:

```markdown
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
```

- [ ] **Step 4: Fix the two remaining path mentions in the README**

- The adapter sentence in the MCP bullet (`README.md:98` region) becomes
  `plugins/homedepot/skills/homedepot-catalogue/scripts/homedepot_adapter.py` **inside the
  installed package clone**, with no `skills/` path.
- Any surviving reference to `skills/woodbuild-engine/scripts/tests/test_boundaries.py`
  in the README becomes the same plugin path inside the clone.

```bash
cd /Users/eric/pi-config
grep -n "skills/" README.md
```

Expected: no line refers to a local `skills/` directory; the only skill paths are
plugin-relative inside the clone.

- [ ] **Step 5: Commit on the branch — no merge, no push**

```bash
cd /Users/eric/pi-config
git add -A skills README.md
git commit -m "config: move the skills out to the published plugin marketplace"
git log --oneline -2
```

Expected: the commit exists on `drop-skills`; `main` is untouched.

---

### Task 8: Install the package, verify, then merge

**Files:**
- Modify: `settings.json` (only by `pi install`, never by hand)

**Interfaces:**
- Consumes: the published repo (Task 6) and the `drop-skills` branch (Task 7).
- Produces: the verified end state — nine skills loaded from the clone, `main` clean of skills.

- [ ] **Step 1: Install**

```bash
cd /Users/eric/pi-config
pi install git:github.com/EricMarcantonio/skills
```

Expected: an install message; the clone appears at
`/Users/eric/pi-config/git/github.com/EricMarcantonio/skills`.

- [ ] **Step 2: Verify the clone is ignored and the entry is the only config change**

```bash
cd /Users/eric/pi-config
git check-ignore -v git/github.com/EricMarcantonio/skills
git diff --stat settings.json
git diff settings.json | grep -A 3 packages
git status --porcelain -uall | grep -v '^ M settings.json' | head
```

Expected: `git check-ignore` prints the `.gitignore:…:git/` rule; the `settings.json` diff
adds exactly one `packages` entry for the repo; nothing else changed in the tree.

- [ ] **Step 3: Verify the clone's own suite still passes where it landed**

```bash
cd /Users/eric/pi-config/git/github.com/EricMarcantonio/skills
python3 -m unittest discover -s plugins/woodbuild/skills/woodbuild-engine/scripts/tests \
  -t plugins/woodbuild/skills/woodbuild-engine/scripts 2>&1 | grep -E "^(Ran|OK|FAILED)"
```

Expected: `Ran 153 tests`, `OK (skipped=9)`.

- [ ] **Step 4: Verify pi actually loads nine skills from the package**

```bash
cd /Users/eric/pi-config
ls git/github.com/EricMarcantonio/skills/plugins/*/skills/*/SKILL.md | wc -l
```

Expected: `9`. Then start a fresh pi session and confirm its skill list contains
`building-from-reference`, `wood-framing`, `sheet-and-board-nesting`, `build-pricing`,
`freecad-model-to-spec`, `woodbuild-engine`, `freecad-model-hygiene`,
`freecad-render-views` and `homedepot-catalogue`, and that `/skill:woodbuild-engine`
loads. **Do not proceed to Step 5 until a fresh session lists them** — this is the gate the
whole migration rests on.

- [ ] **Step 5: Merge the config branch and push**

```bash
cd /Users/eric/pi-config
git checkout main
git merge --ff-only drop-skills
python3 - <<'PY'
import json, pathlib
d = json.loads(pathlib.Path("settings.json").read_text())
print([p for p in d.get("packages", []) if "skills" in p])
PY
git push origin main
git branch -d drop-skills
git log --oneline -1
ls skills 2>&1 | head -1
```

Expected: the merge fast-forwards; the printed list shows the skills package entry;
`main` is pushed; `skills` does not exist.

- [ ] **Step 6: Final negative check on the shared config**

```bash
cd /Users/eric/pi-config
git ls-files | grep -c '^skills/'
git grep -n "Documents/GitHub Projects/skills" -- . | head
```

Expected: `0` tracked skill files, and no reference to the local working copy path — the
shared config names only the public repo URL in `settings.json` and `README.md`.

---

## Self-Review

**Spec coverage**

| spec item | task |
|---|---|
| D1 three plugins, grouped by dependency | Tasks 1, 2 |
| D2 marketplace format kept | Tasks 1, 2, 3 (manifests, READMEs, index, table) |
| D3 `package.json` pi bridge | Task 3 |
| D4 install mechanics, shared entry accepted | Tasks 6, 8 |
| D5 `<skills-repo>` placeholder | Task 5 (all eight files), Tasks 7-8 (documented commands) |
| D6 guard moves and learns the new root | Task 4 (plus its bite check in Step 6) |
| D7 order of operations, the no-skills window | Tasks 6 → 7 → 8, with Task 7 Step 1 and Task 8 Step 4 as the gates |
| D8 `.idea/` ignore, scratch left alone | Task 3 Step 2, Task 6 Step 1 |
| Non-goals (no symlink, no skills entry, docs stay) | Task 7 Steps 2-4, Task 8 Step 6 |
| Carried minors (engine Running block, "only file" overstated) | Task 5 Steps 2 and 4 |

**Placeholder scan:** no TBD/TODO; every manifest and prose block is written out; the one
scripted step (marketplace index) carries its full source.

**Type/name consistency:** `PLUGINS`, `ENGINE_SKILL`, `STORE_OWNER`, `ENGINE_USERS`,
`EXPECTED_PLUGINS` are defined once in Task 4 Step 2 and used only in Steps 3-4 with the
same spelling. Plugin names are `woodbuild`, `freecad`, `homedepot` in every task,
manifest, path, table row and guard constant. The canonical suite command is identical in
Tasks 4, 5, 7 and 8. `ENGINE_USERS` drops `homedepot-catalogue` in Task 4 Step 2, and the
reason is stated where it changes.

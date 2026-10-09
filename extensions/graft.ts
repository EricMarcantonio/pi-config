/**
 * Graft for pi
 *
 * Graft (https://github.com/trailhq/graft) wires itself into Claude Code with an MCP server, a
 * skill and hooks, but has no pi integration yet. pi already reads the Graft section that
 * `graft init` writes into AGENTS.md; this extension adds the rest, for any repo whose root has a
 * `graft/` graph:
 *
 * - registers the `graft` MCP server (`graft mcp`) for the session
 * - loads the Graft skill from `.claude/skills/graft/`, where `graft init` puts it
 * - after each `edit`/`write`, marks the graph dirty and appends Graft's blast-radius note to the
 *   tool result; at the end of each run, starts Graft's background re-sync
 *
 * The edit and end-of-run steps reuse the repo's `.claude/helpers/graft-hooks.cjs` shim, so they
 * behave exactly like Graft's Claude Code hooks. Repos without `graft/` are left alone, and
 * nothing happens when the `graft` CLI is not installed.
 */

import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, isAbsolute, join, resolve, sep } from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const HOOK_TIMEOUT_MS = 8000;

function findRepoRoot(start: string): string | undefined {
	let dir = resolve(start);
	while (true) {
		if (existsSync(join(dir, ".git"))) return dir;
		const parent = dirname(dir);
		if (parent === dir) return undefined;
		dir = parent;
	}
}

function findGraftRoot(cwd: string): string | undefined {
	const root = findRepoRoot(cwd);
	return root && existsSync(join(root, "graft")) ? root : undefined;
}

function graftInstalled(): boolean {
	return spawnSync("graft", ["--version"], { stdio: "ignore" }).status === 0;
}

/** Runs one Graft hook event through the repo's shim and returns the context it emits, if any. */
function runGraftHook(root: string, event: string, input: object): string | undefined {
	const shim = join(root, ".claude", "helpers", "graft-hooks.cjs");
	if (!existsSync(shim)) return undefined;
	const result = spawnSync(process.execPath, [shim, event], {
		cwd: root,
		input: JSON.stringify({ cwd: root, ...input }),
		env: { ...process.env, CLAUDE_PROJECT_DIR: root },
		encoding: "utf8",
		timeout: HOOK_TIMEOUT_MS,
	});
	try {
		return JSON.parse(result.stdout)?.hookSpecificOutput?.additionalContext;
	} catch {
		return undefined;
	}
}

export default function (pi: ExtensionAPI) {
	let graftRoot: string | undefined;
	let editedThisRun = false;

	pi.on("session_start", (_event, ctx) => {
		graftRoot = findGraftRoot(ctx.cwd);
		if (graftRoot && graftInstalled()) {
			pi.registerMcpServer("graft", { command: "graft", args: ["mcp"], cwd: graftRoot });
		}
	});

	pi.on("resources_discover", (event) => {
		const root = findGraftRoot(event.cwd);
		const skill = root && join(root, ".claude", "skills", "graft");
		return skill && existsSync(skill) ? { skillPaths: [skill] } : {};
	});

	pi.on("tool_result", (event, ctx) => {
		if (!graftRoot || event.isError) return;
		if (event.toolName !== "edit" && event.toolName !== "write") return;
		const path = event.input.path;
		if (typeof path !== "string") return;
		const file = isAbsolute(path) ? path : resolve(ctx.cwd, path);
		if (!file.startsWith(graftRoot + sep)) return;

		editedThisRun = true;
		const note = runGraftHook(graftRoot, "post-edit", { tool_input: { file_path: file } });
		if (note) return { content: [...event.content, { type: "text", text: note }] };
	});

	pi.on("agent_end", () => {
		if (!graftRoot || !editedThisRun) return;
		editedThisRun = false;
		runGraftHook(graftRoot, "stop", {});
	});
}

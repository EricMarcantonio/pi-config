/**
 * Wordy footer
 *
 * Replaces pi's symbol footer (↑ ↓ R W CH) with plain words, e.g.:
 *   input 487k  output 56k  cache-read 4.2M  cache-hit 90.8%  cost $0.101  context 4.0% (auto-compact)
 *
 * Why an extension: the built-in footer text is hardcoded in pi
 * (dist/modes/interactive/components/footer.js) and has no settings option,
 * so the only way to change it is ctx.ui.setFooter().
 *
 * Uses the same data sources as the built-in footer:
 *   totals  -> ctx.sessionManager.getEntries()  (assistant + tool + summary usage)
 *   context -> ctx.getContextUsage()
 *   model   -> ctx.model
 *   branch  -> footerData.getGitBranch()
 *
 * Toggle at runtime with /footer-words. The choice is persisted to
 * settings.json as "wordyFooter" so it syncs with the rest of the config.
 */

import type { AssistantMessage } from "@earendil-works/pi-ai";
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { truncateToWidth, visibleWidth } from "@earendil-works/pi-tui";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, isAbsolute, join, relative, resolve, sep } from "node:path";

const HOME = process.env.HOME || process.env.USERPROFILE || homedir();
const CONFIG_DIR = process.env.PI_CODING_AGENT_DIR || join(HOME, ".pi", "agent");
const SETTINGS_PATH = join(CONFIG_DIR, "settings.json");

/** Read the persisted "wordyFooter" flag (defaults to true). */
function readWordyEnabled(): boolean {
	try {
		const raw = JSON.parse(readFileSync(SETTINGS_PATH, "utf8")) as { wordyFooter?: boolean };
		return raw.wordyFooter !== false;
	} catch {
		return true;
	}
}

/** Persist the "wordyFooter" flag, preserving all other settings keys. */
function writeWordyEnabled(enabled: boolean): void {
	try {
		const raw = existsSync(SETTINGS_PATH)
			? (JSON.parse(readFileSync(SETTINGS_PATH, "utf8")) as Record<string, unknown>)
			: {};
		raw.wordyFooter = enabled;
		mkdirSync(dirname(SETTINGS_PATH), { recursive: true });
		writeFileSync(SETTINGS_PATH, `${JSON.stringify(raw, null, 2)}\n`, "utf8");
	} catch {
		// best effort; footer still toggles for this session
	}
}

/** Same formatting thresholds as the built-in footer. */
function formatTokens(count: number): string {
	if (count < 1000) return count.toString();
	if (count < 10000) return `${(count / 1000).toFixed(1)}k`;
	if (count < 1000000) return `${Math.round(count / 1000)}k`;
	if (count < 10000000) return `${(count / 1000000).toFixed(1)}M`;
	return `${Math.round(count / 1000000)}M`;
}

function formatCwd(cwd: string): string {
	if (!HOME) return cwd;
	const resolvedCwd = resolve(cwd);
	const resolvedHome = resolve(HOME);
	const rel = relative(resolvedHome, resolvedCwd);
	const inside = rel === "" || (rel !== ".." && !rel.startsWith(`..${sep}`) && !isAbsolute(rel));
	if (!inside) return cwd;
	return rel === "" ? "~" : `~${sep}${rel}`;
}

/** Read compaction.enabled from settings.json (defaults to true). */
function readAutoCompact(): boolean {
	const dir = CONFIG_DIR;
	try {
		const raw = JSON.parse(readFileSync(join(dir, "settings.json"), "utf8")) as {
			compaction?: boolean | { enabled?: boolean };
		};
		if (raw.compaction === false) return false;
		if (typeof raw.compaction === "object" && raw.compaction !== null && raw.compaction.enabled === false) return false;
	} catch {
		// no settings file / unreadable -> keep default
	}
	return true;
}

function applyWordyFooter(ctx: ExtensionContext): void {
	const autoCompact = readAutoCompact();

	ctx.ui.setFooter((tui, theme, footerData) => {
		const unsubscribe = footerData.onBranchChange(() => tui.requestRender());

		return {
			dispose: unsubscribe,
			invalidate() {},
			render(width: number): string[] {
				// ---- cumulative token + cost totals (same as built-in footer)
				let input = 0;
				let output = 0;
				let cacheRead = 0;
				let cacheWrite = 0;
				let cost = 0;
				let subagentCost = 0;
				let latestHitRate: number | undefined;

				const addUsage = (u: AssistantMessage["usage"] | undefined) => {
					if (!u) return;
					input += u.input ?? 0;
					output += u.output ?? 0;
					cacheRead += u.cacheRead ?? 0;
					cacheWrite += u.cacheWrite ?? 0;
					cost += u.cost?.total ?? 0;
				};

				for (const entry of ctx.sessionManager.getEntries()) {
					if (entry.type === "message" && entry.message.role === "assistant") {
						const u = (entry.message as AssistantMessage).usage;
						addUsage(u);
						const prompt = (u.input ?? 0) + (u.cacheRead ?? 0) + (u.cacheWrite ?? 0);
						latestHitRate = prompt > 0 ? ((u.cacheRead ?? 0) / prompt) * 100 : undefined;
					} else if (entry.type === "message" && entry.message.role === "toolResult") {
						const result = entry.message as {
							toolName?: string;
							usage?: AssistantMessage["usage"];
							details?: { totalCost?: { costUsd?: number } };
						};
						addUsage(result.usage);
						// pi-subagents reports the exact child cost (nested children included)
						// in details.totalCost. usage.cost.total mirrors that number, so count
						// exactly one of the two to keep the split honest.
						const reported = result.details?.totalCost?.costUsd;
						if (typeof reported === "number") {
							subagentCost += reported;
						} else if (result.toolName === "subagent") {
							subagentCost += result.usage?.cost?.total ?? 0;
						}
					} else if (entry.type === "branch_summary" || entry.type === "compaction") {
						addUsage((entry as { usage?: AssistantMessage["usage"] }).usage);
					}
				}

				// ---- context usage
				const usage = ctx.getContextUsage();
				const percentValue = usage?.percent ?? 0;
				const percent = usage && usage.percent !== null ? `${usage.percent.toFixed(1)}%` : "?";
				const auto = autoCompact ? " (auto-compact)" : "";
				const contextText = `context ${percent}${auto}`;
				const contextColored =
					percentValue > 90
						? theme.fg("error", contextText)
						: percentValue > 70
							? theme.fg("warning", contextText)
							: theme.fg("dim", contextText);

				// ---- word stats
				const parts: string[] = [];
				if (input) parts.push(theme.fg("dim", `input ${formatTokens(input)}`));
				if (output) parts.push(theme.fg("dim", `output ${formatTokens(output)}`));
				if (cacheRead) parts.push(theme.fg("dim", `cache-read ${formatTokens(cacheRead)}`));
				if (cacheWrite) parts.push(theme.fg("dim", `cache-write ${formatTokens(cacheWrite)}`));
				if ((cacheRead || cacheWrite) && latestHitRate !== undefined) {
					parts.push(theme.fg("dim", `cache-hit ${latestHitRate.toFixed(1)}%`));
				}
				if (cost || subagentCost) {
					if (subagentCost > 0) {
						// total is the same accumulation pi's builtin footer uses, so it
						// already contains the child cost; chat is what remains.
						const chatCost = Math.max(0, cost - subagentCost);
						parts.push(theme.fg("dim", `chat $${chatCost.toFixed(3)}`));
						parts.push(theme.fg("dim", `subagent $${subagentCost.toFixed(3)}`));
						parts.push(theme.fg("dim", `total $${cost.toFixed(3)}`));
					} else {
						parts.push(theme.fg("dim", `cost $${cost.toFixed(3)}`));
					}
				}
				parts.push(contextColored);

				let left = parts.join("  ");
				if (visibleWidth(left) > width) left = truncateToWidth(left, width, "...");

				// ---- right: model (+ thinking level)
				const modelName = ctx.model?.id ?? "no-model";
				let rightPlain = modelName;
				if (ctx.model?.reasoning) {
					const level = ctx.thinkingLevel ?? "off";
					rightPlain = level === "off" ? `${modelName} · thinking off` : `${modelName} · ${level}`;
				}
				const right = theme.fg("dim", rightPlain);

				const leftWidth = visibleWidth(left);
				const rightWidth = visibleWidth(right);
				const minPad = 2;
				let statsLine: string;
				if (leftWidth + minPad + rightWidth <= width) {
					statsLine = left + " ".repeat(width - leftWidth - rightWidth) + right;
				} else {
					const avail = width - leftWidth - minPad;
					if (avail > 0) {
						const truncRight = truncateToWidth(right, avail, "");
						statsLine =
							left + " ".repeat(Math.max(0, width - leftWidth - visibleWidth(truncRight))) + truncRight;
					} else {
						statsLine = truncateToWidth(left, width, "");
					}
				}

				// ---- pwd (+ branch), then stats, then extension statuses
				let pwd = formatCwd(ctx.cwd);
				const branch = footerData.getGitBranch();
				if (branch) pwd = `${pwd} (${branch})`;

				const lines = [truncateToWidth(theme.fg("dim", pwd), width, theme.fg("dim", "...")), statsLine];

				const statuses = footerData.getExtensionStatuses();
				if (statuses.size > 0) {
					lines.push(truncateToWidth(Array.from(statuses.values()).join(" "), width, theme.fg("dim", "...")));
				}
				return lines;
			},
		};
	});
}

export default function (pi: ExtensionAPI) {
	pi.on("session_start", (_event, ctx) => {
		if (!ctx.hasUI) return;
		if (readWordyEnabled()) applyWordyFooter(ctx);
	});

	pi.registerCommand("footer-words", {
		description: "Toggle wordy footer (words instead of ↑ ↓ R W CH symbols); choice is saved to settings.json",
		handler: async (_args, ctx) => {
			if (!ctx.hasUI) return;
			const next = !readWordyEnabled();
			writeWordyEnabled(next);
			if (next) {
				applyWordyFooter(ctx);
				ctx.ui.notify("Wordy footer enabled (saved to settings.json)", "info");
			} else {
				ctx.ui.setFooter(undefined);
				ctx.ui.notify("Default footer restored (saved to settings.json)", "info");
			}
		},
	});
}

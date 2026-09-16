---
description: Scout gathers context, planner creates implementation plan (no implementation)
---
Run this as ONE `subagent` call using `workflowScript`. Thread the scout's output
into the planner through the awaited run's `.output` — the legacy `chain`
parameter is gone in pi-subagents.

```js
subagent({ workflowScript: `
  const scouted = await runs.run("scout", { agent: "scout", task: "Find all code relevant to: $@" });
  return runs.run("plan", { agent: "planner", task: "Create an implementation plan for \\"$@\\" using this context:\\n" + scouted.output });
` });
```

Steps:
1. `scout` — find all code relevant to the request.
2. `planner` — produce the implementation plan.

Do NOT implement anything. Return only the plan.

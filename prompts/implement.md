---
description: Full implementation workflow - scout gathers context, planner creates plan, worker implements
---
Run this as ONE `subagent` call using `workflowScript`. Thread each step's output
into the next through the awaited run's `.output` — the legacy `chain` parameter
is gone in pi-subagents.

```js
subagent({ workflowScript: `
  const scouted = await runs.run("scout", { agent: "scout", task: "Find all code relevant to: $@" });
  const planned = await runs.run("planner", { agent: "planner", task: "Create an implementation plan for \\"$@\\" using this context:\\n" + scouted.output });
  return runs.run("implement", { agent: "worker", task: "Implement this plan:\\n" + planned.output });
` });
```

Steps:
1. `scout` — find all code relevant to the request.
2. `planner` — turn that context into an implementation plan.
3. `worker` — implement the plan.

Do not skip steps and do not do the work in this session.

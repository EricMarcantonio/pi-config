---
description: Worker implements, reviewer reviews, worker applies feedback
---
Run this as ONE `subagent` call using `workflowScript`. Thread each step's output
into the next through the awaited run's `.output` — the legacy `chain` parameter
is gone in pi-subagents.

```js
subagent({ workflowScript: `
  const implemented = await runs.run("implement", { agent: "worker", task: "$@" });
  const reviewed = await runs.run("review", { agent: "reviewer", task: "Review the implementation from the previous step. Original task: $@\\n\\nImplementation:\\n" + implemented.output });
  return runs.run("apply", { agent: "worker", task: "Apply the review feedback:\\n" + reviewed.output });
` });
```

Steps:
1. `worker` — implement the request.
2. `reviewer` — review the implementation.
3. `worker` — apply the review feedback.

Do not skip steps and do not do the work in this session.

"""Fast-forward pinned forks from upstream and propose pin bumps after a cooldown.

A package in settings.json is managed when it is a `git:github.com/<owner>/<repo>@<40-hex sha>`
source and forks.json maps that repo to its expected upstream. For each managed fork, a weekly run:

1. Fast-forwards the fork's default branch from upstream. A rewritten upstream history (a
   non-fast-forward) is reported and never forced, so commits already pinned stay in the fork. If
   GitHub reports a different parent than forks.json (an upstream was deleted and GitHub picked
   another fork in the network), the sync is skipped.
2. Stages the fork's new head with the time it was first seen. A head staged by an earlier run
   (at least COOLDOWN ago) is promoted to the new pin.
3. Writes promoted pins to settings.json for the workflow to open as a pull request.

Staged heads are kept in the STAGED_PINS Actions variable, so the cooldown is measured from when
this job saw a commit, not from commit dates, which an attacker can set.
"""

import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://api.github.com"
COOLDOWN = timedelta(days=6)  # one weekly run, with slack for cron jitter
PINNED_GIT_SOURCE = re.compile(r"^git:github\.com/([\w.-]+)/([\w.-]+)@([0-9a-f]{40})$")
STATE_VARIABLE = "STAGED_PINS"


def github(method, path, body=None):
    request = urllib.request.Request(
        API + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as error:
        raw = error.read()
        return error.code, json.loads(raw) if raw else None


def source_of(package):
    return package if isinstance(package, str) else package.get("source", "")


def with_source(package, source):
    if isinstance(package, str):
        return source
    return {**package, "source": source}


def load_state(repository):
    status, body = github("GET", f"/repos/{repository}/actions/variables/{STATE_VARIABLE}")
    if status == 404:
        return {}
    return json.loads(body["value"])


def save_state(repository, state):
    payload = {"name": STATE_VARIABLE, "value": json.dumps(state, sort_keys=True)}
    status, _ = github("PATCH", f"/repos/{repository}/actions/variables/{STATE_VARIABLE}", payload)
    if status == 404:
        github("POST", f"/repos/{repository}/actions/variables", payload)


def sync_fork(fork, branch):
    """Fast-forward only. Returns an error message, or None on success."""
    status, body = github("POST", f"/repos/{fork}/merge-upstream", {"branch": branch})
    if status == 200:
        return None
    message = (body or {}).get("message", "")
    if status == 409:
        return f"upstream of {fork} diverged ({message}); not forcing it"
    return f"syncing {fork} failed with HTTP {status}: {message}"


def plan_fork(fork, upstream, pinned, state, now):
    """Return (new_pin or None, problems). Updates state[fork] in place."""
    status, repo = github("GET", f"/repos/{fork}")
    if status != 200:
        return None, [f"cannot read {fork} (HTTP {status})"]
    problems = []
    parent = (repo.get("parent") or {}).get("full_name")
    if parent != upstream:
        problems.append(
            f"{fork} now has parent {parent}, not {upstream}; upstream may be gone, not syncing"
        )
    else:
        error = sync_fork(fork, repo["default_branch"])
        if error:
            problems.append(error)

    _, branch = github("GET", f"/repos/{fork}/branches/{repo['default_branch']}")
    head = branch["commit"]["sha"]

    staged = state.get(fork)
    new_pin = None
    if staged:
        seen = datetime.fromisoformat(staged["seen"])
        if now - seen < COOLDOWN:
            return None, problems
        if staged["sha"] != pinned:
            new_pin = staged["sha"]
    current = new_pin or pinned
    if head == current:
        state.pop(fork, None)
    else:
        state[fork] = {"sha": head, "seen": now.isoformat()}
    return new_pin, problems


def main():
    repository = os.environ["GITHUB_REPOSITORY"]
    now = datetime.now(timezone.utc)
    with open("settings.json") as file:
        settings = json.load(file)
    with open("forks.json") as file:
        upstreams = json.load(file)
    state = load_state(repository)

    bumps, problems = [], []
    for index, package in enumerate(settings.get("packages", [])):
        match = PINNED_GIT_SOURCE.match(source_of(package))
        if not match:
            continue
        owner, name, pinned = match.groups()
        fork = f"{owner}/{name}"
        if fork not in upstreams:
            continue
        new_pin, fork_problems = plan_fork(fork, upstreams[fork], pinned, state, now)
        problems += fork_problems
        if new_pin:
            source = f"git:github.com/{fork}@{new_pin}"
            settings["packages"][index] = with_source(package, source)
            bumps.append(f"- `{fork}`: https://github.com/{fork}/compare/{pinned}...{new_pin}")

    save_state(repository, state)
    if bumps:
        with open("settings.json", "w") as file:
            file.write(json.dumps(settings, indent=2) + "\n")

    with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as output:
        output.write(f"bumped={'true' if bumps else 'false'}\n")
        output.write(f"problems={'true' if problems else 'false'}\n")
    with open("pr-body.md", "w") as file:
        file.write("Pins below were staged by an earlier run and have sat for a week.\n")
        file.write("Review each diff before merging.\n\n" + "\n".join(bumps) + "\n")
        if problems:
            file.write("\n**Problems:**\n\n" + "\n".join(f"- {p}" for p in problems) + "\n")

    for problem in problems:
        print(f"::warning::{problem}")


if __name__ == "__main__":
    main()

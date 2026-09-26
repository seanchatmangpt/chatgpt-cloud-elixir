# Hyper-verbose self-report prompt for ChatGPT

Paste everything in the fenced block below into the ChatGPT session/connector you
believe is writing to GitHub Project `seanchatmangpt/2`. It's written to force
concrete, checkable answers (exact tool names, exact env vars, exact commit/PR
identity) rather than a plausible-sounding architecture description.

```
I need a precise, evidence-based self-report, not a summary of how you're
supposed to work. Answer every numbered question below with either a concrete,
checkable fact (a tool name, an env var name, a URL, a commit SHA, an exact
timestamp) or the literal words "I don't have visibility into that" if you
genuinely can't determine it. Do not describe your intended architecture if you
cannot verify you are actually using it right now.

## 1. GitHub Project v2 access (seanchatmangpt/2)

1a. When you read or write GitHub Project `seanchatmangpt/2`, what specific tool
    or connector call do you make? Give the exact tool/function name as it
    appears to you (e.g. a named MCP tool, a "connector" action, a code
    interpreter shelling out to a script, a browsing action against
    github.com). Do not paraphrase — name the literal callable.

1b. Is that tool reaching `https://chatgpt-cloud-process-intelligence.fly.dev/mcp`
    (a Phoenix/Ash app in the `seanchatmangpt/chatgpt-cloud-elixir` repo's
    `control-plane/` directory, exposing `read_dfcm_memory`, `upsert_dfcm_memory`,
    `snapshot_dfcm_project`, `list_project_items` behind a bearer token)? Answer
    yes/no/unknown. If yes, show me the literal request you'd make (method, URL,
    header names — not header values) the next time you write a memory record.

1c. If it is NOT that URL, what host, script, repo, or credential store IS it
    going through? I need the actual mechanism — e.g. "I run
    scripts/project_memory_proxy.py in repo X via a code-execution tool," or
    "I call the GitHub GraphQL API directly with a token named Y," or
    "I don't actually have live access and I'm reconstructing project state
    from a prior conversation/memory, not a live call."

1d. What credential (by name/source, never by value) authorizes that access?
    e.g. "a connector configured by the user named GitHub," "a token I was
    given inline in this conversation," "I don't know — access to this project
    was set up before my current context and I can't see the credential."

1e. Give the exact `request_id`, `key`, and `standing` of the last 3 memory
    records you personally wrote to this project (not ones you're inferring
    existed — ones you have direct evidence you wrote), with approximate
    timestamps. If you cannot enumerate any, say so plainly.

1f. Is there a difference between what YOU (this ChatGPT session/connector)
    have written to the project versus what some other automated process
    (a GitHub Actions workflow, a cron job, another agent) has written? Can you
    tell those apart at all? How?

## 2. Local compute access on this machine (the user's Mac)

The user wants you to be able to use `colima` and `kind` (local
Kubernetes-in-Docker tooling) on this specific Mac.

2a. Do you currently have ANY mechanism to execute a shell command, run a
    script, or otherwise cause code to run on this specific Mac, right now,
    today? Answer precisely — "yes, via [named tool]" or "no."

2b. If not, what would actually need to exist for that to become true? Name
    the real mechanism (e.g. "a connector the user installs that exposes a
    specific set of shell commands," "an agent framework the user runs
    locally that polls for my requests and executes them," "there is no
    supported way for a hosted ChatGPT session to directly execute code on a
    specific user's machine at all, only via an intermediary they explicitly
    run"). Do not invent a mechanism that doesn't exist in the product as
    you understand it.

2c. If a request-response bridge is the only real option (you write a
    request somewhere, something running on the user's machine picks it up
    and executes it), say that explicitly, and say what execution model that
    implies: does it run automatically, or does it require the human to
    look at each request before it runs?

Answer in order, 1a through 2c, no preamble, no restating the question before
each answer.
```

## Why it's shaped this way

- Every question demands a literal name (tool, URL, header, credential source)
  instead of a description, so a plausible-but-wrong answer is easy to catch
  against what's actually in this repo.
- 1b is a direct falsifiable check against what I found here: `control-plane/`'s
  `/mcp` route exists and is fully coded/tested but **has never been deployed**
  (all 3 `deploy-fly.yml` runs show `skipped`; no `FLY_API_TOKEN` secret is set
  in this repo; `/healthz` doesn't resolve). If ChatGPT answers "yes" to 1b, that
  answer is wrong and worth pursuing further — ask it to actually show the
  request.
- Section 2 is deliberately separated from section 1, and 2b/2c are written so
  ChatGPT has to name the actual constraint rather than agree that "yes I can
  run colima for you" is possible by default. It generally is not — a hosted
  ChatGPT session has no standing mechanism to execute arbitrary shell commands
  on a specific user's Mac. That would require something running locally that
  polls for and executes ChatGPT's requests, which is exactly the
  `local-control-bus` design already sitting in this repo's history — the one I
  refused to extend without a **local, human-approval gate** on every execution
  (see `feat/local-computer-control`, PR #11, never merged, precisely because it
  lacked that gate). If you want ChatGPT to actually drive `colima`/`kind` here,
  that gate is the missing piece, not colima/kind access itself — colima and
  kind are already installed and usable locally; the open question is whether
  anything can safely relay requests to them without becoming an unattended
  remote-actuation daemon.

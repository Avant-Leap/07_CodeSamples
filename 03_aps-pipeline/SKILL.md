---
name: aps-pipeline-config
description: Configure an APS-connected MCP pipeline across Data Management, Model Derivative and Design Automation. Use when joining APS services behind one agent surface, or when scoping auth, polling, engine versions and Activity definitions before writing code.
---

# The APS pipeline

**LO3 · Handout §5.** Each of these three APIs is easy alone. **Joining them** is where real projects
fall over. This sample is a wiring diagram, not a server design: what must exist, per leg, before code
is worth writing.

## One workflow, not three services

```
model_get_metadata  →  model_export_derivative  →  automation_create_workitem  →  job_get_status
   (Data Mgmt)            (Model Derivative)          (Design Automation)           (all of them)
```

The first leg's identifier is what the second translates; the second's derivative is what the third
consumes. **Split these into three servers and the agent carries the handoff** — three chances to drop
it, and no single audit record of what happened.

| Leg | Scope | Tool |
|---|---|---|
| Data Management | `data:read` | `model_get_metadata` |
| Model Derivative | `data:read data:write data:create` | `model_export_derivative` |
| Design Automation | `code:all bucket:create` | `automation_create_workitem` |

Scopes are **per leg**, never one blanket grant. Only the automation leg gets `code:all`, because that
scope means "run my code on your machines" and no other leg has any business holding it.

## Run it

```bash
python ../00_shared-scaffold/host_python/server.py . p3-cloud-chain
python ../00_shared-scaffold/host_python/smoke.py
python ../00_shared-scaffold/validate.py .
cp .env.example .env        # shapes only; the sample never reads them
```

No credentials and no network — the calls are faked so it runs anywhere. The **shape** is what is real.

## Config that is measured, not defaulted

**`poll-intervals.json`** — a poll interval and TTL **per job type**, each carrying the sample count and
p95 it came from. TTL is the 95th percentile of real runs, never the mean. Too aggressive burns rate
limit; too slow and a twenty-second translation reports back in two minutes.

**`engine-versions.json`** — an enum, because a model will confidently invent a plausible engine version
that does not exist.

**`activities/*.json`** — the rule that matters most: **a tool exposes an Activity, never a job body.**
The moment an agent can compose engine, bundle and command line freely, you have shipped a remote code
execution endpoint with a friendly name.

**`endpoints.json`** — every external domain you touch. The Marketplace manifest demands the same list,
so writing it here means writing it once.

## The lesson to keep: long work returns a handle

Blocking a `tools/call` on a translation has been wrong by specification since the 2026-07-28 revision,
and it is also how the client times out and retries a job you already started.

Return `taskId` + `ttlMs` + `pollIntervalMs`. And when a task outlives its TTL, say **`expired`** as a
named result — not a failure. A task that quietly disappears is indistinguishable from one that failed,
and the agent's correct next action differs between the two.

## The retry that runs it twice — both halves

Most people do only the second half.

1. **Bound every internal wait** and return a typed `TIMEOUT` with `retryable: true`. An unbounded wait
   *guarantees* the client-side timeout that causes the retry.
2. **Require a caller-supplied key** on every create tool, derived from **intent** — project, source
   version, activity alias. Never random.

> ⚠️ This failure analysis is **ours**, not a documented pattern. SSE resumability was removed in the
> 2026-07-28 revision, so a dropped stream is re-issued as a brand-new request and your server cannot
> tell it from a first attempt.

## What to change when you make it real

1. **Every handler** — replace the fakes with APS calls. Keep the task-handle shape and the named
   `expired` status.
2. **Token store** — `APS_TOKEN_STORE` is a placeholder. Not the process environment, and not a file
   beside the code.
3. **`ACTIVITIES`** — publish real Activities and reference them by alias. Never accept a job body.

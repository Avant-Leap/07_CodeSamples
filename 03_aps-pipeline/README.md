# 03 · The APS pipeline — configuration, not architecture

> **LO3** — an APS-connected MCP pipeline sequencing Model Derivative, Data Management and Design
> Automation. **Handout §5.**

Each of these three APIs is easy alone. Joining them is where real projects fall over. This is not a
server design — it is a **wiring diagram**: what must exist, per leg, before code is worth writing.

## What is here

```
tools/       four tool definitions
manifests/   p3-cloud-chain.json
config/      endpoints.json · poll-intervals.json · engine-versions.json · activities/*.json
```

Check it: `python ../00_shared-scaffold/validate.py .`

## One workflow, not three services

The first leg's identifier is what the second translates; the second's derivative is what the third
consumes. **Split them into separate servers and the agent carries the handoff** — three chances to
drop it.

| Leg | Scope | Tool |
|---|---|---|
| Data Management | `data:read` | `model_get_metadata` |
| Model Derivative | `data:write` `data:create` | `model_export_derivative` |
| Design Automation | `code:all` `bucket:create` | `automation_create_workitem` |

**CREATE is in that third name deliberately**, because the call is not safely repeatable. A name that
hides its side effect is indefensible when idempotency is the argument three sections later.

## Config that is measured, not defaulted

**`poll-intervals.json`** carries a poll interval and TTL **per job type**, with the sample count and
p95 they came from. TTL is the 95th percentile of real runs, never the mean — a task that quietly
disappears is indistinguishable from one that failed.

**`engine-versions.json`** is an enum, because a model will confidently invent a plausible engine
version that does not exist.

**`activities/*.json`** is the rule that matters most: **a tool exposes an Activity, never a job
body.** The moment an agent can compose one freely — engine, bundle, command line — you have shipped a
remote code execution endpoint with a friendly name.

**`endpoints.json`** is every external domain you touch. The Marketplace manifest demands the same
list, so keeping it here means you write it once.

## The retry that runs it twice

Two halves, and most people only do the second. **Bound every internal wait** and return a typed
`TIMEOUT` with `retryable: true` — an unbounded wait *guarantees* the client timeout that causes the
retry. **Then** require a caller-supplied key on every create tool.

Derive the key from **intent** — project, source file version, activity alias. A key the model
generates randomly is worse than no key, because it creates the appearance of protection.

> ⚠️ That failure analysis is **ours**, not a documented pattern. Resumability was removed in the
> 2026-07-28 revision, so a dropped stream is re-issued as a brand-new request and your server cannot
> tell it from a first attempt.

## Not here

The server host and live credentials. These are the rails.

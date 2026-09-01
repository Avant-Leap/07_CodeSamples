---
name: mcp-scaffold
description: Scaffold a new MCP server from the AS2698 contracts — process manifest, tool definitions, envelope and validator. Use when starting any MCP server, or when an existing server needs a tool surface that will survive review.
---

# Scaffolding an MCP server

Drop this folder into `.claude/skills/mcp-scaffold/` and it becomes usable directly.
Everything below is the sequence — do it in this order, because each step constrains the next.

## 1. Write the process manifest before the tools

A manifest is one **process**, not one product. If you cannot fill in `trigger`, `owner` and
`acceptanceTest` in one sentence each, you do not yet have a process — you have a folder of API calls,
and no amount of tool design will fix that.

```
manifests/<process-id>.json     validated by contracts/process.schema.json
```

The `acceptanceTest` array is the part people skip and the part that pays. Write down how a **reviewer**
confirms the work is done without reading logs. If you cannot answer that, the server is not
finishable.

## 2. Stay under six tools, and read the overflow as a diagnosis

`maxTools` has `"maximum": 6` in the schema, so the ceiling is not advisory — a manifest that breaks it
fails validation and the host refuses to start.

The ceiling is **per surface, not per project**. It counts what the agent can see *at the moment it
acts*. A product with forty tools is fine; a *process* that needs more than six is almost always two
processes sharing one manifest. Split it and both halves get better.

## 3. Write three sentences per tool, and mean the third

```
tools/<tool_name>.json          validated by contracts/tool.schema.json
```

`what` · `when` · `whenNot`. The third is the one people leave out and the only one that stops a tool
being chosen for a job it cannot do. Add `requires` for preconditions and `onPartialSuccess` for any
tool that can half-succeed.

Name the side effect in the name. `automation_create_workitem` says `create` out loud, because a name
that hides its blast radius is indefensible the first time someone asks what the agent did.

## 4. Return the envelope on both paths

Success and failure are both **data**. Error codes come from a closed enum in
`contracts/envelope.schema.json` — inventing a local code means an agent can no longer reason about
failure across a chain of servers, which is the entire reason the enum is closed.

## 5. Pair every write with a preview

Declare it in the manifest's `writes` array: the write tool, its `previewTool`, its `blastRadius` in
plain words, and whether it needs an idempotency key. The host enforces the pair; no handler can forget
it, and there is no convenience bypass.

Derive `requestKey` from **intent** — project, version, activity alias. A random key is worse than no
key, because it looks like protection and is not.

## 6. Run the validator, and watch it fail first

```bash
python validate.py ../01_revit-addin-surface      # your folder
python validate.py --demo                         # deliberately broken fixtures
```

Run `--demo` once before you trust a green run. A gate that has never rejected anything is decoration.

## 7. Run the host

The Python host in `host_python/` runs any folder built to these contracts, unchanged:

```bash
python host_python/server.py ../02_dynamo-promotion p2-graph-catalogue
python host_python/smoke.py                        # the failure-path test
```

The C# host in `../01_revit-addin-surface/host_csharp/` enforces the identical rails in .NET 8. Read
them side by side — the contracts are the same, so neither host knows what it is running.

## The rails the host enforces for you

| Rail | Where it fires |
|---|---|
| Six-tool ceiling | Startup. The server refuses to boot, not the call. |
| Manifest selects tools | Tools on disk but unlisted stay invisible. |
| Envelope on both paths | Every return, including uncaught exceptions. |
| Preview → confirm | Every non-read tool. Tokens are single use. |
| Idempotency | Every `create` tool. A repeated key returns the stored envelope. |
| Bounded waits | Every call, against the tool's own `timeoutMs`. |
| Append-only audit | Written before the write tool returns. |

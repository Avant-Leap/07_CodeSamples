---
name: dynamo-graph-promotion
description: Turn an ageing Dynamo graph library into an MCP surface, or promote graphs to add-ins or Python nodes. Use when deciding what to do with graphs that still work but nobody maintains, especially where add-in installation is restricted.
---

# Promoting Dynamo work

**LO2 · Handout §4.** Dynamo 4.0 ships DynamoMCP and the Autodesk Assistant, so the question is no
longer *whether* graphs get an agent surface. It is what happens to the graphs you already have.

## The two routes, and the discriminator

```
old graph  →  Path A: compile to a Revit add-in     →  MCP surface
           →  Path B: wrap in a Python custom node  →  MCP surface  →  (later, an add-in)
```

The choice is **deployment governance, not skill.** Path A is cleaner and needs installation rights on
every machine. Path B ships inside a package where add-ins are restricted, and keeps the promotion
route open. A team that picks A in a locked-down firm ships nothing at all.

Both routes end at the same surface, which is why the tool contracts here do not care which one you
took.

## The catalogue is the product

Three tools, and the middle one carries the weight:

| Tool | Effect | Notes |
|---|---|---|
| `list_dynamo_packages` | read | What exists, and when it last ran on a real project |
| `get_graph_outputs` | read | Inputs, preconditions, failure modes — and the confirm token |
| `run_dynamo_graph` | update | Refuses without that token |

The `validated` field — *the last real project this ran on* — is what earns internal trust. A catalogue
without it is a folder with better formatting.

## Run it

```bash
python ../00_shared-scaffold/host_python/server.py . p2-graph-catalogue
python ../00_shared-scaffold/host_python/smoke.py
python ../00_shared-scaffold/validate.py .
```

Same host binary as `03_aps-pipeline`. Nothing in it knows about Dynamo.

## The lesson to keep: partial success is not failure

A graph that renumbers 42 rooms and skips 3 has **not failed**. Naive wrappers raise, and an agent that
catches an exception can tell the user nothing useful.

`run_dynamo_graph` returns the count that worked *and* the list that did not, each with a reason:

```
42 renumbered · 3 skipped — Room 1204 unplaced, Room 1207 unplaced, Room 1310 read-only workset
```

That is a sentence an agent can say to a person. An exception is not. Every tool that can half-succeed
needs `onPartialSuccess` in its description and a `warnings` array in its response.

## What to change when you make it real

1. **`CATALOGUE`** — replace with your catalogue file. Keep `validated`, `preconditions` and
   `failure_modes`; those three fields are why the agent picks correctly.
2. **`run_dynamo_graph`** — invoke through Dynamo's journal/player API or your add-in bridge. Keep the
   `changed` / `skipped` shape untouched.
3. **`_documentOpen`** — a real bridge answers this. Return `NO_ACTIVE_DOCUMENT` rather than guessing;
   guessing is how an agent corrupts something.

## Before you promote a graph, check it is worth promoting

A graph nobody has run in two years does not become valuable by being wrapped. Score it with
`../04_selection-framework/score.py` first. Promotion is the reward for a graph that survives the six
questions — not the rescue for one that does not.

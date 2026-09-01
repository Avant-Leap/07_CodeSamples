# 02 · Dynamo — wrap what works, promote what has earned it

> **LO2** — a Dynamo MCP server in Python that wraps existing scripts as AI-callable tools.
> **Handout §4.**

Dynamo 4.0 ships graph authoring in the box, so that job is taken. The question left is the one
Dynamo cannot ask about itself: **should this still be a graph at all?** Most should. A few have
earned promotion — and **which route you take is decided by what you are allowed to deploy, not by
what you can build.**

## What is here

```
tools/       three tool definitions
manifests/   p2-graph-catalogue.json
config/      scaffold.config.json — the six promotion layers, and which are generated
```

Check it: `python ../00_shared-scaffold/validate.py .`

## The two routes

| | Path A — compile | Path B — Python node |
|---|---|---|
| Deploys as | software: signed, installed | **content: a package, like a graph** |
| Gate it must pass | IT policy, signing, review board | the shared library location |
| Typing | real, at compile time | enforced at the tool schema instead |
| Time to first run | a morning to build, a quarter to approve | a morning, and it runs |

**Path B is not the compromise path.** For a large number of firms it is the only path, and a pattern
that ignores it is a pattern for consultancies rather than for companies.

And the migration is invisible from above: when B becomes A, the tool names, schemas, manifest and
envelope do not change — because none of them were ever defined by the implementation.

## The six promotion layers

`config/scaffold.config.json` names them. Two come from the graph, one is translated, and **three are
things a graph structurally cannot carry**:

- **envelope** — graphs half-succeed by design and report it in a warning nobody reads
- **guard** — a graph run by a human *has* a human as its guard; remove them and you must replace them
- **proof** — if you cannot write the acceptance test, the graph has not earned promotion, whatever
  its run count says

That last one is deliberately marked `generated: false`.

## Partial success is what wrappers get wrong

`run_dynamo_graph` returns the count that worked **and** the list that did not, with reasons.
"42 renumbered, 3 skipped — unplaced rooms" is useful to an agent; an exception is not. The tool
description says the warnings array must be shown to the user, because otherwise it gets swallowed.

## Not here

The Python host and the Dynamo invocation layer. These are the rails.

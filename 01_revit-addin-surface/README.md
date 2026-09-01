# 01 · The Revit add-in surface — C# .NET 8

> **LO1** — a production MCP server that exposes Revit add-in build and deployment operations as
> AI-callable tools. **Handout §3.**

**The add-in is the subject, not the output.** Build the capability into Revit first; expose it
second; choose the client last. A tool you cannot already perform by hand is not a tool — it is an
experiment with a schema attached.

## What is here

```
tools/       four tool definitions, validating against
             ../00_shared-scaffold/contracts/tool.schema.json
manifests/   p8-addin-release-gate.json — the process, ≤6 tools, with its acceptance test
config/      validation-rules.json · version-matrix.json · audit-record.schema.json
```

Check it: `python ../00_shared-scaffold/validate.py .`

## The four tools

| Tool | Side effect | Blast radius |
|---|---|---|
| `validate_addin` | read | **None.** Ship this one first |
| `check_store_requirements` | read | **None.** Its token authorises the write |
| `build_all_versions` | update | Overwrites build output. Reversible |
| `package_release` | **create** | Writes installer, bundle and one audit record. Needs a `requestKey` |

Two of four cannot change anything, and one of those two is the one worth building first.

## The rules are data, not code

`config/validation-rules.json` holds the four causes that got real submissions rejected — version
format, entitlement mismatch, installer privilege, and a privacy-policy URL that must resolve. The
last one failed because of **a missing dash**, and cost a full review cycle.

Nobody ever wrote a requirement saying "the privacy URL must resolve." It was learned by losing a
review — and what forced all four to be written down was trying to describe the tool. **You cannot
write "when to use it, and when not to" for a validator without enumerating what it validates.**

Because they are data, changing a rule is a pull request against a JSON file that somebody who does
not write C# can read and review.

## What the audit record deliberately omits

`config/audit-record.schema.json` records process, tool, host, subject, count and timestamp — and
**not** which agent or model made the call. The protocol authenticates the host, not the agent, so
any agent identity would be an inference. Recording a guess is worse than recording nothing: it looks
like provenance in an audit review and is not.

## Auth — where "it is local so it is fine" breaks

A bridge listening on a fixed local port is reachable by anything on that machine, including a
browser tab. Once write tools exist, **require a bearer token checked in middleware before any write
tool runs.** Local is not the same as trusted.

## Not here

The C# host itself. These are the rails — the contracts, the process definition and the rule data.
Wire them to your own build pipeline; the point is that the pipeline already exists, and this exposes
it rather than reinventing it.

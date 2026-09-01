---
name: revit-addin-release-gate
description: Build a C# .NET 8 MCP server exposing Revit add-in build, validation, packaging and store-submission checks. Use when putting an add-in release pipeline behind an assistant, or when submissions keep getting rejected for the same avoidable reasons.
---

# The add-in release gate

**LO1 · Handout §3.** A production MCP server in C# .NET 8, exposing add-in **build and deployment**
operations. Not a Revit-API server — the add-in is the *subject*, not the output.

## The direction of travel

```
deterministic pattern  →  Revit add-in  →  MCP surface  →  client
```

You do not ask an assistant to write Revit code. You write the add-in from a pattern you can defend,
then expose **operating** that add-in as tools. What the agent orchestrates is release engineering,
which is repetitive, reversible and scriptable — the three properties that make automation worth
building.

## The four tools, and why exactly four

| Tool | Effect | Preview partner |
|---|---|---|
| `validate_addin` | read | — (it *is* a preview) |
| `build_all_versions` | update | `validate_addin` |
| `check_store_requirements` | read | — (it *is* a preview) |
| `package_release` | create | `check_store_requirements` |

Two reads and two writes, paired. The reads are not conveniences: each one is the authorisation step
for the write beside it, which is why the surface does not need a fifth tool to "check before doing".

## Run it

```bash
cd host_csharp
dotnet run -- smoke ..                  # the failure-path script, no client needed
dotnet run -- serve .. p8-addin-release-gate
python ../00_shared-scaffold/validate.py ..
```

`clients/mcp.json` is the client wiring — replace `<ABSOLUTE>` and drop it into your MCP config.

## Rules that live in data, not in code

`config/validation-rules.json` holds the four causes that got real submissions rejected. They are
**data on purpose**: adding a rule is a pull request against a JSON file that a release manager who
does not write C# can read and approve. A gate people can amend is a gate they maintain rather than
route around.

`config/version-matrix.json` is an explicit **list**, never a range expression. The framework changes
at 2025 (`net48` → `net8.0-windows`), and a range hides that. Never narrow the list in a minor release
— someone is on the version you dropped.

## What to change when you make it real

1. **`Handlers.FakeCheck`** — replace with the actual file reads and the HTTP HEAD. Everything around
   it already works.
2. **`BuildAllVersions`** — shell out to `dotnet build` per version. Keep the per-version result array;
   do not collapse it to a boolean.
3. **`PackageRelease`** — call your installer toolchain. Keep the blocking-findings refusal exactly
   where it is.
4. **Audit sink** — `audit.log` is a file here. Point it at something append-only that the server
   cannot rewrite.

Do **not** change: the envelope, the error enum, the preview→confirm pairing, or the startup ceiling
check. Those are the parts that survive review.

## The lesson to keep

`package_release` refuses while validation has blocking findings — with a valid token, a valid request
key, and everything the caller was told to bring. **The refusal is in the host, not in the prompt.**
A rule stated in a prompt is a preference; a rule enforced in the host is a rule.

On the sample product it always refuses. That is the demonstration, not a bug.

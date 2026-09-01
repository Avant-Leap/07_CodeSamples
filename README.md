# AS2698 — Code Samples

**Four folders. One per learning objective.** These are the artefacts an attendee takes home,
and — since the AU DevCon reference repository is staying private — **they are the only code this
session ships.** That raises the bar: what is here has to stand on its own, without the earlier class.

> **Status:** 🟢 **Runnable, 31 August 2026.** All four folders run, and all four are checked by a
> validator that can fail. Nothing here is a product, and nothing here is for sale.

---

## Run everything in four commands

No install, no packages. Python 3.11+ for three of them, the .NET 8 SDK for the C# one.

```bash
python 00_shared-scaffold/validate.py            # contracts, all four folders
python 00_shared-scaffold/host_python/smoke.py   # 02 and 03 over real stdio JSON-RPC
cd 01_revit-addin-surface/host_csharp && dotnet run -- smoke ..
python 04_selection-framework/score.py 04_selection-framework/candidates.example.csv
```

Each smoke run is a **failure-path** test. Almost every line it prints is a guard turning something
down, because a guard that has never refused anything is decoration.

## Every folder carries the same three documents

| File | For |
|---|---|
| `SKILL.md` | **Using it.** Frontmatter included — drop the folder into `.claude/skills/` and it works as a skill. |
| `ARTIFACTS.md` | **Finding your way around.** Every file, what kind it is, and whether to copy or replace it. |
| `README.md` | **The argument.** Why the design is what it is, including what failed. |

---

## The rule that applies to every folder

This session carries **AIA LU credit**, which means everything published under it is instructional.

| Do | Do not |
|---|---|
| Show **how a pattern works**, so someone can rebuild it | Name or promote a commercial product |
| Use generic, descriptive component names | Use internal product names |
| Explain the reasoning, including what failed | Imply a purchase path of any kind |
| Ship something runnable | Ship a demo that only works on our machines |

**Naming convention for anything that maps to real internal work:** describe the *role*, not the
product. A downstream composer is `composer`, not a brand. A parameter service is `parameter-service`.
If a reader can rebuild it from the description, the objective is met.

---

## The folders

**Read [`00_shared-scaffold/`](00_shared-scaffold/) first.** It holds the contracts, schemas and
checklists the other four inherit, so each sample only has to explain what is different about itself.
Every folder carries its own `rules/` (prose — how you may build) and `config/` (data — what the
contract is); handout §9.2 lists the recommended default set per folder.

| # | Folder | Learning objective | What it proves |
|---|---|---|---|
| **0** | [`00_shared-scaffold/`](00_shared-scaffold/) | **all four** | The envelope, the tool contract, the process manifest, preview→confirm, and the tier definitions |
| 1 | [`01_revit-addin-surface/`](01_revit-addin-surface/) | **LO1** — a production MCP server in C# .NET 8 exposing Revit add-in build and deployment as AI-callable tools | Manifest-scoped tool surfaces, the three deterministic pillars, preview→confirm, and the composition boundary |
| 2 | [`02_dynamo-promotion/`](02_dynamo-promotion/) | **LO2** — a Dynamo MCP server in Python that wraps existing scripts as AI-callable tools | The catalog, the six-layer scaffold, and when a graph has earned promotion |
| 3 | [`03_aps-pipeline/`](03_aps-pipeline/) | **LO3** — an APS-connected MCP pipeline sequencing Model Derivative, Data Management and Design Automation | Auth posture, the access model, packaging automations, tasks, and idempotency |
| 4 | [`04_selection-framework/`](04_selection-framework/) | **LO4** — a server selection framework for identifying the highest-priority Autodesk workflows | The six questions as something you *run*, not something you read |

---

## Shared conventions — read this before opening any folder

Every sample in all four folders obeys the same three contracts. They are what make the samples
comparable, and they are the cheapest thing to get right on day one.

### 1 · The return envelope

Every tool, every language, both paths:

```jsonc
{ "ok": true,  "data": { … } }
{ "ok": false, "code": "NOT_FOUND", "message": "…", "detail": { … } }
```

**Error codes are a closed enum.** Adding one is a specification change, not a local decision. The
shared list lives in each folder's `contracts/` directory and is identical across all four.

### 2 · Preview, then confirm

Any tool that writes returns a preview first. Execution takes a second, explicit call carrying the
preview token. **No exceptions, no convenience bypass.** One bypass puts a hole in the audit trail
that nobody remembers later.

### 3 · Six tools or fewer, per process

If a surface needs more, the *scope* is wrong — not the budget. Decompose and re-run the six
questions on each half.

---

## What "done" means for a sample

A sample in this repository is finished when all seven hold:

1. It runs from a clean clone with a documented setup, on a machine that is not ours.
2. Every tool description has all three sentences: what it does, when to use it, **when not to**.
3. It returns the standard envelope on success *and* failure.
4. It has a test asserting the **failure** path, not only the happy one.
5. Its token cost for one successful run is **measured**, in the manifest's `tokenBudget` —
   `toolSurfaceTokens`, `medianRunTokens`, `medianTurns`. The validator fails a manifest without it.
6. Its `config/` holds every rule that governs it, as **data**, not as code.
7. Its `SKILL.md` names the functions to replace, so a reader can tell scaffolding from stubs without
   reading the code first.

Item 5 is the one that is new, and it is the one this session argues matters most.

---

## Open

| # | Question | Owner |
|---|---|---|
| ~~1~~ | ~~Scope per folder~~ — **settled: all four are runnable.** 01 is a C# .NET 8 host, 02 and 03 share one Python host, 04 is a script. The external work (Revit, Dynamo, APS) is faked so every folder runs on any machine; `SKILL.md` in each says exactly what to replace | — |
| ~~2~~ | ~~Where these are published~~ — **settled: this repository, public.** `github.com/Avant-Leap/07_CodeSamples` | — |
| ~~3~~ | ~~Licence~~ — **settled: MIT for the whole repository.** See below | — |
| 4 | Which folder carries the recorded 40-second demo clip | Enrique |

---

## Licence

**MIT.** See [`LICENSE`](LICENSE).

Chosen so you can copy `00_shared-scaffold/contracts/` straight into a commercial add-in without
starting a legal conversation. That is the point of publishing this at all — the envelope and the
process manifest are only worth anything if they spread, and a copyleft licence on a schema file is a
landmine for anyone shipping a product.

Two things the licence does not cover, stated plainly:

- **Trademarks.** "AvantLeap", "Autodesk", "Revit", "Dynamo" and product names generally are not
  licensed here. Reuse the code; do not imply an endorsement.
- **Warranty.** Read the AS-IS clause before wiring any of this into a real release pipeline. These
  are teaching samples with the external work deliberately faked. What is real is the *shape*.

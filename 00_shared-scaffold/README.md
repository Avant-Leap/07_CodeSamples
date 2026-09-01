# 00 · The shared scaffold

> **What makes the four learning objectives keepable rather than merely described.**
> **Status:** 🟡 scaffolded 24 August 2026 · contracts defined, implementations pending
> **Handout section:** §9.1–9.3

---

## Why this folder exists

Four samples written independently drift into four error-handling styles, four manifest shapes and
four different ideas of what "finished" means. A reader who studies two of them learns
contradictions.

So the contracts live here once, and the four sample folders inherit them. **Read this folder first;
each sample then only has to explain what is different about itself.**

---

## Structure

```
00_shared-scaffold/
├── README.md
├── rules/                     ← prose. How you are allowed to build
│   ├── tool-design-checklist.md
│   ├── server-checklist.md
│   ├── client-checklist.md
│   ├── tier-definitions.md
│   ├── fixes-policy.md
│   └── git-safety.md
├── config/                    ← data. What the contracts actually are
│   ├── tool.schema.json
│   ├── resource.schema.json
│   ├── process.schema.json
│   ├── envelope.json
│   └── client-config.example.json
└── templates/
    ├── csharp/                ← stdio server skeleton, .NET 8
    ├── python/                ← stdio server skeleton
    └── node/                  ← stdio server skeleton
```

---

## The rule that decides where something goes

> **Rules are prose. Configs are data.**

If changing a rule means editing code, it was a config in disguise. Version matrices, validation
checks, engine lists and poll intervals are all data for exactly this reason — a standards change
should be a pull request against a JSON file that a non-developer can read and review.

**Every rules file ends with what goes wrong when it is ignored.** A rule that only describes the
happy path gets skipped under pressure. The failure sentence is what makes somebody follow it at 6pm
on a Friday.

---

## The four contracts every sample inherits

### 1 · The return envelope — `config/envelope.json`

```jsonc
{ "ok": true,  "data": { … } }
{ "ok": false, "code": "NOT_FOUND", "message": "…", "detail": { … } }
```

**Error codes are a closed enum.** Adding one is a specification change, not a local decision. The
moment each server invents its own codes, an agent can no longer reason about failure across a chain
— and chains are the whole point.

### 2 · The tool contract — `config/tool.schema.json`

`name` (snake_case, verb_noun, imperative) · `description` (three sentences: what it does, when to use
it, **when not to**) · `inputSchema` with typed properties, `enum` wherever the value set is closed,
and an explicit `required` array.

**Enums are not a nicety.** A model will confidently produce a plausible value that does not exist.
The schema is the cheapest place to catch that — before the call, not after.

### 3 · The process manifest — `config/process.schema.json`

The contract that keeps a large function portfolio from becoming a large tool surface. A server does
not expose functions; it loads **one manifest at a time**, and the manifest selects which functions
become visible tools.

```jsonc
{
  "id": "p8-addin-release-gate",   // stable, kebab-case, never reused
  "version": "1.0.0",
  "name": "Add-in Release Gate",
  "description": "…",

  // what makes a manifest a deliverable rather than a config file
  "trigger": "A product is ready for submission.",
  "owner": "Release engineer",          // the ROLE that presses the button
  "deliverable": { "kind": "report+artifact", "artifacts": ["…"] },
  "acceptanceTest": [
    "Stated so a non-technical reviewer can confirm it, without knowing how it was produced."
  ],

  "maxTools": 6,
  "tools": [ "validate_addin", "…" ],
  "services": [ "rule-service" ]       // called BY tools. Invisible to the agent
}
```

**Two fields carry more weight than the rest.**

`acceptanceTest` is the line everybody leaves blank. If you cannot state what "done and correct" looks
like to someone who does not understand how the result was produced, you do not have a process — you
have a demo.

`services` is what stops the tool count climbing. A shared capability is declared here and is
**invisible to the agent**. An agent that can call a service directly is holding a parts bin rather
than running a process.

> **Infrastructure has no tools. It has a contract.** That sentence resolves the recurring argument
> about how many tools a shared component "has". The question is malformed.

### 4 · Preview → confirm — `rules/tool-design-checklist.md`

Any tool that writes returns a preview: the set of changes it *would* make, and nothing else.
Execution requires a second, explicit call carrying the preview's token. **No exceptions and no
convenience bypass for internal use** — one bypass puts a hole in the audit trail and nobody
remembers where it is.

---

## Tiers — `rules/tier-definitions.md`

Not every sample needs to be production-grade, and pretending otherwise is how nothing ships. Four
tiers, and each one is explicit about what it is allowed to skip:

| Tier | Must have | May skip |
|---|---|---|
| **PoC** | It runs. Envelope on both paths | Auth, audit, tests, packaging |
| **Pilot** | Failure-path test, real inputs, documented setup | Multi-tenancy, rate limiting, health endpoint |
| **Internal product** | Preview→confirm, audit, named owner, acceptance test | Marketplace submission artefacts |
| **Production** | Everything in handout §6.1, plus a measured token budget | Nothing |

**State the tier in every README.** A PoC labelled as one is honest; a PoC labelled as a product is
how a pilot becomes an unsupported thing somebody depends on.

---

## The definition of done, inherited by all four

1. It runs from a clean clone with documented setup, on a machine that is not ours.
2. Every tool description has all three sentences.
3. It returns the standard envelope on success *and* failure.
4. It has a test asserting the **failure** path, not only the happy one.
5. Its token cost for one successful run is measured and written in the README.
6. Its `rules/` and `config/` directories are complete. **A rule that exists only in someone's head is
   not shipped.**

---

## Open

| # | Question | Owner |
|---|---|---|
| 1 | Do the three language templates all ship, or only the two the samples use? | Enrique |
| 2 | Is the closed error enum final, or does it grow once during the build? | Enrique |
| 3 | Which tier is each of the four samples aiming at? Current assumption: **Pilot** for all four | Enrique |

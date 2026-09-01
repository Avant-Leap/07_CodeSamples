---
name: mcp-workflow-selection
description: Score candidate workflows against six questions to decide which deserves an MCP server first. Use before building anything — when there is a list of possible automations and no agreed order, or when a proposed server needs a defensible go/no-go.
---

# Which server to build first

**LO4 · Handout §2 and §6.** The other three folders show *how* to build. This one answers the question
that comes first and gets skipped: **which one deserves the effort.**

It takes an afternoon and it does not scale with the size of your firm. A two-person practice gets the
same answer a two-hundred-person one does; what changes is how many candidates you are choosing
between, not whether you get to choose.

## Run it

```bash
python score.py candidates.example.csv            # the ranked list
python score.py candidates.example.csv --explain  # why each question passed or failed
python score.py --blank > my-candidates.csv       # start your own
```

Standard library only. No install.

## The six questions

1. **Does it already exist as a script or pipeline?** If not, you are inventing the workflow and
   validating it at the same time, and you will not be able to tell which half is broken.
2. **Is the failure reversible?** Start where a wrong answer costs a rework, not a rebuild.
3. **Does a human wait at a boundary?** The waiting is the value. A question a person answers
   themselves in thirty seconds is not a workflow.
4. **Repetitions × people.** The only ROI calculation that survives contact with reality. The floor is
   20 runs a month across all users — tune `FREQUENCY_FLOOR` to your own economics.
5. **Can the agent see six tools or fewer at the moment it acts?** Note the wording: *not* "does the
   server have six tools". A large catalogue is fine if only one process is loaded.
6. **Would any company ship this?** If a vendor plausibly would, you are building something that
   becomes free. If nobody would — your pipeline, your standards, your scripts — it is yours
   permanently.

## Three things the script encodes that the questions alone do not

**Question 6 is inverted.** A vendor *would* ship it is a **fail for you**. The CSV column is
`vendor_would_ship`, and `y` costs you the point. This trips almost everyone the first time.

**Failing question 5 is a diagnosis, not a rejection.** It returns `DECOMPOSE`, because going over six
means the scope is wrong, not the budget. Split it and re-score each half — both halves usually score
better than the whole did.

**Blast radius breaks ties.** Several candidates clear all six. Among them, the smallest blast radius
wins, so exactly one comes back `BUILD FIRST`. A framework that returns four winners has not made a
decision.

## Fill in your own candidates

```
workflow,exists,reversible,human_waits,per_month,people,six_tools,vendor_would_ship,blast_radius,notes
```

`y`/`n` for the flags, integers for `per_month` and `people`, and `none`/`bounded`/`high` for
`blast_radius`. Be honest about `vendor_would_ship` — optimism there is what gets a year of work
retired by somebody else's release note.

## Re-run it quarterly

Question 6 is the only answer that **changes while you sleep.** Dynamo 4.0 shipping DynamoMCP and the
Autodesk Assistant retired the graph-authoring answer between one AU and the next; graph *promotion*
survived, because nobody else was going to do it.

Five of the six answers are facts about your firm and move slowly. The sixth is a fact about somebody
else's roadmap. Score once and you are working from a snapshot that has already expired.

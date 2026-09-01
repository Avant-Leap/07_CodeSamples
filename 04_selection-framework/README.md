# 04 · The selection framework — six questions you run, not read

> **Learning objective 4** — apply a server selection framework to identify the highest-priority
> Autodesk workflows for MCP.
> **Handout section:** §2 and §6 · **Status:** ✅ runnable

---

## What is in here

| File | |
|---|---|
| `score.py` | **Runnable.** Standard library only — no install, no dependencies |
| `candidates.example.csv` | Nine worked candidates: four that clear everything, one that only needs decomposing, three that fail on question 6, one that is simply not ready |

```
python score.py candidates.example.csv            # the ranked list
python score.py candidates.example.csv --explain  # why each question passed or failed
python score.py --blank > my-candidates.csv       # start your own
```

The other three folders show *how* to build. This one answers the question that comes first and gets
skipped: **which one deserves the effort.** It takes an afternoon and it does not scale with the size
of your firm — a two-person practice gets the same answer a two-hundred-person one does. What changes
is how many candidates you choose between, not whether you get to choose.

---

## The six questions

**1 · Does it already exist as a script or a pipeline?**
If it does, you are exposing something already validated with a known failure mode. If not, you are
inventing the workflow and validating it at the same time, and you will not be able to tell which
half is broken. *Fail → build the script first.*

**2 · Is the failure reversible?**
Start where a wrong answer costs a rework, not a rebuild. *Fail → pick something else for server one.*

**3 · Does a human wait at a boundary?**
The waiting is the value. A query a person could answer themselves in thirty seconds is not a
workflow. *Fail → you are automating curiosity, not work.*

**4 · How often does it repeat × how many people?**
The only ROI calculation that survives contact with reality. `score.py` uses a floor of **20
repetitions per month across all users** — tune `FREQUENCY_FLOOR` to your own economics.

**5 · Can the agent see six tools or fewer at the moment it acts?**
Note the wording — not "does the server have six tools". A large catalogue is fine if only one
process is loaded. *Fail → the scope is wrong, not the budget. Decompose and re-score each half.*

**6 · Would any company ship this?**
If a vendor would plausibly ship it, you are building something that becomes free. If nobody would —
because it is your pipeline, your standards, your scripts — it is yours permanently.

---

## Two things the script encodes that the questions alone do not

**Question 6 is inverted, and it trips people.** A vendor *would* ship it is a **fail** for you. The
CSV column is `vendor_would_ship`, and `y` costs you the point.

**Passing all six is a shortlist, not an order.** Several workflows clear every question. The tiebreak
is `blast_radius` — `none`, `bounded` or `high`. Among candidates that qualify, start with the one
that can hurt least, because **the first server is the one you are still learning on.** That is why
the release pipeline outranks workflows with far higher usage.

---

## The printable sheet

```
Workflow: ______________________________________________

  1. Already exists as script/pipeline?      [ ] Y  [ ] N
  2. Failure reversible?                     [ ] Y  [ ] N
  3. Human waits at a boundary?              [ ] Y  [ ] N
     — who: ____________  how often: ____________
  4. Repetitions per month × people:         ______ × ______ = ______
  5. Agent sees ≤6 tools when it acts?       [ ] Y  [ ] N
     — name them: 1.__________ 2.__________ 3.__________
                  4.__________ 5.__________ 6.__________
  6. Would any company ship this?            [ ] Y — wait
                                             [ ] N — permanently yours

  Score: ___ / 6      Blast radius:  [ ] none  [ ] bounded  [ ] high

  Steps in the workflow today:      ______
  Steps after you subtract:         ______   ← if these are equal, stop
  Acceptance test — how a non-technical reviewer confirms it worked:
  _______________________________________________________________
```

**Below 5 of 6 is not your first server.**

> Two lines get skipped and both decide it. **The step count** — if you cannot remove steps you have
> wrapped a workflow rather than improved one, and added running cost for nothing. **The acceptance
> test** — if you cannot state what "done and correct" looks like to somebody who does not understand
> how it was produced, you have a demo.

---

## Question 6 is not hypothetical

Two of the most-starred community Revit MCP projects are archived. A well-regarded APS server was
archived and absorbed into the Autodesk org. Autodesk shipped its own Revit server into that space in
June 2026, and shipped graph authoring into Dynamo 4.0.

**The commodity desktop-bridge layer consolidated in about eighteen months.** That is what question 6
protects you from — and it is why one claim in this session's own abstract had to be retracted before
it was delivered.

> **Q6 is the only answer that changes while you sleep.** Re-run this quarterly, not once. The cost of
> re-running is an afternoon; the cost of not re-running is a year building something that arrived
> free.

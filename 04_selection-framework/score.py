"""
The six-question screen, as something you run.

Scores candidate workflows, ranks them, and says why — which is the part a
checklist cannot do. A framework that only describes itself is a checklist;
what you want from one is a sorted list.

No dependencies beyond the standard library, on purpose: this folder has to be
usable by somebody who does not write code.

    python score.py candidates.example.csv
    python score.py candidates.example.csv --explain
    python score.py --blank > my-candidates.csv

CSV columns — see candidates.example.csv:
    workflow, exists, reversible, human_waits, per_month, people,
    six_tools, vendor_would_ship, blast_radius, notes
blast_radius is none | bounded | high — it breaks ties among candidates that
clear all six, because the first server is the one you are still learning on.
Booleans accept y/n, yes/no, true/false, 1/0.
"""

import argparse
import csv
import sys
from pathlib import Path

QUESTIONS = [
    ("exists", "Already exists as a script or pipeline?",
     "You are exposing something already validated, with a failure mode you know.",
     "You are inventing the workflow and validating it at the same time, and you "
     "will not be able to tell which half is broken. Build the script first."),
    ("reversible", "Is the failure reversible?",
     "The worst case is that somebody runs it again.",
     "Your first write surface should not be one where a wrong answer costs a "
     "rebuild. Pick something else for server one."),
    ("human_waits", "Does a human wait at a boundary?",
     "The waiting is the value — that gap is what the agent removes.",
     "A query a person could answer themselves in thirty seconds is not a "
     "workflow. You are automating curiosity, not work."),
    ("frequency", "Does it repeat enough to repay a server?",
     "Frequency times people clears the bar.",
     "The maintenance will outlive the benefit."),
    ("six_tools", "Can the agent see six tools or fewer when it acts?",
     "The surface is small at the moment the model chooses.",
     "The SCOPE is wrong, not the tool budget. Decompose into two processes and "
     "re-score each — going over six is a diagnosis, not a rejection."),
    ("vendor_would_ship", "Would any company ship this?",
     "Nobody else will build it, so it is permanently yours.",
     "You are building something that becomes free in twelve months. Wait."),
]

# Question 4 is the only one that is not a straight yes/no on the sheet.
FREQUENCY_FLOOR = 20      # repetitions per month x people


def truthy(v):
    return str(v).strip().lower() in {"y", "yes", "true", "1", "t"}


def score_row(row):
    per_month = float(row.get("per_month") or 0)
    people = float(row.get("people") or 0)
    reps = per_month * people

    answers = {
        "exists": truthy(row.get("exists")),
        "reversible": truthy(row.get("reversible")),
        "human_waits": truthy(row.get("human_waits")),
        "frequency": reps >= FREQUENCY_FLOOR,
        "six_tools": truthy(row.get("six_tools")),
        # NOTE the inversion. A vendor shipping it is a FAIL for you.
        "vendor_would_ship": not truthy(row.get("vendor_would_ship")),
    }
    return answers, sum(answers.values()), reps


BLAST = {"none": 0, "bounded": 1, "high": 2}


def verdict(answers, total):
    if not answers["vendor_would_ship"]:
        return "WAIT", "Fails Q6 — somebody else is going to ship this."
    if not answers["six_tools"]:
        return "DECOMPOSE", "Fails Q5 only. Split it and re-score each half."
    if total >= 5:
        return "BUILD", ("Clears every question." if total == 6
                         else "Clears five of six. Fix the gap before you start.")
    return "NOT YET", f"Scores {total}/6. Below five is not your first server."


def pick_first(scored):
    """Exactly one candidate is FIRST, and passing everything does not decide it.

    Several workflows can clear all six — that is a shortlist, not an order. The
    tiebreak is BLAST RADIUS: among things that qualify, start with the one that
    can hurt least, because the first server is the one you are still learning
    on. Frequency breaks any remaining tie.
    """
    eligible = [s for s in scored if s[4] == "BUILD" and s[2] == 6]
    if not eligible:
        return
    eligible.sort(key=lambda s: (BLAST.get(
        (s[0].get("blast_radius") or "high").strip().lower(), 2), -s[3]))
    winner = eligible[0]
    reason = (winner[0].get("blast_radius") or "high").strip().lower()
    winner[4:] = ["BUILD FIRST",
                  f"Clears every question, and has the smallest blast radius ({reason})."]


ORDER = {"BUILD FIRST": 0, "BUILD": 1, "DECOMPOSE": 2, "NOT YET": 3, "WAIT": 4}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_file", nargs="?", help="candidate workflows")
    ap.add_argument("--explain", action="store_true",
                    help="say why each question passed or failed")
    ap.add_argument("--blank", action="store_true",
                    help="print an empty CSV to fill in")
    args = ap.parse_args()

    if args.blank:
        w = csv.writer(sys.stdout)
        w.writerow(["workflow", "exists", "reversible", "human_waits",
                    "per_month", "people", "six_tools", "vendor_would_ship",
                    "blast_radius", "notes"])
        w.writerow(["Your workflow here", "y", "y", "y", "4", "6", "y", "n",
                    "bounded", ""])
        return

    if not args.csv_file:
        ap.error("give a CSV, or --blank to print one")

    rows = list(csv.DictReader(Path(args.csv_file).open(encoding="utf-8")))
    scored = []
    for r in rows:
        answers, total, reps = score_row(r)
        v, why = verdict(answers, total)
        scored.append([r, answers, total, reps, v, why])

    pick_first(scored)
    scored.sort(key=lambda s: (ORDER[s[4]], -s[2], -s[3]))

    width = max(len(s[0]["workflow"]) for s in scored)
    print(f"\n{'WORKFLOW'.ljust(width)}  SCORE  VERDICT      WHY")
    print("-" * (width + 48))
    for r, answers, total, reps, v, why in scored:
        marks = "".join("+" if answers[q[0]] else "-" for q in QUESTIONS)
        print(f"{r['workflow'].ljust(width)}  {total}/6 {marks}  {v:<11}  {why}")

    if args.explain:
        for r, answers, total, reps, v, why in scored:
            print(f"\n=== {r['workflow']}  —  {v}")
            for key, question, on_pass, on_fail in QUESTIONS:
                ok = answers[key]
                detail = on_pass if ok else on_fail
                extra = ""
                if key == "frequency":
                    extra = f"  [{reps:.0f} repetitions/month × people]"
                print(f"  {'PASS' if ok else 'FAIL'}  {question}{extra}")
                print(f"        {detail}")
            if r.get("notes"):
                print(f"  note: {r['notes']}")

    print("\nQ6 is the only answer that changes while you sleep. Re-run quarterly.")


if __name__ == "__main__":
    main()

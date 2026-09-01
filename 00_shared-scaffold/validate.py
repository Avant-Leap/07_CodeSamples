"""
Enforce the rails.

A ruleset nobody checks is a ruleset nobody follows. This walks the sample
folders and asserts the things the handout claims — the tool ceiling, the
three-sentence description, preview+confirm on every write, idempotency keys on
every create, a bounded timeout, a named failure test.

It is deliberately allowed to FAIL. A gate that has never rejected anything is
decoration, so `--demo` runs it against deliberately broken fixtures and shows
it going red.

Standard library only.

    python validate.py                 # check every sample folder
    python validate.py ../01_revit-addin-surface
    python validate.py --demo          # prove the gates can fail
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
SAMPLES = HERE.parent

MAX_TOOLS = 6
SENTENCE_KEYS = ("what", "when", "whenNot")


class Findings:
    def __init__(self):
        self.rows = []

    def fail(self, where, rule, detail):
        self.rows.append(("FAIL", where, rule, detail))

    def warn(self, where, rule, detail):
        self.rows.append(("WARN", where, rule, detail))

    @property
    def failures(self):
        return [r for r in self.rows if r[0] == "FAIL"]


def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"{path}: invalid JSON — {e}")


# --- the rules --------------------------------------------------------------
def check_manifest(f, path, manifest, tools_by_name):
    where = path.name

    for field in ("id", "version", "name", "trigger", "owner",
                  "deliverable", "acceptanceTest", "maxTools", "tools"):
        if field not in manifest:
            f.fail(where, "manifest/required", f"missing `{field}`")

    tools = manifest.get("tools", [])
    cap = manifest.get("maxTools", MAX_TOOLS)

    if len(tools) > cap:
        f.fail(where, "rule-1/ceiling",
               f"{len(tools)} tools against maxTools {cap}. Going over is a "
               f"diagnosis: this is two processes sharing one manifest.")
    if cap > MAX_TOOLS:
        f.fail(where, "rule-1/ceiling", f"maxTools {cap} exceeds the hard limit of {MAX_TOOLS}")

    if not manifest.get("acceptanceTest"):
        f.fail(where, "done/acceptance",
               "no acceptance test. Without one this is a demo, not a process.")

    for t in tools:
        if t not in tools_by_name:
            f.fail(where, "manifest/tools", f"`{t}` is listed but has no definition")

    # every write must name its preview partner, and that partner must exist
    declared_writes = {w["tool"]: w for w in manifest.get("writes", [])}
    for name in tools:
        tool = tools_by_name.get(name)
        if not tool or tool.get("sideEffect") == "read":
            continue
        if name not in declared_writes:
            f.fail(where, "rule-4/preview",
                   f"`{name}` writes but is not declared in `writes`")
            continue
        partner = declared_writes[name].get("previewTool")
        if not partner:
            f.fail(where, "rule-4/preview", f"`{name}` has no previewTool")
        elif partner not in tools_by_name:
            f.fail(where, "rule-4/preview",
                   f"`{name}` previews with `{partner}`, which does not exist")

    if not manifest.get("supportedVersions"):
        f.warn(where, "versions", "no supportedVersions list — state them explicitly, never a range")
    if not manifest.get("tokenBudget"):
        f.warn(where, "done/cost", "no measured tokenBudget. If the number is unknown, it is not done")


def check_tool(f, path, tool):
    where = f"{path.name}:{tool.get('name', '?')}"
    name = tool.get("name", "")

    if not name or not name.replace("_", "").isalnum() or not name.islower():
        f.fail(where, "naming", "verb_noun, lower snake case")

    desc = tool.get("description")
    if not isinstance(desc, dict):
        f.fail(where, "rule-7/description", "description must be an object with what/when/whenNot")
    else:
        for k in SENTENCE_KEYS:
            if not desc.get(k):
                f.fail(where, "rule-7/description",
                       f"missing `{k}` — the third sentence is the one that prevents mis-selection")

    effect = tool.get("sideEffect")
    if effect not in ("read", "create", "update", "delete"):
        f.fail(where, "sideEffect", "must be read | create | update | delete")

    if effect == "create" and not tool.get("idempotencyKey"):
        f.fail(where, "idempotency",
               "a create tool needs a caller-supplied key, derived from intent. "
               "Without it the retry runs it twice.")

    if effect in ("create", "update", "delete") and not tool.get("previewTool"):
        f.fail(where, "rule-4/preview", "a write tool must name its preview partner")

    if effect != "read" and not tool.get("blastRadius"):
        f.fail(where, "blast-radius", "state the worst outcome of one confirmed call")

    if not tool.get("timeoutMs"):
        f.warn(where, "bounded-waits",
               "no timeoutMs. An unbounded wait guarantees the retry that causes duplicate work")

    if not tool.get("failureTest"):
        f.warn(where, "done/tests", "no failureTest named. A tool without one is not done")

    props = tool.get("inputSchema", {}).get("properties", {})
    for pname, spec in props.items():
        if spec.get("type") == "string" and "enum" not in spec and "pattern" not in spec:
            f.warn(where, "schema/bounds",
                   f"`{pname}` is an unbounded string — a model will invent a plausible value")


def check_folder(folder, f):
    tools_by_name = {}
    for tp in sorted((folder / "tools").glob("*.json")) if (folder / "tools").is_dir() else []:
        tool = load(tp)
        tools_by_name[tool.get("name")] = tool
        check_tool(f, tp, tool)

    mdir = folder / "manifests"
    if mdir.is_dir():
        for mp in sorted(mdir.glob("*.json")):
            check_manifest(f, mp, load(mp), tools_by_name)
    return len(tools_by_name)


def report(f, label):
    if not f.rows:
        print(f"  {label}: clean")
        return
    for level, where, rule, detail in f.rows:
        mark = "x" if level == "FAIL" else "!"
        print(f"  {mark} {level}  {where}  [{rule}]")
        print(f"          {detail}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    demo = "--demo" in sys.argv

    if demo:
        folder = HERE / "fixtures" / "broken"
        print(f"\nDEMO — running the gates against deliberately broken fixtures\n"
              f"A gate that cannot fail is not a gate.\n")
        f = Findings()
        check_folder(folder, f)
        report(f, "fixtures/broken")
        print(f"\n{len(f.failures)} failures. That is the correct result.\n")
        return 0

    targets = [Path(a) for a in args] or [
        p for p in sorted(SAMPLES.glob("0[1-4]_*")) if p.is_dir()]

    print("\nChecking the rails\n")
    total_fail = 0
    for folder in targets:
        f = Findings()
        n = check_folder(folder, f)
        print(f"{folder.name}  ({n} tools)")
        report(f, folder.name)
        total_fail += len(f.failures)
        print()

    print(f"{total_fail} failures.")
    return 1 if total_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
Handlers for the graph catalogue. A teaching sample.

The interesting one is `run_dynamo_graph`. Everything else here is plumbing;
that one shows the thing naive wrappers get wrong — **partial success is not
failure.** A graph that renumbers 42 rooms and skips 3 has not failed, and an
agent that receives an exception cannot tell the user anything useful.

There is no Dynamo here. Invocation is faked so the sample runs anywhere; the
shape of what comes back is the part worth copying.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "00_shared-scaffold" / "host_python"))
from contracts import ToolError, ok        # noqa: E402

# Stands in for the catalogue file. In a real server this is the YAML entry per
# graph, and the `validated` field — the last real project it ran on — is what
# earns trust internally. A catalogue without it is a folder with better
# formatting.
CATALOGUE = {
    "Standards/Renumber_Rooms_ByLevel.dyn": {
        "name": "Renumber rooms by level",
        "category": "documentation",
        "description": ("Renumbers all rooms on a level following the firm sequence "
                        "convention, starting from a supplied prefix."),
        "inputs": [{"name": "level_name", "type": "string", "required": True},
                   {"name": "prefix", "type": "string", "required": False, "default": ""}],
        "outputs": ["rooms_renumbered", "skipped"],
        "preconditions": ["A Revit document must be open",
                          "The named level must exist in the document"],
        "failure_modes": ["Unplaced rooms are skipped and reported, not renumbered"],
        "validated": "2026-03, Project 2214",
    },
    "Standards/Tag_All_Ducts.dyn": {
        "name": "Tag all ducts in view",
        "category": "documentation",
        "description": "Places a tag on every untagged duct in the active view.",
        "inputs": [{"name": "tag_family", "type": "string", "required": True}],
        "outputs": ["tags_placed", "skipped"],
        "preconditions": ["A Revit document must be open", "A plan view must be active"],
        "failure_modes": ["Ducts already tagged are skipped"],
        "validated": "2026-05, Project 2301",
    },
}


def list_dynamo_packages(args):
    wanted = args.get("filterCategory", "any")
    rows = [{"path": p, "name": g["name"], "category": g["category"],
             "description": g["description"], "validated": g["validated"]}
            for p, g in CATALOGUE.items()
            if wanted in ("any", g["category"])]
    return ok({"graphs": rows, "count": len(rows)})


def get_graph_outputs(args):
    graph = CATALOGUE.get(args["graphPath"])
    if graph is None:
        # Typed, not a stack trace. The agent can act on this: go back to the
        # catalogue tool and pick a path that exists.
        raise ToolError("NOT_FOUND",
                        "That graph is not in the catalogue. Call list_dynamo_packages first.",
                        graphPath=args["graphPath"])
    return ok({"inputs": graph["inputs"], "outputs": graph["outputs"],
               "preconditions": graph["preconditions"],
               "failureModes": graph["failure_modes"],
               "validated": graph["validated"]})


def run_dynamo_graph(args):
    graph = CATALOGUE.get(args["graphPath"])
    if graph is None:
        raise ToolError("NOT_FOUND", "That graph is not in the catalogue.",
                        graphPath=args["graphPath"])

    # A real host checks the bridge here and returns NO_ACTIVE_DOCUMENT rather
    # than guessing. Guessing is how an agent corrupts something.
    document_open = args.get("_documentOpen", True)
    if not document_open:
        raise ToolError("NO_ACTIVE_DOCUMENT",
                        "This graph needs an open document. Ask the user to open the "
                        "model and call again.",
                        retryable=True)

    for spec in graph["inputs"]:
        if spec["required"] and spec["name"] not in (args.get("inputs") or {}):
            raise ToolError("BAD_INPUT",
                            f"`{spec['name']}` is required by this graph.",
                            missing=spec["name"])

    # --- the part worth copying ------------------------------------------
    # Return the count that WORKED and the list that did NOT, with reasons.
    # "42 renumbered, 3 skipped — unplaced rooms" is something an agent can
    # tell a person. An exception is not.
    changed, skipped = 42, [
        {"item": "Room 1204", "reason": "unplaced"},
        {"item": "Room 1207", "reason": "unplaced"},
        {"item": "Room 1310", "reason": "read-only workset"},
    ]

    warnings = [{"code": "PARTIAL_FAILURE",
                 "message": f"{s['item']} was skipped: {s['reason']}.",
                 "item": s["item"]} for s in skipped]

    return ok({"count": changed, "changed": changed, "skipped": skipped,
               "graph": graph["name"]},
              warnings=warnings or None)


HANDLERS = {
    "list_dynamo_packages": list_dynamo_packages,
    "get_graph_outputs": get_graph_outputs,
    "run_dynamo_graph": run_dynamo_graph,
}

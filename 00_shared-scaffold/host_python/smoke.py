"""
Drive both sample servers over real stdio JSON-RPC and show the rails firing.

This is the failure-path test the samples keep insisting on. It does not check
that the happy path works — anyone can see that. It checks that the guards
REFUSE, because a guard that has never refused anything is decoration.

It talks to the server turn by turn rather than posting a batch, because that
is what a client actually does: the token you pass to a write is the token the
previous read handed you. A test that cannot carry that token cannot exercise
the confirm path at all.

    python smoke.py
"""

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SAMPLES = HERE.parents[1]


class Client:
    """One live server on stdin/stdout, spoken to a line at a time."""

    def __init__(self, folder, process_id):
        self.proc = subprocess.Popen(
            [sys.executable, str(HERE / "server.py"), str(SAMPLES / folder), process_id],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1)
        self.n = 0

    def rpc(self, method, params=None):
        self.n += 1
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self.n,
                                          "method": method,
                                          "params": params or {}}) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise SystemExit("server closed the stream\n" + self.proc.stderr.read())
        return json.loads(line)["result"]

    def call(self, name, args):
        r = self.rpc("tools/call", {"name": name, "arguments": args})
        return json.loads(r["content"][0]["text"])

    def close(self):
        self.proc.stdin.close()
        self.proc.wait(timeout=30)


def show(title, env, expect_ok=None, expect_code=None):
    got = "ok" if env.get("ok") else env.get("code")
    verdict = "  "
    if expect_ok is not None or expect_code is not None:
        want = "ok" if expect_ok else expect_code
        verdict = "PASS" if got == want else "FAIL"
    detail = env.get("message") or json.dumps(env.get("data"))[:66]
    print(f"  {verdict}  {title:<44} -> {got:<18} {detail}")
    return verdict != "FAIL"


def dynamo():
    good = True
    print("\n=== 02_dynamo-promotion ===")
    c = Client("02_dynamo-promotion", "p2-graph-catalogue")
    info = c.rpc("server/discover")
    listed = c.rpc("tools/list")
    print(f"  server: {info['serverInfo']['name']} | protocol {info['protocolVersion']}")
    print(f"  tools exposed: {[t['name'] for t in listed['tools']]}"
          f"  (ttlMs {listed['ttlMs']})")

    graph = "Standards/Renumber_Rooms_ByLevel.dyn"
    good &= show("catalogue lists graphs",
                 c.call("list_dynamo_packages", {}), expect_ok=True)
    good &= show("write WITHOUT a confirm token",
                 c.call("run_dynamo_graph", {"graphPath": graph,
                                             "inputs": {"level_name": "L02"},
                                             "requestKey": "k1"}),
                 expect_code="PREVIEW_REQUIRED")

    preview = c.call("get_graph_outputs", {"graphPath": graph})
    good &= show("preview issues a token", preview, expect_ok=True)
    token = preview["data"]["confirmToken"]

    good &= show("write with an INVENTED token",
                 c.call("run_dynamo_graph", {"graphPath": graph,
                                             "inputs": {"level_name": "L02"},
                                             "requestKey": "k1",
                                             "confirmToken": "PLACEHOLDER"}),
                 expect_code="PREVIEW_EXPIRED")

    run = c.call("run_dynamo_graph", {"graphPath": graph,
                                      "inputs": {"level_name": "L02"},
                                      "requestKey": "k1", "confirmToken": token})
    good &= show("write with the REAL token", run, expect_ok=True)
    # The point of the whole sample: this succeeded AND reported what it skipped.
    good &= show("   and partial success is reported, not raised",
                 {"ok": bool(run.get("warnings")),
                  "data": f"{run['data']['changed']} changed, "
                          f"{len(run['data']['skipped'])} skipped with reasons"},
                 expect_ok=True)

    good &= show("the SPENT token cannot be reused",
                 c.call("run_dynamo_graph", {"graphPath": graph,
                                             "inputs": {"level_name": "L02"},
                                             "requestKey": "k2",
                                             "confirmToken": token}),
                 expect_code="PREVIEW_EXPIRED")
    good &= show("unknown graph",
                 c.call("get_graph_outputs", {"graphPath": "Nope/Missing.dyn"}),
                 expect_code="NOT_FOUND")
    c.close()
    return good


def aps():
    good = True
    print("\n=== 03_aps-pipeline ===")
    c = Client("03_aps-pipeline", "p3-cloud-chain")
    info = c.rpc("server/discover")
    listed = c.rpc("tools/list")
    print(f"  server: {info['serverInfo']['name']} | protocol {info['protocolVersion']}")
    print(f"  tools exposed: {[t['name'] for t in listed['tools']]}")

    resolved = c.call("model_get_metadata", {"projectId": "b.1234", "itemId": "abc"})
    good &= show("resolve a model", resolved, expect_ok=True)
    urn, token = resolved["data"]["urn"], resolved["data"]["confirmToken"]

    good &= show("malformed project id",
                 c.call("model_get_metadata", {"projectId": "oops", "itemId": "abc"}),
                 expect_code="BAD_INPUT")
    good &= show("create WITHOUT a requestKey",
                 c.call("model_export_derivative", {"urn": urn, "outputFormat": "svf2"}),
                 expect_code="BAD_INPUT")

    # An argument the model invented. It has a valid token and a valid key, so
    # the ONLY thing standing between it and the engine is the Activity contract.
    good &= show("argument outside the Activity enum",
                 c.call("automation_create_workitem",
                        {"activityAlias": "cleanup.prod", "urn": urn,
                         "arguments": {"ruleSet": "nonsense"},
                         "requestKey": "j1", "confirmToken": token}),
                 expect_code="BAD_INPUT")

    fresh = c.call("model_get_metadata", {"projectId": "b.1234", "itemId": "abc"})
    started = c.call("model_export_derivative",
                     {"urn": urn, "outputFormat": "svf2", "requestKey": "d1",
                      "confirmToken": fresh["data"]["confirmToken"]})
    good &= show("long work returns a task handle", started, expect_ok=True)
    task = started["data"]["taskId"]

    repeat = c.call("model_export_derivative",
                    {"urn": urn, "outputFormat": "svf2", "requestKey": "d1"})
    good &= show("   and same requestKey, no second billable job",
                 {"ok": repeat.get("ok") and repeat["data"]["taskId"] == task,
                  "data": f"returned the stored handle {task}"},
                 expect_ok=True)

    good &= show("poll reports progress, never blocks",
                 c.call("job_get_status", {"taskId": task}), expect_ok=True)
    good &= show("unknown task id",
                 c.call("job_get_status", {"taskId": "task-does-not-exist"}),
                 expect_code="NOT_FOUND")
    c.close()
    return good


def main():
    good = dynamo() & aps()
    print("\nEvery line above that says PASS is a guard refusing something,")
    print("or a promise the README makes turning out to be true.\n")
    return 0 if good else 1


if __name__ == "__main__":
    raise SystemExit(main())

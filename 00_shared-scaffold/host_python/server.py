"""
A minimal MCP host that reads the contracts and enforces the rails.

This is a TEACHING SAMPLE. It is stdlib-only and about two hundred lines so the
protocol stays visible — an SDK would hide the very thing worth seeing.

What makes it worth reading is that it is driven entirely by the JSON you
already wrote. It loads a manifest and a tools folder, and from those alone it:

  · exposes ONLY the tools the manifest lists            (rule 3, one manifest)
  · refuses to start if the manifest breaks the ceiling  (rule 1, six tools)
  · returns the standard envelope on both paths          (the shared contract)
  · blocks any write that arrives without a confirm token (rule 4, preview→confirm)
  · dedupes any create that repeats a requestKey          (idempotency)
  · bounds every call with the tool's own timeoutMs       (bounded waits)
  · writes an append-only audit line before returning     (rule 6)

The same host runs 02_dynamo-promotion and 03_aps-pipeline unchanged. That is
the argument made executable: the contract sits above the implementation, so
the server does not know — or care — what is underneath it.

    python server.py ../../02_dynamo-promotion p2-graph-catalogue
    python server.py ../../03_aps-pipeline     p3-cloud-chain
"""

import json
import sys
import time
import uuid
from pathlib import Path

MAX_TOOLS = 6
PROTOCOL = "2026-07-28"


from contracts import ToolError, err, ok      # noqa: F401


# ── the server ──────────────────────────────────────────────────────────────
class Server:
    def __init__(self, folder: Path, process_id: str, handlers):
        self.folder = folder
        self.handlers = handlers
        self.manifest = json.loads(
            (folder / "manifests" / f"{process_id}.json").read_text("utf-8"))

        # Rule 1, checked at STARTUP. A server that can breach its own ceiling
        # at runtime will, on the day nobody is looking.
        names = self.manifest["tools"]
        cap = min(self.manifest.get("maxTools", MAX_TOOLS), MAX_TOOLS)
        if len(names) > cap:
            raise SystemExit(
                f"refusing to start: {len(names)} tools against a ceiling of {cap}. "
                f"That is two processes sharing one manifest.")

        # Rule 3: the manifest selects. Tools on disk but not listed stay invisible.
        self.tools = {}
        for name in names:
            self.tools[name] = json.loads(
                (folder / "tools" / f"{name}.json").read_text("utf-8"))

        self.writes = {w["tool"]: w for w in self.manifest.get("writes", [])}
        self.previews = {}       # token -> (tool, expiry)
        self.seen = {}           # requestKey -> stored envelope
        self.audit = folder / "audit.log"

    # -- MCP surface --------------------------------------------------------
    def list_tools(self):
        out = []
        for name, t in self.tools.items():
            d = t["description"]
            # The three sentences are what the model actually reads. Joining
            # them here is the only place the split shape becomes prose.
            text = f"{d['what']} {d['when']} {d['whenNot']}"
            for extra in ("requires", "onPartialSuccess"):
                if d.get(extra):
                    v = d[extra]
                    text += " " + (" ".join(v) if isinstance(v, list) else v)
            out.append({"name": name, "description": text,
                        "inputSchema": t["inputSchema"]})
        # Rule: deterministic ordering, so a client can cache it.
        return sorted(out, key=lambda t: t["name"])

    def call(self, name, args):
        tool = self.tools.get(name)
        if tool is None:
            # Not "unknown tool" — the manifest deliberately hid it.
            return err("NOT_FOUND", f"`{name}` is not in this process.")

        effect = tool.get("sideEffect", "read")

        # Idempotency, before anything executes. A repeat key returns the STORED
        # result; it does not run again and does not bill again.
        key = args.get("requestKey")
        if effect == "create":
            if not key:
                return err("BAD_INPUT",
                           f"`{name}` creates something and needs a requestKey "
                           f"derived from intent.")
            if key in self.seen:
                return self.seen[key]

        # Preview → confirm. No convenience bypass: one bypass puts a hole in
        # the audit trail that nobody remembers.
        if effect != "read":
            token = args.get("confirmToken")
            partner = self.writes.get(name, {}).get("previewTool")
            if not token:
                return err("PREVIEW_REQUIRED",
                           f"`{name}` writes. Call `{partner}` first and pass its token.",
                           previewTool=partner)
            held = self.previews.get(token)
            if not held:
                return err("PREVIEW_EXPIRED", "That confirm token is unknown or spent.")
            if held[0] != partner or held[1] < time.time():
                self.previews.pop(token, None)
                return err("PREVIEW_EXPIRED", "That confirm token has expired. Preview again.")
            self.previews.pop(token)

        started = time.time()
        budget = tool.get("timeoutMs", 30000) / 1000
        try:
            result = self.handlers[name](args)
        except ToolError as e:
            result = e.envelope
        except Exception as e:                      # never leak a stack trace
            result = err("INTERNAL", f"{name} failed.", retryable=False,
                         kind=type(e).__name__)

        # Bounded waits. An unbounded wait guarantees the client timeout that
        # causes the retry — so we own the deadline rather than the client.
        if time.time() - started > budget:
            result = err("TIMEOUT",
                         f"`{name}` exceeded its {budget:.0f}s budget.",
                         retryable=True, waitedMs=int((time.time() - started) * 1000))

        # A read tool that previews issues a token its partner will demand.
        if effect == "read" and name in {w.get("previewTool") for w in self.writes.values()}:
            if result.get("ok"):
                token = uuid.uuid4().hex
                self.previews[token] = (name, time.time() + 300)
                result["data"] = dict(result["data"] or {}, confirmToken=token)

        if effect == "create" and key:
            self.seen[key] = result

        if effect != "read":
            self._audit(name, args, result)
        return result

    def _audit(self, name, args, result):
        """Append-only, written BEFORE the tool returns.

        Note what is absent: which agent or model made the call. The protocol
        authenticates the HOST, not the agent, so any agent identity would be a
        guess — and recording a guess is worse than recording nothing, because
        it looks like provenance in an audit review and is not.
        """
        line = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "processId": self.manifest["id"],
            "processVersion": self.manifest["version"],
            "tool": name,
            "host": "sample-python-host",
            "hostVersion": "1.0.0",
            "subject": str(args.get("productPath") or args.get("graphPath")
                           or args.get("urn") or "-"),
            "itemCount": int((result.get("data") or {}).get("count", 0))
            if result.get("ok") else 0,
            "requestKey": args.get("requestKey"),
            "outcome": "ok" if result.get("ok") else result.get("code"),
        }
        with self.audit.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(line) + "\n")


# ── stdio JSON-RPC, by hand so the protocol stays visible ───────────────────
def serve(server: Server):
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            req = json.loads(raw)
        except json.JSONDecodeError:
            continue

        method, rid = req.get("method"), req.get("id")
        params = req.get("params") or {}

        if method == "server/discover":
            result = {"protocolVersion": PROTOCOL,
                      "serverInfo": {"name": server.manifest["name"],
                                     "version": server.manifest["version"]},
                      "capabilities": {"tools": {}}}
        elif method == "tools/list":
            # ttlMs and cacheScope are required on list operations since 2026-07-28.
            result = {"tools": server.list_tools(), "ttlMs": 300000,
                      "cacheScope": "session"}
        elif method == "tools/call":
            result = {"content": [{"type": "text",
                                   "text": json.dumps(
                                       server.call(params.get("name"),
                                                   params.get("arguments") or {}))}]}
        else:
            result = None

        if rid is not None:
            print(json.dumps({"jsonrpc": "2.0", "id": rid, "result": result}),
                  flush=True)


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    folder = Path(sys.argv[1]).resolve()
    sys.path.insert(0, str(folder))
    import handlers                                   # noqa: E402
    serve(Server(folder, sys.argv[2], handlers.HANDLERS))


if __name__ == "__main__":
    main()

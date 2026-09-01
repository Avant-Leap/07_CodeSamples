using System.Text.Json.Nodes;

namespace ReleaseGate;

/// <summary>
/// The rails, enforced in the host so no handler can forget one.
///
/// This is the same server as host_python/server.py, written in the language
/// LO1 names. Read them side by side: the contracts are identical, the rails
/// are identical, and neither host knows anything about what it is running.
/// That is the argument — the contract sits above the implementation.
/// </summary>
public sealed class Server
{
    const int MaxTools = 6;
    public const string Protocol = "2026-07-28";

    readonly Contracts _c;
    readonly Dictionary<string, Func<JsonObject, JsonObject>> _handlers;
    readonly Dictionary<string, JsonObject> _writes = new();
    readonly Dictionary<string, (string Tool, DateTime Expires)> _previews = new();
    readonly Dictionary<string, JsonObject> _seen = new();
    readonly string _auditPath;

    public Server(Contracts contracts,
                  Dictionary<string, Func<JsonObject, JsonObject>> handlers)
    {
        _c = contracts;
        _handlers = handlers;

        // Rule 1, checked at STARTUP rather than per call. A server that *can*
        // breach its own ceiling at runtime eventually will, on the day nobody
        // is watching. Refusing to boot is the only check that cannot be skipped.
        var declared = _c.Manifest["maxTools"]?.GetValue<int>() ?? MaxTools;
        var cap = Math.Min(declared, MaxTools);
        if (_c.Tools.Count > cap)
            throw new InvalidOperationException(
                $"refusing to start: {_c.Tools.Count} tools against a ceiling of {cap}. " +
                "That is two processes sharing one manifest.");

        foreach (var w in _c.Manifest["writes"]?.AsArray() ?? new JsonArray())
            _writes[w!["tool"]!.GetValue<string>()] = w.AsObject();

        _auditPath = Path.Combine(_c.Folder, "audit.log");
    }

    public JsonObject Manifest => _c.Manifest;

    // -- MCP surface ---------------------------------------------------------

    public JsonArray ListTools()
    {
        var list = new JsonArray();
        foreach (var name in _c.Tools.Keys.OrderBy(n => n, StringComparer.Ordinal))
        {
            var d = _c.Tools[name]["description"]!.AsObject();

            // The three sentences are what the model actually reads before it
            // chooses. `whenNot` is the one people leave out, and it is the one
            // that stops a tool being called for a job it cannot do.
            var text = $"{d["what"]} {d["when"]} {d["whenNot"]}";
            foreach (var extra in new[] { "requires", "onPartialSuccess" })
                if (d[extra] is JsonNode n)
                    text += " " + (n is JsonArray a
                        ? string.Join(" ", a.Select(x => x!.GetValue<string>()))
                        : n.GetValue<string>());

            list.Add(new JsonObject
            {
                ["name"] = name,
                ["description"] = text,
                ["inputSchema"] = _c.Tools[name]["inputSchema"]!.DeepClone(),
            });
        }
        return list;
    }

    public JsonObject Call(string name, JsonObject args)
    {
        if (!_c.Tools.TryGetValue(name, out var tool))
            // Not "unknown tool" — the manifest deliberately did not expose it.
            return Envelope.Err("NOT_FOUND", $"`{name}` is not in this process.");

        var effect = tool["sideEffect"]?.GetValue<string>() ?? "read";
        var key = args["requestKey"]?.GetValue<string>();

        // Idempotency BEFORE anything executes. A repeated key returns the
        // stored envelope: it does not run again, and it does not bill again.
        if (effect == "create")
        {
            if (string.IsNullOrEmpty(key))
                return Envelope.Err("BAD_INPUT",
                    $"`{name}` creates something and needs a requestKey derived from intent.");
            if (_seen.TryGetValue(key, out var stored)) return stored;
        }

        // Preview → confirm, with no convenience bypass. One bypass puts a hole
        // in the audit trail that nobody remembers adding.
        if (effect != "read")
        {
            var partner = _writes.TryGetValue(name, out var w)
                ? w["previewTool"]?.GetValue<string>() : null;
            var token = args["confirmToken"]?.GetValue<string>();

            if (string.IsNullOrEmpty(token))
                return Envelope.Err("PREVIEW_REQUIRED",
                    $"`{name}` writes. Call `{partner}` first and pass its token.",
                    detail: new JsonObject { ["previewTool"] = partner });

            if (!_previews.TryGetValue(token, out var held))
                return Envelope.Err("PREVIEW_EXPIRED", "That confirm token is unknown or spent.");

            if (held.Tool != partner || held.Expires < DateTime.UtcNow)
            {
                _previews.Remove(token);
                return Envelope.Err("PREVIEW_EXPIRED",
                    "That confirm token has expired. Preview again.");
            }
            _previews.Remove(token);      // single use, always
        }

        var started = DateTime.UtcNow;
        var budget = TimeSpan.FromMilliseconds(tool["timeoutMs"]?.GetValue<int>() ?? 30000);

        JsonObject result;
        try
        {
            result = _handlers[name](args);
        }
        catch (ToolException e)
        {
            result = e.Envelope;
        }
        catch (Exception e)
        {
            // Never leak a stack trace across the protocol boundary. The type
            // name is enough for an operator reading the audit log.
            result = Envelope.Err("INTERNAL", $"{name} failed.",
                detail: new JsonObject { ["kind"] = e.GetType().Name });
        }

        // Bounded waits. An unbounded wait *guarantees* the client-side timeout
        // that causes the retry — so the server owns the deadline, not the client.
        var elapsed = DateTime.UtcNow - started;
        if (elapsed > budget)
            result = Envelope.Err("TIMEOUT",
                $"`{name}` exceeded its {budget.TotalSeconds:F0}s budget.",
                retryable: true,
                detail: new JsonObject { ["waitedMs"] = (int)elapsed.TotalMilliseconds });

        // A read tool that acts as somebody's preview issues the token its
        // partner will demand.
        var isPreview = _writes.Values.Any(
            w => w["previewTool"]?.GetValue<string>() == name);
        if (effect == "read" && isPreview && result["ok"]!.GetValue<bool>())
        {
            var token = Guid.NewGuid().ToString("N");
            _previews[token] = (name, DateTime.UtcNow.AddMinutes(5));
            result["data"]!.AsObject()["confirmToken"] = token;
        }

        if (effect == "create" && key is not null) _seen[key] = result;
        if (effect != "read") Audit(name, args, result);

        return result;
    }

    /// <summary>
    /// Append-only, written before the tool returns.
    ///
    /// Note what is absent: which agent or model made the call. The protocol
    /// authenticates the HOST, not the agent, so any agent identity here would
    /// be a guess — and a recorded guess is worse than a blank, because in a
    /// review it looks like provenance and is not.
    /// </summary>
    void Audit(string name, JsonObject args, JsonObject result)
    {
        var okFlag = result["ok"]!.GetValue<bool>();
        var line = new JsonObject
        {
            ["timestamp"] = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ"),
            ["processId"] = _c.Manifest["id"]!.DeepClone(),
            ["processVersion"] = _c.Manifest["version"]!.DeepClone(),
            ["tool"] = name,
            ["host"] = "sample-csharp-host",
            ["hostVersion"] = "1.0.0",
            ["subject"] = args["productPath"]?.GetValue<string>() ?? "-",
            ["itemCount"] = okFlag
                ? result["data"]?["count"]?.GetValue<int>() ?? 0
                : 0,
            ["requestKey"] = args["requestKey"]?.DeepClone(),
            ["outcome"] = okFlag ? "ok" : result["code"]!.DeepClone(),
        };
        File.AppendAllText(_auditPath, line.ToJsonString() + Environment.NewLine);
    }
}

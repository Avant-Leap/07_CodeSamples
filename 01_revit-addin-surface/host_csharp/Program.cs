using System.Text.Json.Nodes;

namespace ReleaseGate;

/// <summary>
/// stdio JSON-RPC, written by hand so the protocol stays visible.
///
///     dotnet run -- serve ..            p8-addin-release-gate
///     dotnet run -- smoke ..            p8-addin-release-gate
///
/// `serve` is what an MCP client launches. `smoke` runs the failure-path script
/// in-process so you can see the gate refuse without wiring up a client first.
/// </summary>
public static class Program
{
    public static int Main(string[] argv)
    {
        var mode = argv.ElementAtOrDefault(0) ?? "serve";
        var folder = Path.GetFullPath(argv.ElementAtOrDefault(1) ?? "..");
        var processId = argv.ElementAtOrDefault(2) ?? "p8-addin-release-gate";

        Contracts contracts;
        Server server;
        try
        {
            contracts = new Contracts(folder, processId);
            server = new Server(contracts, new Handlers(contracts).Map());
        }
        catch (InvalidOperationException e)
        {
            Console.Error.WriteLine(e.Message);
            return 1;
        }

        return mode == "smoke" ? Smoke.Run(server) : Serve(server);
    }

    static int Serve(Server server)
    {
        string? raw;
        while ((raw = Console.ReadLine()) is not null)
        {
            if (string.IsNullOrWhiteSpace(raw)) continue;

            JsonObject req;
            try { req = JsonNode.Parse(raw)!.AsObject(); }
            catch { continue; }

            var method = req["method"]?.GetValue<string>();
            var id = req["id"];
            var pars = req["params"]?.AsObject() ?? new JsonObject();

            JsonNode? result = method switch
            {
                // Mandatory since the 2026-07-28 revision — a client must be
                // able to learn what a server is before it commits to it.
                "server/discover" => new JsonObject
                {
                    ["protocolVersion"] = Server.Protocol,
                    ["serverInfo"] = new JsonObject
                    {
                        ["name"] = server.Manifest["name"]!.DeepClone(),
                        ["version"] = server.Manifest["version"]!.DeepClone(),
                    },
                    ["capabilities"] = new JsonObject { ["tools"] = new JsonObject() },
                },

                // ttlMs and cacheScope are required on list operations, so a
                // client can cache the surface instead of re-reading it a turn.
                "tools/list" => new JsonObject
                {
                    ["tools"] = server.ListTools(),
                    ["ttlMs"] = 300000,
                    ["cacheScope"] = "session",
                },

                "tools/call" => new JsonObject
                {
                    ["content"] = new JsonArray(new JsonObject
                    {
                        ["type"] = "text",
                        ["text"] = server.Call(
                            pars["name"]!.GetValue<string>(),
                            pars["arguments"]?.AsObject() ?? new JsonObject())
                            .ToJsonString(),
                    }),
                },

                _ => null,
            };

            if (id is not null)
                Console.WriteLine(new JsonObject
                {
                    ["jsonrpc"] = "2.0",
                    ["id"] = id.DeepClone(),
                    ["result"] = result,
                }.ToJsonString());
        }
        return 0;
    }
}

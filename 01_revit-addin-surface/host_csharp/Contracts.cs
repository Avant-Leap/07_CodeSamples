using System.Text.Json;
using System.Text.Json.Nodes;

namespace ReleaseGate;

/// <summary>
/// The envelope, and the contract files it is defined by.
///
/// Every tool returns one of exactly two shapes. The point is that a client
/// never has to ask "did this throw, or did it return something odd?" — success
/// and failure are both data, and failure carries a code from a closed set.
/// </summary>
public static class Envelope
{
    public static JsonObject Ok(JsonObject data, JsonArray? warnings = null)
    {
        var env = new JsonObject { ["ok"] = true, ["data"] = data };
        if (warnings is { Count: > 0 }) env["warnings"] = warnings;
        return env;
    }

    public static JsonObject Err(string code, string message,
                                 bool retryable = false, JsonObject? detail = null)
    {
        var env = new JsonObject
        {
            ["ok"] = false,
            ["code"] = code,
            ["message"] = message,
            ["retryable"] = retryable,
        };
        if (detail is not null) env["detail"] = detail;
        return env;
    }
}

/// <summary>
/// Thrown by a handler to return a typed failure instead of a stack trace.
///
/// A stack trace tells an agent nothing it can act on. `NO_ACTIVE_DOCUMENT`
/// tells it to ask the user to open a model, and `BAD_INPUT` tells it to fix
/// the call and try again. That difference is the whole reason this type exists.
/// </summary>
public sealed class ToolException : Exception
{
    public JsonObject Envelope { get; }

    public ToolException(string code, string message,
                         bool retryable = false, JsonObject? detail = null)
        : base(message)
        => Envelope = ReleaseGate.Envelope.Err(code, message, retryable, detail);
}

/// <summary>Loads the JSON contracts that drive the server.</summary>
public sealed class Contracts
{
    public JsonObject Manifest { get; }
    public Dictionary<string, JsonObject> Tools { get; } = new();
    public string Folder { get; }

    public Contracts(string folder, string processId)
    {
        Folder = folder;
        Manifest = Load(Path.Combine(folder, "manifests", processId + ".json"));

        foreach (var name in Manifest["tools"]!.AsArray()
                                     .Select(n => n!.GetValue<string>()))
            Tools[name] = Load(Path.Combine(folder, "tools", name + ".json"));
    }

    public JsonObject Config(string name) =>
        Load(Path.Combine(Folder, "config", name));

    static JsonObject Load(string path) =>
        JsonNode.Parse(File.ReadAllText(path))!.AsObject();

    public static string Pretty(JsonNode node) =>
        node.ToJsonString(new JsonSerializerOptions { WriteIndented = false });
}

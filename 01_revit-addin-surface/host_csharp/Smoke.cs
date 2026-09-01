using System.Text.Json.Nodes;

namespace ReleaseGate;

/// <summary>
/// The failure-path script. `dotnet run -- smoke ..`
///
/// It does not test that packaging works. It tests that packaging REFUSES —
/// without a preview token, after a stale token, and while validation has
/// blocking findings. Every PASS below is a guard turning something down.
/// </summary>
public static class Smoke
{
    static bool _good = true;

    public static int Run(Server s)
    {
        const string product = "AvantLeap.Tools.Sample";

        Console.WriteLine("\n=== 01_revit-addin-surface (C# host) ===");
        Console.WriteLine($"  protocol {Server.Protocol} | tools exposed: " +
                          string.Join(", ", s.ListTools()
                              .Select(t => t!["name"]!.GetValue<string>())));

        var validation = s.Call("validate_addin", new JsonObject
        {
            ["productPath"] = product,
        });
        Show("validation runs the rules from JSON", validation, ok: true);
        Show("   and it reports a blocked verdict, not a crash",
             Fake(validation["data"]!["verdict"]!.GetValue<string>() == "blocked",
                  $"{validation["data"]!["blocking"]} blocking of "
                  + $"{validation["data"]!["count"]} findings"), ok: true);

        Show("build WITHOUT a confirm token",
             s.Call("build_all_versions", new JsonObject
             {
                 ["productPath"] = product,
             }), code: "PREVIEW_REQUIRED");

        // Note the ORDER the host enforces: authorisation first, arguments
        // second. This call is properly authorised and still refused, so the
        // refusal can only have come from the version matrix.
        Show("a version outside the matrix",
             s.Call("build_all_versions", new JsonObject
             {
                 ["productPath"] = product,
                 ["versions"] = new JsonArray("2031"),
                 ["confirmToken"] = validation["data"]!["confirmToken"]!.GetValue<string>(),
             }), code: "UNSUPPORTED_VERSION");

        // validate_addin is build's preview partner, so each run hands out a
        // token — and the one above was spent proving the point.
        var token = s.Call("validate_addin", new JsonObject
        {
            ["productPath"] = product,
        })["data"]!["confirmToken"]!.GetValue<string>();
        var build = s.Call("build_all_versions", new JsonObject
        {
            ["productPath"] = product,
            ["confirmToken"] = token,
        });
        Show("build with the REAL token", build, ok: true);
        Show("   and per-version outcomes, not one boolean",
             Fake(build["warnings"] is JsonArray { Count: > 0 },
                  $"{build["data"]!["count"]} of {build["data"]!["attempted"]} versions built"),
             ok: true);

        Show("the SPENT token cannot be reused",
             s.Call("build_all_versions", new JsonObject
             {
                 ["productPath"] = product,
                 ["confirmToken"] = token,
             }), code: "PREVIEW_EXPIRED");

        var preview = s.Call("check_store_requirements", new JsonObject
        {
            ["productPath"] = product,
            ["releaseVersion"] = "1.4.2",
        });
        Show("preview reports what packaging would write", preview, ok: true);
        var packToken = preview["data"]!["confirmToken"]!.GetValue<string>();

        Show("package WITHOUT a requestKey",
             s.Call("package_release", new JsonObject
             {
                 ["productPath"] = product,
                 ["releaseVersion"] = "1.4.2",
                 ["confirmToken"] = packToken,
             }), code: "BAD_INPUT");

        // Fully authorised — right token, right key — and it still refuses,
        // because validation is unresolved. That is the whole sample.
        Show("package while findings are outstanding",
             s.Call("package_release", new JsonObject
             {
                 ["productPath"] = product,
                 ["releaseVersion"] = "1.4.2",
                 ["confirmToken"] = packToken,
                 ["requestKey"] = $"{product}@1.4.2",
             }), code: "PRECONDITION_FAILED");

        Show("a tool the manifest does not expose",
             s.Call("delete_everything", new JsonObject()), code: "NOT_FOUND");

        Console.WriteLine("\nEvery PASS above is the gate refusing something.");
        Console.WriteLine("A gate that has never rejected anything is decoration.\n");
        return _good ? 0 : 1;
    }

    static JsonObject Fake(bool condition, string note) =>
        condition ? Envelope.Ok(new JsonObject { ["note"] = note })
                  : Envelope.Err("PRECONDITION_FAILED", note);

    static void Show(string title, JsonObject env, bool? ok = null, string? code = null)
    {
        var got = env["ok"]!.GetValue<bool>() ? "ok" : env["code"]!.GetValue<string>();
        var want = ok == true ? "ok" : code;
        var verdict = got == want ? "PASS" : "FAIL";
        if (verdict == "FAIL") _good = false;

        var detail = env["message"]?.GetValue<string>()
                     ?? env["data"]?.ToJsonString() ?? "";
        if (detail.Length > 64) detail = detail[..64];

        Console.WriteLine($"  {verdict}  {title,-46} -> {got,-20} {detail}");
    }
}

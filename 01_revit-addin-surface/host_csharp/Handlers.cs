using System.Text.Json.Nodes;
using System.Text.RegularExpressions;

namespace ReleaseGate;

/// <summary>
/// The four tools of the release gate. A teaching sample.
///
/// There is no Revit here and no compiler is invoked — the work is faked so the
/// sample runs on any machine with the .NET SDK. What is real is the SHAPE:
///
///   · validate_addin runs rules that live in JSON, not in this file
///   · it returns every finding it can reach, even when one check errors
///   · build_all_versions reports per-version outcomes, not one boolean
///   · package_release refuses to run when validation has blocking findings
///
/// The last one is the point of the whole sample. A gate that has never
/// rejected anything is decoration.
/// </summary>
public sealed class Handlers
{
    readonly Contracts _c;
    readonly JsonObject _rules;
    readonly JsonObject _matrix;

    // What the last validation concluded. package_release consults this rather
    // than trusting the caller's word that everything was fine.
    readonly Dictionary<string, int> _blockingByProduct = new();

    public Handlers(Contracts contracts)
    {
        _c = contracts;
        _rules = _c.Config("validation-rules.json");
        _matrix = _c.Config("version-matrix.json");
    }

    public Dictionary<string, Func<JsonObject, JsonObject>> Map() => new()
    {
        ["validate_addin"] = ValidateAddin,
        ["build_all_versions"] = BuildAllVersions,
        ["check_store_requirements"] = CheckStoreRequirements,
        ["package_release"] = PackageRelease,
    };

    static string Product(JsonObject args) =>
        args["productPath"]?.GetValue<string>()
        ?? throw new ToolException("BAD_INPUT", "`productPath` is required.");

    List<string> Supported() =>
        _matrix["supported"]!.AsArray().Select(v => v!.GetValue<string>()).ToList();

    List<string> RequestedVersions(JsonObject args, string field)
    {
        var supported = Supported();
        if (args[field] is not JsonArray asked) return supported;

        var wanted = asked.Select(v => v!.GetValue<string>()).ToList();
        var unknown = wanted.Where(v => !supported.Contains(v)).ToList();
        if (unknown.Count > 0)
            // A model will confidently ask for a version that does not exist.
            // The enum in the schema is the cheap gate; this is the real one.
            throw new ToolException("UNSUPPORTED_VERSION",
                $"Not in the version matrix: {string.Join(", ", unknown)}.",
                detail: new JsonObject { ["supported"] = _matrix["supported"]!.DeepClone() });
        return wanted;
    }

    // -- validate ------------------------------------------------------------

    /// <summary>
    /// Runs the rules from validation-rules.json.
    ///
    /// The rules are DATA. Adding one is a pull request against a JSON file
    /// that a release manager who does not write C# can read and approve — and
    /// that is the difference between a gate people maintain and one they
    /// route around.
    /// </summary>
    JsonObject ValidateAddin(JsonObject args)
    {
        var product = Product(args);
        var versions = RequestedVersions(args, "targetVersions");

        var findings = new JsonArray();
        var warnings = new JsonArray();

        foreach (var ruleNode in _rules["rules"]!.AsArray())
        {
            var rule = ruleNode!.AsObject();
            var id = rule["id"]!.GetValue<string>();

            // Stand-in for the real check. Two of the four fail on the sample
            // product on purpose: a validator whose demo is always green
            // teaches the wrong lesson.
            try
            {
                var (passed, note) = FakeCheck(id, product);

                if (!passed)
                    findings.Add(new JsonObject
                    {
                        ["rule"] = id,
                        ["severity"] = rule["severity"]!.DeepClone(),
                        ["message"] = rule["failureMessage"]!.DeepClone(),
                        ["found"] = note,
                    });
            }
            catch (Exception e)
            {
                // onPartialSuccess, honoured. One unreachable check must not
                // discard the three findings we already have — reporting a
                // clean run here would be a lie of omission.
                warnings.Add(new JsonObject
                {
                    ["code"] = "PARTIAL_FAILURE",
                    ["message"] = $"Rule `{id}` could not be evaluated: {e.GetType().Name}. "
                                + "Treat this report as incomplete.",
                    ["item"] = id,
                });
            }
        }

        var blocking = findings.Count(f =>
            f!["severity"]!.GetValue<string>() == "blocking");
        _blockingByProduct[product] = blocking;

        return Envelope.Ok(new JsonObject
        {
            ["product"] = product,
            ["targetVersions"] = new JsonArray(versions.Select(v => (JsonNode)v!).ToArray()),
            ["count"] = findings.Count,
            ["blocking"] = blocking,
            ["findings"] = findings,
            ["rulesEvaluated"] = _rules["rules"]!.AsArray().Count - warnings.Count,
            ["verdict"] = blocking == 0 ? "clear-to-package" : "blocked",
        }, warnings);
    }

    static (bool Passed, string Note) FakeCheck(string ruleId, string product) => ruleId switch
    {
        "version-format" => (true, "1.4.2 in both manifest and assembly"),
        "entitlement-consistency" =>
            (false, "manifest claims `avantleap.sample.pro`, config declares `avantleap.sample`"),
        "installer-privilege" => (true, "asInvoker in both"),
        // The one that costs a full review cycle for a single missing character.
        "privacy-url-resolves" => (false, "HTTP 404 from https://example.invalid/privacy"),
        _ => (true, "not implemented in the sample"),
    };

    // -- build ---------------------------------------------------------------

    /// <summary>
    /// One result per version, never one boolean for the set.
    ///
    /// "The build failed" sends a person to look at five logs. "2023 and 2024
    /// failed, 2025–2027 succeeded" sends them to the two that matter — and the
    /// pattern is the same one the Dynamo sample makes about partial success.
    /// </summary>
    JsonObject BuildAllVersions(JsonObject args)
    {
        var product = Product(args);
        var versions = RequestedVersions(args, "versions");
        var configuration = args["configuration"]?.GetValue<string>() ?? "Release";

        var results = new JsonArray();
        var warnings = new JsonArray();
        var succeeded = 0;

        foreach (var v in versions)
        {
            var tfm = _matrix["targetFramework"]![v]!.GetValue<string>();

            // The framework split at 2025 is where real matrices break: an API
            // that exists on net8.0-windows and not on net48, or the reverse.
            var failed = tfm == "net48" && configuration == "Release";

            results.Add(new JsonObject
            {
                ["version"] = v,
                ["targetFramework"] = tfm,
                ["outcome"] = failed ? "failed" : "succeeded",
                ["detail"] = failed
                    ? "CS0246: type or namespace `ForgeTypeId` not found on net48."
                    : $"{product} built for {v}.",
            });

            if (failed)
                warnings.Add(new JsonObject
                {
                    ["code"] = "PARTIAL_FAILURE",
                    ["message"] = $"{v} did not build: an API used here does not exist on {tfm}.",
                    ["item"] = v,
                });
            else succeeded++;
        }

        return Envelope.Ok(new JsonObject
        {
            ["product"] = product,
            ["configuration"] = configuration,
            ["count"] = succeeded,
            ["attempted"] = versions.Count,
            ["results"] = results,
        }, warnings);
    }

    // -- preview -------------------------------------------------------------

    /// <summary>
    /// The preview half of the pair. Its token is what authorises packaging.
    ///
    /// It reports what packaging WOULD do, in the words a submission reviewer
    /// uses — because a confirmation nobody can read is a confirmation nobody
    /// meaningfully gave.
    /// </summary>
    JsonObject CheckStoreRequirements(JsonObject args)
    {
        var product = Product(args);
        var release = args["releaseVersion"]?.GetValue<string>() ?? "1.0.0";

        if (!Regex.IsMatch(release, "^[0-9]+[.][0-9]+[.][0-9]+$"))
            throw new ToolException("BAD_INPUT",
                "`releaseVersion` must look like 1.4.2.",
                detail: new JsonObject { ["got"] = release });

        var blocking = _blockingByProduct.TryGetValue(product, out var b) ? b : -1;

        return Envelope.Ok(new JsonObject
        {
            ["product"] = product,
            ["releaseVersion"] = release,
            ["lastValidation"] = blocking switch
            {
                -1 => "never validated in this session",
                0 => "clear",
                _ => $"{blocking} blocking finding(s) outstanding",
            },
            ["wouldWrite"] = new JsonArray(
                $"{product}/release/{release}/installer.msi",
                $"{product}/release/{release}/submission-bundle.zip",
                "one append-only audit record"),
            ["manifestFields"] = new JsonObject
            {
                ["privacyPolicyUrl"] = "https://example.invalid/privacy",
                ["descriptionChars"] = 1180,
                ["descriptionLimit"] = 2000,
            },
        });
    }

    // -- the gate ------------------------------------------------------------

    /// <summary>
    /// Packaging refuses while validation has blocking findings.
    ///
    /// The refusal lives HERE and not in the prompt, because a rule stated in a
    /// prompt is a preference and a rule enforced in the host is a rule. On the
    /// sample product this always refuses — which is the demonstration.
    /// </summary>
    JsonObject PackageRelease(JsonObject args)
    {
        var product = Product(args);
        var release = args["releaseVersion"]!.GetValue<string>();

        if (!_blockingByProduct.TryGetValue(product, out var blocking))
            throw new ToolException("PRECONDITION_FAILED",
                "This product has not been validated. Call validate_addin first.",
                detail: new JsonObject { ["product"] = product });

        if (blocking > 0)
            throw new ToolException("PRECONDITION_FAILED",
                $"{blocking} blocking finding(s) outstanding. Fix them and validate again.",
                detail: new JsonObject { ["blocking"] = blocking });

        return Envelope.Ok(new JsonObject
        {
            ["product"] = product,
            ["releaseVersion"] = release,
            ["count"] = 2,
            ["artifacts"] = new JsonArray(
                $"{product}/release/{release}/installer.msi",
                $"{product}/release/{release}/submission-bundle.zip"),
            ["auditRecord"] = "written before this response was returned",
        });
    }
}

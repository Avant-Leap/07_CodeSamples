# Artifacts · Add-in release gate — LO1

A C# .NET 8 MCP server exposing add-in build and deployment. The add-in is the SUBJECT of the tools,
not their output.

| File | Kind | What it is |
|---|---|---|
| `README.md` | 📘 doc | The argument behind the design, in prose. |
| `SKILL.md` | 📘 doc | How to use this folder. Drop into `.claude/skills/` to make it directly usable. |
| `clients/mcp.json` | ⚙ config | Client wiring. Replace `<ABSOLUTE>` and drop into your MCP config. |
| `config/audit-record.schema.json` | 📄 contract | What one audit line must contain. Note what is absent: agent identity. |
| `config/validation-rules.json` | ⚙ config | The four causes that got real submissions rejected. DATA, so a non-C# reviewer can amend a rule. |
| `config/version-matrix.json` | ⚙ config | An explicit list, never a range. Framework changes at 2025. |
| `host_csharp/Contracts.cs` | ▶ runnable | Envelope, `ToolException`, contract loading. The C# twin of contracts.py. |
| `host_csharp/Handlers.cs` | ▶ runnable | The four tools. Replace `FakeCheck` and the build shell-out; keep everything around them. |
| `host_csharp/Program.cs` | ▶ runnable | stdio JSON-RPC by hand. `serve` for a client, `smoke` for the failure script. |
| `host_csharp/ReleaseGate.csproj` | ▶ runnable | .NET 8, no PackageReference. Copies the contracts to output. |
| `host_csharp/Server.cs` | ▶ runnable | The rails: ceiling, manifest selection, envelope, preview→confirm, idempotency, timeout, audit. |
| `host_csharp/Smoke.cs` | ✔ test | Twelve assertions, all of them a guard refusing something. |
| `manifests/p8-addin-release-gate.json` | 📄 contract | One process manifest. |
| `tools/build_all_versions.json` | 📄 contract | One tool definition. |
| `tools/check_store_requirements.json` | 📄 contract | One tool definition. |
| `tools/package_release.json` | 📄 contract | One tool definition. |
| `tools/validate_addin.json` | 📄 contract | One tool definition. |

Runtime output: `audit.log` (append-only, gitignored) and `bin/`/`obj/`.

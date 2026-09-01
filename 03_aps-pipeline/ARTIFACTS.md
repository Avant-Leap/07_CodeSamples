# Artifacts · APS pipeline — LO3

A wiring diagram, not a server design: what must exist per leg before code is worth writing.
No credentials and no network — the calls are faked so it runs anywhere.

| File | Kind | What it is |
|---|---|---|
| `.env.example` | ⚙ config | Credential SHAPES only. Scopes are per leg; the sample never reads them. |
| `README.md` | 📘 doc | The argument behind the design, in prose. |
| `SKILL.md` | 📘 doc | How to use this folder. Drop into `.claude/skills/` to make it directly usable. |
| `clients/mcp.json` | ⚙ config | Client wiring. Replace `<ABSOLUTE>` and drop into your MCP config. |
| `config/activities/cleanup.prod.json` | ⚙ config | A declared Activity. A tool exposes THIS, never a job body. |
| `config/endpoints.json` | ⚙ config | Every external domain touched. The Marketplace manifest wants the same list. |
| `config/engine-versions.json` | ⚙ config | An enum, because a model will invent a plausible version. |
| `config/poll-intervals.json` | ⚙ config | Interval and TTL per job type, with the sample count and p95 behind each. |
| `handlers.py` | ▶ runnable | The tool implementations. Replace the fakes; keep the response shapes. |
| `manifests/p3-cloud-chain.json` | 📄 contract | One process manifest. |
| `tools/automation_create_workitem.json` | 📄 contract | One tool definition. |
| `tools/job_get_status.json` | 📄 contract | One tool definition. |
| `tools/model_export_derivative.json` | 📄 contract | One tool definition. |
| `tools/model_get_metadata.json` | 📄 contract | One tool definition. |

Runtime output: `audit.log` (append-only, gitignored). Create `.env` from `.env.example`; it stays
gitignored.

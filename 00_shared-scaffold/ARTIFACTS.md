# Artifacts · The shared scaffold

The contracts every other folder is built to, the validator that checks them, and the Python host
that runs them. Nothing here is Autodesk-specific.

| File | Kind | What it is |
|---|---|---|
| `README.md` | 📘 doc | The argument behind the design, in prose. |
| `SKILL.md` | 📘 doc | How to use this folder. Drop into `.claude/skills/` to make it directly usable. |
| `contracts/envelope.schema.json` | 📄 contract | The two return shapes and the CLOSED error enum. Copy verbatim; do not add codes locally. |
| `contracts/process.schema.json` | 📄 contract | What a process manifest must declare. `maxTools` maximum is 6, so the ceiling is enforced by schema. |
| `contracts/tool.schema.json` | 📄 contract | The three-sentence description, `sideEffect`, `previewTool`, `idempotencyKey`. |
| `fixtures/broken/manifests/too-many-tools.json` | 🧪 fixture | Deliberately breaks the ceiling. Proof the validator can fail. |
| `fixtures/broken/tools/delete_everything.json` | 🧪 fixture | An unpaired destructive write. Deliberately invalid. |
| `fixtures/broken/tools/make_thing.json` | 🧪 fixture | A create tool with no idempotency key. Deliberately invalid. |
| `host_python/contracts.py` | ▶ runnable | Envelope, `ToolError`, contract loading. Imported by the host AND every handler, by name, so the exception type has one identity. |
| `host_python/server.py` | ▶ runnable | The stdio JSON-RPC host. Stdlib only. Runs 02 and 03 unchanged. |
| `host_python/smoke.py` | ✔ test | Drives both servers over real stdio and asserts the guards REFUSE. |
| `validate.py` | ▶ runnable | Checks a sample folder against all three schemas. `--demo` runs the broken fixtures and goes red on purpose. |

Copy `contracts/` verbatim into a new server. Copy `host_python/` if you want a working server
without writing one. Copy `validate.py` always — a scaffold nobody checks is a suggestion.

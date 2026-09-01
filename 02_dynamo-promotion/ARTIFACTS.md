# Artifacts · Dynamo promotion — LO2

Turning an ageing graph library into an MCP surface, by either of the two promotion routes.
The discriminator between them is deployment governance, not skill.

| File | Kind | What it is |
|---|---|---|
| `README.md` | 📘 doc | The argument behind the design, in prose. |
| `SKILL.md` | 📘 doc | How to use this folder. Drop into `.claude/skills/` to make it directly usable. |
| `clients/mcp.json` | ⚙ config | Client wiring. Replace `<ABSOLUTE>` and drop into your MCP config. |
| `config/scaffold.config.json` | ⚙ config | Promotion settings for the graph→add-in / graph→Python-node routes. |
| `handlers.py` | ▶ runnable | The tool implementations. Replace the fakes; keep the response shapes. |
| `manifests/p2-graph-catalogue.json` | 📄 contract | One process manifest. |
| `tools/get_graph_outputs.json` | 📄 contract | One tool definition. |
| `tools/list_dynamo_packages.json` | 📄 contract | One tool definition. |
| `tools/run_dynamo_graph.json` | 📄 contract | One tool definition. |

Runtime output: `audit.log` (append-only, gitignored).

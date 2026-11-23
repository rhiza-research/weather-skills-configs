## Layout

| Path | Holds | Schema |
| --- | --- | --- |
| `models/<encoded id>.yaml` | One catalog model per file | `schemas/model.json` |
| `skill-packs.yaml` | Skill packs, with pack and skill on/off state | `schemas/skill-packs.json` |
| `connections.yaml` | OpenAI-compatible connections, keyed by base URL | `schemas/connections.json` |
| `settings.yaml` | Tracked non-secret app settings | `schemas/settings.json` |

Install the hook that validates each data file against its schema on commit: `pre-commit install`.

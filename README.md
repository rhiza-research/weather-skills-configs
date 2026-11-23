# weather-skills-configs

The definition of the weather-skills-chat app: its models, skill packs, connections and tracked settings. weather-skills-eval runs the app as defined at one commit of this repo. This repo holds no secrets.

## Layout

| Path | Holds | Schema definition |
| --- | --- | --- |
| `schema.json` | The JSON Schema for every data file, and its version | |
| `models/<encoded id>.yaml` | One catalog model per file | `#/$defs/model_file` |
| `skill-packs.yaml` | Skill packs, with pack and skill on/off state | `#/$defs/skill_packs_file` |
| `connections.yaml` | OpenAI-compatible connections, keyed by base URL | `#/$defs/connections_file` |
| `settings.yaml` | Tracked non-secret app settings | `#/$defs/settings_file` |

## Rules

### Schema version

- `schema.json` carries the version in `x-schema-version`. Every data file names the version it was written for in `schema_version`.
- Adding an optional field keeps the version. A breaking change, such as a rename or removal, bumps it and migrates every data file in the same commit.

### Roles

The schema marks keys with `x-role`:

- `app-input`: given to the app at startup as environment values.
- `app-state`: set by the harness through the app's API after startup.
- `eval-metadata`: used by the eval only. It never reaches the app.

What each file gives the app:

- `models/*.yaml`: each file's `model` is one `CATALOG_MODELS` entry, exactly as `CatalogModelEntry` accepts it. `eval` is eval metadata.
- `skill-packs.yaml`: each pack's `git_url`, `ref` and `enabled_by_default` form its `SKILL_PACKS` entry. A pack's `is_active` and its `skills` are app state. A pack is keyed by `git_url`, a skill by `name`. App ids are never stored. A skill not listed is not checked.
- `connections.yaml`: the keys, in file order, are `OPENAI_API_BASE_URLS`. Each value is that connection's `OPENAI_API_CONFIGS` entry, at the same index. `OPENAI_API_KEYS` comes from the eval, which maps each base URL to its key and lists the keys in the same order.
- `settings.yaml`: each key is the app's environment variable of the same name.

### No secrets

- No data file holds a secret value or a `${...}` reference.
- Connections and settings allow only the non-secret keys the schema names.

### Models

- Every model file has a `base_model_id`.
- The file name is the model id, percent-encoded (every byte except `A-Z a-z 0-9 - . _ ~`), with a leading `.` written as `%2E`, plus `.yaml`. The `id` inside the file is authoritative.
- `organization_id` is `platform` and `visibility` is `public`, the values the app stores for every catalog model.

# weather-skills-configs

The definition of the weather-skills-chat app: its models, skill packs, connections and tracked settings. weather-skills-eval runs the app as defined at one commit of this repo. This repo holds no secrets.

## Layout

| Path | Holds |
| --- | --- |
| `schema.json` | The JSON Schema for every data file, and its version |
| `models/<encoded id>.yaml` | One catalog model per file |
| `skill-packs.yaml` | Skill packs, with pack and skill on/off state |
| `connections.yaml` | OpenAI-compatible connections, keyed by base URL |
| `settings.yaml` | Tracked non-secret app settings |
| `scripts/check.py` | Validates every data file |

## Check

```sh
uv run scripts/check.py
```

It exits 1 and lists every problem when any rule below is broken.

## Rules

### Schema version

- `schema.json` carries the version in `x-schema-version`. Every data file names the version it was written for in `schema_version`.
- Adding an optional field keeps the version. A breaking change, such as a rename or removal, bumps it and migrates every data file in the same commit.
- `x-files` maps each data file to its definition in `$defs`.

### Roles

The schema marks keys with `x-role`:

- `app-input`: given to the app at startup as environment values.
- `app-state`: set by the harness through the app's API after startup.
- `eval-metadata`: used by the eval only. It never reaches the app.

What each file gives the app:

- `models/*.yaml`: each file's `model` is one `CATALOG_MODELS` entry, exactly as `CatalogModelEntry` accepts it. `eval` is eval metadata.
- `skill-packs.yaml`: each pack's `git_url`, `ref` and `enabled_by_default` form its `SKILL_PACKS` entry. A pack's `is_active` and its `skills` are app state. A pack is keyed by `git_url`, a skill by `name`. App ids are never stored. A skill not listed is not checked.
- `connections.yaml`: the keys, in file order (code point order), are `OPENAI_API_BASE_URLS`. Each value is that connection's `OPENAI_API_CONFIGS` entry, at the same index. `OPENAI_API_KEYS` comes from the eval, which maps each base URL to its key and lists the keys in the same order.
- `settings.yaml`: each key is the app's environment variable of the same name.

### No secrets

- No data file holds a secret value or a `${...}` reference.
- Connections and settings allow only the non-secret keys the schema names.

### One file form

- Keys follow the object's `x-key-order`. Keys it does not list, and every key of an object without one, follow in code point order.
- Lists with `x-sort-by` are sorted by that key, ascending, with no duplicates.
- Every key the schema declares with a default is written, even when it holds the default. Free-form maps, such as `params` and connection options, hold only the keys that are set.
- No mapping repeats a key. Every key is a string, and every value is valid JSON.

### Models

- Every model file has a `base_model_id`.
- The file name is the model id, percent-encoded (every byte except `A-Z a-z 0-9 - . _ ~`), with a leading `.` written as `%2E`, plus `.yaml`. The `id` inside the file is authoritative.
- `organization_id` is `platform` and `visibility` is `public`, the values the app stores for every catalog model.

### Model references

Keys marked `x-model-ref` must resolve within the commit:

- `upstream` (`base_model_id`, `meta.fallback_model_id`): a connection in `connections.yaml` serves the id. A connection serves an id unless its `enable` is false, it has a `prefix_id` the id does not start with (followed by `.`), or it has `model_ids` that list neither the id nor the id without the prefix.
- `any` (`TASK_MODEL`, `TASK_MODEL_EXTERNAL`): a model in `models/` has that id, or a connection serves it. An empty value means none.

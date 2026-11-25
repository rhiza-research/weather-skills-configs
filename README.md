# Weather Skills Configs

This repo holds the setup of a [Weather Skills Chat](https://github.com/rhiza-research/weather-skills-chat) app: its models, skill packs, connections and settings. [weather-skills-eval](https://github.com/rhiza-research/weather-skills-eval) reads this repo at one commit and starts the app with that setup for each eval run.

No secrets are stored here. weather-skills-eval's `EVAL_CONNECTION_KEYS` names the environment variable that holds each connection's API key.

## Layout

| Path | Holds | Schema |
| --- | --- | --- |
| `models/<encoded id>.yaml` | One catalog model per file | `schemas/model.json` |
| `skill-packs.yaml` | Skill packs, with pack and skill on/off state | `schemas/skill-packs.json` |
| `connections.yaml` | OpenAI-compatible connections, keyed by base URL | `schemas/connections.json` |
| `settings.yaml` | Tracked non-secret app settings | `schemas/settings.json` |

## What each file sets

- `models/*.yaml`: each file's `model` is one entry of the app's `CATALOG_MODELS`. Each file also needs an `eval` block with a `variant`, which may be `null`. A variant is added in parentheses after the served model in the eval experiment's name. The app never sees it.
- `skill-packs.yaml`: each pack's `git_url`, `ref` and `enabled_by_default` form its `SKILL_PACKS` entry. weather-skills-eval sets the pack's `is_active` and `skills` through the app's API after the app starts.
- `connections.yaml`: each key under `connections` is a base URL in `OPENAI_API_BASE_URLS`. Its value is that connection's `OPENAI_API_CONFIGS` entry.
- `settings.yaml`: each key under `settings` is the app environment variable of that name. It takes only the settings `schemas/settings.json` lists, so add a setting to the schema first.

## Making a change

Edit or add a file, and keep its `schema_version: 1`. Commit and push it. An eval batch runs the commit of the ref you give it.

## Checks

Install the pre-commit hook: `pre-commit install`. On each commit it checks the staged data files against their schemas and scans for secrets with gitleaks. To check every file, run `pre-commit run --all-files`.

## License

MIT. See [LICENSE](LICENSE).

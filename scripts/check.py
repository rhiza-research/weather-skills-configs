# /// script
# requires-python = ">=3.12"
# dependencies = ["jsonschema>=4.26.0", "pyyaml>=6.0.4"]
# ///
"""Check every data file against schema.json, the file form and model references.

Usage: uv run scripts/check.py [repo root]
Prints every problem and exits 1 when any check fails.
"""

import json
import sys
import urllib.parse
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

SECRET_MARK = "${"


def encode_model_id(model_id: str) -> str:
    """The model file's base name: percent-encoded id, with a leading dot encoded so it is never hidden."""
    name = urllib.parse.quote(model_id, safe="")
    return "%2E" + name[1:] if name.startswith(".") else name


def resolve(node, defs):
    while node is not None and "$ref" in node:
        node = defs[node["$ref"].rsplit("/", 1)[1]]
    return node


def child(node, key):
    if not node:
        return None
    properties = node.get("properties", {})
    if key in properties:
        return properties[key]
    extra = node.get("additionalProperties")
    return extra if isinstance(extra, dict) else None


class UniqueKeyLoader(yaml.SafeLoader):
    """Refuses a repeated key, which safe_load would drop silently."""

    def construct_mapping(self, node, deep=False):
        keys = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in keys:
                raise yaml.constructor.ConstructorError(
                    None, None, f"repeated key {key!r}", key_node.start_mark
                )
            keys.add(key)
        return super().construct_mapping(node, deep=deep)


def non_string_keys(value, where):
    """JSON turns every key into a string, so 1 and "1" would collide."""
    found = []
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                found.append(f"{where}/{key}: keys must be strings")
            found += non_string_keys(item, f"{where}/{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found += non_string_keys(item, f"{where}/{index}")
    return found


def form_problems(value, node, defs, where):
    """Key order, list order and missing defaults, per x-key-order, x-sort-by and default."""
    node = resolve(node, defs)
    found = []
    if isinstance(value, dict):
        for key, spec in (node or {}).get("properties", {}).items():
            if "default" in spec and key not in value:
                found.append(f"{where}/{key}: must be written, even at its default")
        order = (node or {}).get("x-key-order", [])
        expected = [k for k in order if k in value] + sorted(
            (k for k in value if k not in order), key=str
        )
        if list(value) != expected:
            found.append(f"{where or '/'}: keys must be in this order: {expected}")
        for key, item in value.items():
            found += form_problems(item, child(node, key), defs, f"{where}/{key}")
    elif isinstance(value, list):
        sort_by = (node or {}).get("x-sort-by")
        if sort_by:
            ids = [item[sort_by] for item in value]
            if any(a >= b for a, b in zip(ids, ids[1:])):
                found.append(
                    f"{where}: items must be sorted by {sort_by}, ascending, with no duplicates"
                )
        items = (node or {}).get("items")
        for index, item in enumerate(value):
            found += form_problems(item, items, defs, f"{where}/{index}")
    return found


def model_refs(value, node, defs, where):
    """(where, kind, value) for every non-empty x-model-ref value."""
    node = resolve(node, defs)
    found = []
    if node and node.get("x-model-ref") and isinstance(value, str) and value:
        found.append((where, node["x-model-ref"], value))
    if isinstance(value, dict):
        for key, item in value.items():
            found += model_refs(item, child(node, key), defs, f"{where}/{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found += model_refs(item, (node or {}).get("items"), defs, f"{where}/{index}")
    return found


def served_by_connection(model_id, connections):
    """Whether a connection would serve this upstream id.

    Follows weather-skills-chat routers/openai.py connection_index_for_model.
    """
    for options in connections.values():
        if not options.get("enable", True):
            continue
        prefix_id = options.get("prefix_id")
        bare = model_id
        if prefix_id:
            if not model_id.startswith(f"{prefix_id}."):
                continue
            bare = model_id[len(prefix_id) + 1 :]
        allowed = options.get("model_ids") or []
        if allowed and bare not in allowed and model_id not in allowed:
            continue
        return True
    return False


def main(argv) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent.parent
    problems = []

    # 1. The schema itself
    try:
        schema = json.loads((root / "schema.json").read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
    except (OSError, ValueError) as e:
        print(f"schema.json: {e}", file=sys.stderr)
        return 1
    except SchemaError as e:
        print(f"schema.json: {e.message}", file=sys.stderr)
        return 1
    defs = schema["$defs"]
    version = schema["x-schema-version"]
    if defs["schema_version"]["const"] != version:
        problems.append(
            f"schema.json: $defs/schema_version is {defs['schema_version']['const']}, "
            f"x-schema-version is {version}"
        )

    # 2. Data files, by x-files
    files = {}
    for pattern, pointer in schema["x-files"].items():
        matches = sorted(p for p in root.glob(pattern) if p.is_file())
        if not matches:
            problems.append(f"{pattern}: missing")
        for path in matches:
            files[path] = pointer
    models_dir = root / "models"
    for path in sorted(models_dir.iterdir()) if models_dir.is_dir() else []:
        # Dotfiles are skipped: an encoded id never starts with a dot.
        if path not in files and not path.name.startswith("."):
            problems.append(f"models/{path.name}: models/ holds only <encoded id>.yaml files")

    # 3. Each file: no secret references, schema, JSON-compatible values, form
    docs = {}
    for path, pointer in files.items():
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            problems.append(f"{rel}: not UTF-8: {e}")
            continue
        if SECRET_MARK in text:
            problems.append(f"{rel}: holds a ${{...}} reference; secrets never go in this repo")
        try:
            data = yaml.load(text, Loader=UniqueKeyLoader)
        except yaml.YAMLError as e:
            problems.append(f"{rel}: not valid YAML: {e}")
            continue
        validator = Draft202012Validator({"$defs": defs, "$ref": pointer})
        errors = sorted(validator.iter_errors(data), key=lambda e: list(map(str, e.absolute_path)))
        for error in errors:
            where = "/" + "/".join(map(str, error.absolute_path))
            problems.append(f"{rel}: {where}: {error.message}")
        if errors:
            continue
        # The harness passes values to the app as JSON.
        key_problems = non_string_keys(data, "")
        problems += [f"{rel}: {p}" for p in key_problems]
        try:
            json.dumps(data, allow_nan=False)
        except (TypeError, ValueError) as e:
            problems.append(f"{rel}: a value is not JSON: {e}")
            continue
        if key_problems:
            continue
        problems += [f"{rel}: {p}" for p in form_problems(data, {"$ref": pointer}, defs, "")]
        docs[rel] = (data, pointer)

    # 4. Model file names
    catalog_ids = set()
    folded = {}
    for rel, (data, _) in docs.items():
        if not rel.startswith("models/"):
            continue
        model_id = data["model"]["id"]
        catalog_ids.add(model_id)
        # Case-insensitive file systems would store both ids in one file.
        other = folded.setdefault(model_id.casefold(), model_id)
        if other != model_id:
            problems.append(f"{rel}: id {model_id!r} differs from {other!r} only in case")
        expected = f"models/{encode_model_id(model_id)}.yaml"
        if rel != expected:
            problems.append(f"{rel}: id {model_id!r} must be in {expected}")

    # 5. Model references, once every file is valid, so a broken file adds no noise
    if not problems:
        connections = docs["connections.yaml"][0]["connections"]
        for rel, (data, pointer) in docs.items():
            for where, kind, value in model_refs(data, {"$ref": pointer}, defs, ""):
                if served_by_connection(value, connections):
                    continue
                if kind == "any" and value in catalog_ids:
                    continue
                target = "a connection" if kind == "upstream" else "a model in models/ or a connection"
                problems.append(f"{rel}: {where}: {value!r} is not served by {target}")

    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        return 1
    print(f"OK: {len(docs)} data files, schema version {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

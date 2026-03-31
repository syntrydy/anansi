"""
Validation script for country context pack JSON files.

Checks each *.json file (except schema.json) in the data directory against:
  1. The JSON schema definition in schema.json (structural validation)
  2. Pydantic CountryData model (semantic validation)
  3. Minimum content requirements (non-empty lists, populated strings)

Exit code 0 on success, 1 on any failure.

Usage:
    uv run python scripts/validate_context_packs.py
"""

import json
import sys
from pathlib import Path

# Resolve paths relative to repo root regardless of invocation directory.
REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "src" / "anansi" / "context" / "data"
SCHEMA_PATH = DATA_DIR / "schema.json"

# Minimum number of items expected in each list field.
MIN_LIST_LENGTH = 4


def _check_min_lengths(data: dict, country: str) -> list[str]:
    """Return a list of human-readable issues for fields below the minimum length."""
    issues: list[str] = []

    def check(field_path: str, value: list) -> None:  # type: ignore[type-arg]
        if len(value) < MIN_LIST_LENGTH:
            issues.append(
                f"  {field_path}: only {len(value)} item(s), expected >= {MIN_LIST_LENGTH}"
            )

    check("names.male", data.get("names", {}).get("male", []))
    check("names.female", data.get("names", {}).get("female", []))
    check("places.cities", data.get("places", {}).get("cities", []))
    check("places.rivers", data.get("places", {}).get("rivers", []))
    check("places.landmarks", data.get("places", {}).get("landmarks", []))

    for sub in ("food", "clothing", "housing", "transport", "animals"):
        check(f"culture.{sub}", data.get("culture", {}).get(sub, []))

    check("avoids", data.get("avoids", []))

    if not data.get("art_style_cues", "").strip():
        issues.append("  art_style_cues: empty string")
    if not data.get("country", "").strip():
        issues.append("  country: empty string")

    return issues


def main() -> None:
    if not DATA_DIR.exists():
        print(f"ERROR: data directory not found: {DATA_DIR}", file=sys.stderr)
        sys.exit(1)

    # Load JSON Schema (optional dependency: jsonschema)
    schema: dict | None = None
    try:
        import jsonschema  # type: ignore[import]

        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except ImportError:
        print(
            "WARNING: jsonschema not installed — skipping structural schema validation.\n"
            "         Install with: uv add --dev jsonschema",
            file=sys.stderr,
        )
    except FileNotFoundError:
        print(f"WARNING: schema.json not found at {SCHEMA_PATH}", file=sys.stderr)

    # Load CountryData model (always available)
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from anansi.core.models.context import CountryData
    from pydantic import ValidationError

    json_files = sorted(
        p for p in DATA_DIR.glob("*.json") if p.name != "schema.json"
    )

    if not json_files:
        print(f"ERROR: no country JSON files found in {DATA_DIR}", file=sys.stderr)
        sys.exit(1)

    failed = False

    for path in json_files:
        print(f"Validating {path.name} ...", end=" ")
        try:
            raw: dict = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"FAIL\n  JSON parse error: {exc}")
            failed = True
            continue

        # 1. JSON Schema validation
        if schema is not None:
            try:
                jsonschema.validate(instance=raw, schema=schema)
            except jsonschema.ValidationError as exc:
                print(f"FAIL\n  Schema error: {exc.message}")
                failed = True
                continue

        # 2. Pydantic validation
        try:
            CountryData.model_validate(raw)
        except ValidationError as exc:
            print(f"FAIL\n  Pydantic error: {exc}")
            failed = True
            continue

        # 3. Minimum content check
        issues = _check_min_lengths(raw, path.stem)
        if issues:
            print("WARN")
            for issue in issues:
                print(issue)
        else:
            print("OK")

    if failed:
        print("\nValidation FAILED — fix the errors above before committing.")
        sys.exit(1)
    else:
        print("\nAll context packs are valid.")


if __name__ == "__main__":
    main()

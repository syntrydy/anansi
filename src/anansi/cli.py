"""
Run the teaching pipeline from the terminal; prints JSON (similar to an API response body).

Examples::

    ANANSI_MOCK_PIPELINE=1 uv run python -m anansi.cli
    uv run python -m anansi.cli --mock --topic Photosynthesis --country Kenya
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run Anansi pipeline and print package JSON.")
    p.add_argument(
        "--mock",
        action="store_true",
        help="Use mock image/audio (no BFL or Google credentials).",
    )
    p.add_argument("--topic", default="Photosynthesis", help="Lesson topic")
    p.add_argument(
        "--country",
        default="Kenya",
        help="Country (Kenya, Nigeria, Senegal, Ghana, Cameroon)",
    )
    p.add_argument("--grade", type=int, default=5, help="Grade level")
    p.add_argument("--language", default="English", help="Instruction language")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    if args.mock:
        os.environ["ANANSI_MOCK_PIPELINE"] = "1"

    from anansi.agent.graph import run_pipeline
    from anansi.core.models.state import initialize_state

    initial = initialize_state(
        {
            "topic": args.topic,
            "country": args.country,
            "grade": args.grade,
            "language": args.language,
            "extra_context": {},
        }
    )

    try:
        final = asyncio.run(run_pipeline(initial))
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)

    package = final.get("package")
    if package is None:
        print(json.dumps({"error": "No package in result", "keys": list(final.keys())}))
        sys.exit(1)

    print(json.dumps(package, indent=2))


if __name__ == "__main__":
    main()

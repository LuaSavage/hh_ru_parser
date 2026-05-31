#!/usr/bin/env python3
"""Extract key_skills from a golang vacancies dump JSON.

Output format: list of lists, one skills list per vacancy (same order as input).

Usage:
    python examples/extract_skills.py
    python examples/extract_skills.py output/golang_50_vacancies.json -o output/skills.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def normalize_skills(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return [part.strip() for part in raw.split(",") if part.strip()]
    if isinstance(raw, list):
        skills: list[str] = []
        for item in raw:
            if isinstance(item, str) and item.strip():
                skills.append(item.strip())
            elif isinstance(item, dict):
                name = item.get("name")
                if isinstance(name, str) and name.strip():
                    skills.append(name.strip())
        return skills
    return []


def extract_skills_lists(payload: dict[str, Any]) -> list[list[str]]:
    skills_by_vacancy: list[list[str]] = []
    for entry in payload.get("vacancies", []):
        vacancy = entry.get("vacancy", entry)
        skills_by_vacancy.append(normalize_skills(vacancy.get("key_skills")))
    return skills_by_vacancy


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract key_skills from vacancies JSON dump.")
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        default=Path("output/golang_50_vacancies.json"),
        help="Input JSON from vacancy dump script",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("output/golang_50_skills.json"),
        help="Output JSON path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    skills_lists = extract_skills_lists(payload)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(skills_lists, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    non_empty = sum(1 for skills in skills_lists if skills)
    total_skills = sum(len(skills) for skills in skills_lists)
    print(f"vacancies: {len(skills_lists)}")
    print(f"with skills: {non_empty}")
    print(f"total skill entries: {total_skills}")
    print(f"saved: {args.output}")


if __name__ == "__main__":
    main()

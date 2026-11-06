"""Compare package dependency names across manifests (requires Python 3.11+)."""
from pathlib import Path
import re
import sys
import tomllib


ROOT = Path(__file__).resolve().parents[1]


def dependency_names(requirements: list[str]) -> set[str]:
    names = set()
    for requirement in requirements:
        match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", requirement)
        if match is None:
            raise ValueError(f"Missing package name in requirement: {requirement!r}")
        names.add(re.sub(r"[-_.]+", "-", match.group(1)).lower())
    return names


def main() -> int:
    with (ROOT / "pyproject.toml").open("rb") as source:
        project = tomllib.load(source)
    with (ROOT / "briefcase.toml").open("rb") as source:
        briefcase = tomllib.load(source)
    project_names = dependency_names(project["project"]["dependencies"])
    briefcase_names = dependency_names(briefcase["tool"]["briefcase"]["app"]["nfc_tools"]["requires"])
    if project_names != briefcase_names:
        print(f"Only in pyproject.toml: {', '.join(sorted(project_names - briefcase_names)) or '(none)'}")
        print(f"Only in briefcase.toml: {', '.join(sorted(briefcase_names - project_names)) or '(none)'}")
        return 1
    print(f"Dependency names match ({len(project_names)} packages).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

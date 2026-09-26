"""Check the four release version declarations without extra dependencies."""
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]


def read_version(path: str, key: str, section: str | None = None) -> str:
    text = (ROOT / path).read_text(encoding="utf-8")
    if section is not None:
        match = re.search(
            rf"^\[{re.escape(section)}\][ \t]*\n(.*?)(?=^\[|\Z)",
            text,
            re.MULTILINE | re.DOTALL,
        )
        if match is None:
            raise ValueError(f"{path}: missing [{section}] section")
        text = match.group(1)
    matches = re.findall(rf"^{re.escape(key)}\s*=\s*['\"]([^'\"]+)['\"]", text, re.MULTILINE)
    if len(matches) != 1:
        raise ValueError(f"{path}: expected one {key} declaration")
    return matches[0]


def main() -> int:
    versions = {
        "VERSION": (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        "pyproject.toml": read_version("pyproject.toml", "version", "project"),
        "briefcase.toml": read_version("briefcase.toml", "version", "tool.briefcase"),
        "src/nfc_tools/version.py": read_version("src/nfc_tools/version.py", "__version__"),
    }
    for path, version in versions.items():
        print(f"{path}: {version}")
    if not versions["VERSION"] or len(set(versions.values())) != 1:
        print("Version declarations do not match.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

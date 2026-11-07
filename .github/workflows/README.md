# Continuous integration workflows

`ci.yml` runs the Python test matrix on Linux, Windows, and macOS, checks versions/dependency names and Ruff references, validates browser scripts, builds a wheel, and smoke-tests installed entry points/assets.

Dependencies: GitHub Actions checkout/setup-python, `pyproject.toml` development dependencies, Node for browser checks, and commands from [scripts](../../scripts/README.md). The workflow is triggered by pushes and pull requests. Keep local check instructions in [README_DEV.md](../../README_DEV.md) consistent with it.

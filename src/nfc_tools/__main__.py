"""Allow `python -m nfc_tools` to run the CLI."""

# Role: Module launcher for python -m nfc_tools.
# Dependencies: cli.main dispatches commands using Click.
from .cli import main

if __name__ == "__main__":
    main()

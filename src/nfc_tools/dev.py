"""Dedicated development launcher; choose the profile before importing the app."""

# Role: Selects the isolated development profile before launching the GUI.
# Dependencies: Environment variables and paths establish the profile; app.main launches
# it.
import os


def main():
    os.environ["NFC_TOOLS_PROFILE"] = "dev"
    from .paths import dev_output_root
    dev_output_root().mkdir(parents=True, exist_ok=True)
    from .app import main as launch
    launch()


if __name__ == "__main__":
    main()

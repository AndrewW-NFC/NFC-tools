"""Open a native folder picker for local save-location settings."""
from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path

from .paths import recordings_root_path


class FolderPickerUnavailable(RuntimeError):
    """Raised when no local folder picker can be opened."""


def choose_directory(current_path: str | None = None, *, title: str = "Choose folder") -> str | None:
    """Return a directory selected by the user, or None if they cancel.

    The Settings page runs in a browser, whose built-in directory picker cannot
    reliably return a normal filesystem path. This helper asks the local
    operating system to show its native folder chooser instead.
    """
    initial_dir = _initial_directory(current_path)
    system = platform.system()

    if system == "Darwin":
        selected = _choose_with_osascript(initial_dir, title)
    elif system == "Windows":
        selected = _choose_with_powershell(initial_dir, title)
    else:
        selected = _choose_with_zenity(initial_dir, title)

    if selected is None:
        return None
    return _normalize_selected_path(selected)


def _initial_directory(current_path: str | None) -> Path:
    candidate = recordings_root_path(current_path)
    if candidate.exists():
        return candidate

    parent = candidate
    while parent != parent.parent:
        parent = parent.parent
        if parent.exists():
            return parent

    return Path.home()


def _normalize_selected_path(path: str) -> str:
    text = path.strip()
    if not text:
        return ""
    return str(Path(text).expanduser())


def _choose_with_osascript(initial_dir: Path, title: str) -> str | None:
    if not shutil.which("osascript"):
        return _choose_with_tkinter(initial_dir, title)

    script = """
on run argv
  set promptText to item 1 of argv
  set defaultPath to item 2 of argv
  set selectedFolder to choose folder with prompt promptText default location POSIX file defaultPath
  return POSIX path of selectedFolder
end run
"""
    result = subprocess.run(
        ["osascript", "-e", script, title, str(initial_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return result.stdout
    if "User canceled" in result.stderr:
        return None
    raise FolderPickerUnavailable(result.stderr.strip() or "Folder chooser could not be opened.")


def _choose_with_powershell(initial_dir: Path, title: str) -> str | None:
    shell = shutil.which("powershell.exe") or shutil.which("powershell") or shutil.which("pwsh")
    if not shell:
        return _choose_with_tkinter(initial_dir, title)

    command = r"""
Add-Type -AssemblyName System.Windows.Forms
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$dialog = New-Object System.Windows.Forms.FolderBrowserDialog
$dialog.Description = $args[0]
$dialog.SelectedPath = $args[1]
$dialog.ShowNewFolderButton = $true
$result = $dialog.ShowDialog()
if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
  Write-Output $dialog.SelectedPath
  exit 0
}
exit 2
"""
    result = subprocess.run(
        [shell, "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass", "-Command", command, title, str(initial_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return result.stdout
    if result.returncode == 2:
        return None
    raise FolderPickerUnavailable(result.stderr.strip() or "Folder chooser could not be opened.")


def _choose_with_zenity(initial_dir: Path, title: str) -> str | None:
    zenity = shutil.which("zenity")
    if not zenity:
        return _choose_with_tkinter(initial_dir, title)

    result = subprocess.run(
        [zenity, "--file-selection", "--directory", f"--title={title}", f"--filename={initial_dir}/"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return result.stdout
    if result.returncode == 1:
        return None
    raise FolderPickerUnavailable(result.stderr.strip() or "Folder chooser could not be opened.")


def _choose_with_tkinter(initial_dir: Path, title: str) -> str | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as exc:
        raise FolderPickerUnavailable("No local folder chooser is available on this system.") from exc

    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
    except tk.TclError:
        pass

    try:
        selected = filedialog.askdirectory(
            parent=root,
            title=title,
            initialdir=str(initial_dir),
            mustexist=True,
        )
    except Exception as exc:
        raise FolderPickerUnavailable("Folder chooser could not be opened.") from exc
    finally:
        root.destroy()

    return selected or None

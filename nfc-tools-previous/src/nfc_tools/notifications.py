"""Cross-platform desktop notifications. Falls back to logging."""
from __future__ import annotations

import platform
import shutil
import subprocess
import threading
import wave
from pathlib import Path

from .logging_setup import get

log = get("notify")


def play_completion_chime() -> None:
    """Play the bundled batch chime without delaying processing or raising errors."""
    def play():
        try:
            path = Path(__file__).parent / "data" / "sounds" / "slow-ding.wav"
            if platform.system() == "Darwin":
                subprocess.run(["/usr/bin/afplay", str(path)], check=True, timeout=10,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif platform.system() == "Windows":
                import winsound
                winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_NODEFAULT)
            else:
                import numpy as np
                import sounddevice as sd
                with wave.open(str(path), "rb") as audio:
                    samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2")
                    with sd.OutputStream(samplerate=audio.getframerate(), channels=1,
                                         dtype="int16") as stream:
                        stream.write(samples.reshape(-1, 1))
        except Exception as exc:  # noqa: BLE001 — optional audio must never fail processing
            log.debug("completion chime failed: %s", exc)

    try:
        threading.Thread(target=play, name="nfc-completion-chime", daemon=True).start()
    except Exception as exc:  # noqa: BLE001 — optional audio must never fail processing
        log.debug("could not start completion chime: %s", exc)


def notify(title: str, message: str) -> None:
    system = platform.system()
    try:
        if system == "Darwin" and shutil.which("osascript"):
            script = f'display notification "{message}" with title "{title}"'
            subprocess.run(["osascript", "-e", script], check=False, timeout=5)
            return
        if system == "Linux" and shutil.which("notify-send"):
            subprocess.run(["notify-send", title, message], check=False, timeout=5)
            return
        if system == "Windows":
            try:
                from winotify import Notification  # type: ignore
                Notification(app_id="NFC Tools", title=title, msg=message).show()
                return
            except ImportError:
                pass
    except Exception as e:  # noqa: BLE001
        log.debug("notification failed: %s", e)
    log.info("[notify] %s — %s", title, message)

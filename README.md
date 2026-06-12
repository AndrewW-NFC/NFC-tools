## Running NFC Tools after installation

You only need to install NFC Tools once. After that, each time you want to use it, open a new Terminal or PowerShell window, go back to the NFC Tools folder, activate the virtual environment, and start the app.

### macOS or Linux

If the NFC Tools folder is on your Desktop:

```bash
cd ~/Desktop/NFC-tools
source .venv/bin/activate
nfc-tools
```

### Windows PowerShell

If the NFC Tools folder is on your Desktop:

```powershell
cd $HOME\Desktop\NFC-tools
.\.venv\Scripts\Activate.ps1
nfc-tools
```

The app should open in your browser. If it does not, open this address manually:

```text
http://127.0.0.1:8765/
```

Keep the Terminal or PowerShell window open while NFC Tools is running. To stop the app, return to that window and press:

```text
Control-C
```

### Why do I need to activate `.venv` each time?

The `.venv` folder is NFC Tools’ private Python environment. It contains the installed `nfc-tools` and `nfc` commands. A new Terminal window does not automatically know about that environment, so you activate it again each time you come back to use the app.

You do not need to reinstall NFC Tools unless you delete the folder, delete `.venv`, or want to update the code.

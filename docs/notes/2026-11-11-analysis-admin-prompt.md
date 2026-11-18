# Administrator prompt during unattended analysis

User reported a macOS dialog requesting administrator access for a script started
by python3.13, possibly when analysis starts.

Initial code inspection identified the optional `analyze_with_lid_closed` setting as the
trigger: analysis calls `SleepPreventer.start(allow_closed_lid=True)`, which uses
AppleScript administrator authorization to run the guarded `pmset disablesleep`
override. Ordinary macOS sleep prevention uses `caffeinate` without elevation.
The screenshot alone does not establish the setting or process state at that time.

Existing workaround: disable Settings → Power & battery → Continue analysis with
the laptop lid closed, retain Keep awake for recording and analysis, and save
before the next analysis/import. Keep the lid open; the screen may sleep.
Declining authorization allows analysis to continue without the lid override.

The user subsequently explicitly requested the alternative authorization design,
with no System Settings setup. Implemented an in-app authorization button that
starts a narrowly scoped privileged helper for the current app process. Approval
is reused across analyses until NFC Tools quits. Approval alone leaves sleep
settings unchanged; each analysis lease applies and restores its own override.
Analysis never prompts for authorization, and falls back to ordinary sleep
prevention if no authorized helper is available. No password is stored and no
persistent service or sudo exemption is installed. Users must authorize again
after reopening NFC Tools. Existing preferences were not changed.

Regression coverage uses a fake power command to verify repeated/overlapping
leases, idle behavior, app exit, owner crash, restoration failure, and the absence
of authorization prompts from analysis. Actual macOS password-dialog and closed-lid
hardware behavior still require a manual smoke test.

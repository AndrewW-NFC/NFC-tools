# Closed-lid analysis technical details

For setup instructions, see [Automated analysis](../README.md#automated-analysis).

## macOS sleep prevention

NFC Tools temporarily disables system sleep during analysis with `pmset`. An
independent watchdog restores the previous setting after analysis, cancellation,
or app exit. Concurrent analyses share the override until the last one finishes.

Authorization lasts until NFC Tools quits and covers subsequent analyses in that
app session. Authorizing alone does not change sleep settings or enable the
closed-lid checkbox. Analysis never opens an administrator prompt; without prior
authorization, it continues with ordinary sleep prevention and the lid must stay
open. The session log explains authorization failures.

## Restoring normal sleep manually

If macOS loses power or the privileged watchdog is forcibly killed, automatic
restoration cannot run. To re-enable normal sleep in that case, run
`sudo pmset disablesleep 0` and remove the stale guard with
`sudo rmdir /var/run/nfc-tools-closed-lid.lock`.

## Linux lid inhibition

Linux uses a systemd lid inhibitor. Desktop power policies may override it.

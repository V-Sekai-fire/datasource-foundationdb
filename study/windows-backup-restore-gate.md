# Windows backup/restore gate: four bugs, one real fix

seaweedfs's `build-weed.yml` gate (FDB 7.3 + weed + S3 + restart + desync) kept failing stage 7
(fdbbackup, restore into a second cluster, compare the key) on the Windows runner, before and
after datasource-foundationdb#17 (the `OPEN_UNBUFFERED` assertion fix). Four separate bugs were
layered on top of each other; untangling them took six dispatches on the gate and one on this
fork.

## #17's fix: confirmed working, not the cause of the remaining failures

`OPEN_UNBUFFERED` assertion count across gate runs:

| Run | Tag | Assertion count |
| --- | --- | --- |
| Before #17 | `dev.3` | 5 |
| After #17 | `dev.4` | 0 (every run since) |

The fix is real and verified gone. Everything below is a separate, pre-existing problem in the
gate script and in `AsyncFileWinASIO`, independent of #17.

## Three bugs in the gate script itself (seaweedfs#7)

1. `fdbbackup status`'s real completion text is `"the previous backup ... completed at version
   N"`, never the literal phrase `"has completed"` the script grepped for. Destined to time out
   regardless of platform or backup health.
2. `fdbbackup start -d <URL>` writes to `<URL>/backup-<timestamp>/`, not `<URL>` itself.
   `fdbrestore -r` was given the bare container path; FDB reports `"not restorable to any
   version"` for that, which Windows's buffered-I/O error path reported as the far less legible
   `"Fatal Error: Disk i/o operation failed"` — a second, *different* bug (below) wearing the
   same error text.
3. A restore submitted to a destination cluster needs a `backup_agent` running against *that*
   cluster, not only the source one. Without it the restore sits `queued` forever
   (`CurrentVersion: -1`). Only one agent existed in the gate.

A fourth, cosmetic bug compounded the diagnosis: `Wait-Until { $status = ...; ... }` assigns
`$status` inside a scriptblock invoked via `& $t`, which does not propagate to the calling scope
in PowerShell — so `Check`'s own diagnostic line was blank on every failure, regardless of what
`fdbbackup`/`fdbrestore` actually printed. All four fixed in seaweedfs#7.

Local verification before touching CI: built `fdbserver`/`fdbcli`/`fdbbackup` (+ `backup_agent`/
`fdbrestore` hardlinks) via pixi on macOS, matching this fork's own macOS CI recipe (661s build,
12 cores). Reproduced bugs 1-3 exactly (identical error text) in a bash harness, fixed them,
reran end-to-end: `queued -> starting -> running -> completed`, restored key read back correctly.
Installed PowerShell Core locally and ran the corrected logic against stub binaries printing the
real captured text, catching bug 4 before it ever reached CI.

## Disproven: Windows networking / Defender theory

After #7, the gate still failed with `fdbbackup status` stuck at `"is in progress (just
started)"` past a 180s poll (raised from 90s; see seaweedfs#8, superseded). The source
`fdbserver`'s own trace showed a new TCP connection arriving and being torn down roughly once per
second for the whole window (`ConnectionFrom -> ConnectionClosed, Error=connection_failed
"Network connection failed" -> PeerDestroy`), with `BackupWorkerDoneRequests` at zero throughout.
That pattern, plus one-shot `fdbcli`/`fdbbackup` CLI calls connecting fine every time, looked like
Defender or the firewall reacting to the newly-introduced `backup_agent.exe`/`fdbrestore.exe`
binaries (seaweedfs#9: `Add-MpPreference -ExclusionProcess`, `New-NetFirewallRule` for every FDB/
weed binary).

Dispatched and disproven directly: identical `connection_failed` storm, same ~1/s rate, same
total count (183 events, then 366 across both clusters), with the exclusions in place and no
"note:" error lines from the exclusion code (meaning it applied without error and simply had no
effect). The storm also reproduced on a brand-new destination cluster that was never restarted,
ruling out a restart/stale-port theory too.

## The real cause: `backup_agent` traces nothing by default

`backup_agent --help` documents trace logging as off unless `--log` is passed explicitly. Every
prior `agent.out`/`agent.err` being 0 bytes meant "nothing printed to the console", not "nothing
happened" — there was never any visibility into `backup_agent`'s own view of the failure.
seaweedfs#10 adds `--log --logdir <dir> --loggroup agent --knob_min_trace_severity=1` to both
`backup_agent` invocations (source and destination) and uploads the resulting trace dirs as gate
artifacts. Verified locally first: the same flags on macOS produce a full
`FileBackupSnapshotDispatchStats` / `FileBackupWroteSnapshotManifest` / `ClearBackup` trace and
the backup completes end-to-end.

On the real Windows run, `backup_agent` connected to the cluster successfully this time
(`ConnectionEstablished`, `ConnectedOutgoing`, no failure at all in its own trace) — the earlier
`connection_failed` storm on the *server* side was real but unrelated noise, not caused by
`backup_agent` and not blocking it. The actual failure, now visible for the first time:

```
FileOpenError: Error="io_error" ErrorDescription="Disk i/o operation failed"
               ErrorCode="1510" WinErrorCode="3" (ERROR_PATH_NOT_FOUND)
File="...\backup-<timestamp>\properties/encryption_metadata"
-> WriteEncryptionMetadataReadError -> TaskBucketExecuteFailure -> FileBackupError
```

`fdbclient/BackupContainerFileSystem.actor.cpp`'s `writeEncryptionMetadataIfNotExists` reads
`properties/encryption_metadata`, expects `error_code_file_not_found` when it doesn't exist yet
(the normal case for a brand-new backup container whose `properties/` subfolder has never been
created), and rethrows anything else as fatal. `fdbrpc/include/fdbrpc/AsyncFileWinASIO.actor.h`'s
`open()` only mapped `ERROR_FILE_NOT_FOUND` (leaf missing) to `file_not_found()`; the distinct
Windows code for "a parent directory is missing" — `ERROR_PATH_NOT_FOUND` — fell through to the
generic `io_error()`. POSIX's `ENOENT` covers both cases identically, so this never surfaced on
Linux or macOS; on Windows, every first-ever local-directory backup hit it.

Not a guessed fix: this fork's own `flow/Platform.actor.cpp` already checks both
`ERROR_FILE_NOT_FOUND` and `ERROR_PATH_NOT_FOUND` together in two other call sites (its
`createDirectory` retry, and a third). datasource-foundationdb#21 adds the same pair to
`AsyncFileWinASIO::open`, matching the codebase's own established idiom for "not found" on
Windows.

Could not compile-test this header locally — it's `#ifdef _WIN32`-guarded and there is no local
Windows machine. Verified instead by reproducing the exact symptom on the real Windows CI runner
(via #10's newly-enabled `backup_agent` trace) and cross-checking the fix against the fork's own
existing convention for the identical pair of error codes. #21's `only=windows` dispatch and its
full `pull_request`-triggered matrix (linux/macos/windows/windows-flowquic) all passed; the
merge-queue's `merge_group` re-verification is the final gate before `main`.

## Summary

| Bug | Where | Fix |
| --- | --- | --- |
| `OPEN_UNBUFFERED` assertion on restore | `AsyncFileWinASIO.actor.h` | datasource-foundationdb#17 (prior work) |
| Wrong "has completed" regex | `build-weed.yml` | seaweedfs#7 |
| Bare container path passed to restore | `build-weed.yml` | seaweedfs#7 |
| No destination-side `backup_agent` | `build-weed.yml` | seaweedfs#7 |
| `$status` scoping swallowed diagnostics | `build-weed.yml` | seaweedfs#7 |
| 90s poll too tight for the Windows runner | `build-weed.yml` | seaweedfs#8 (superseded into #10) |
| Defender/firewall theory | `build-weed.yml` | seaweedfs#9 (disproven, superseded into #10) |
| No `backup_agent` trace visibility | `build-weed.yml` | seaweedfs#10 |
| `ERROR_PATH_NOT_FOUND` mis-mapped to `io_error` | `AsyncFileWinASIO.actor.h` | datasource-foundationdb#21 |

Not yet confirmed: the actual backup/restore scenario passing end-to-end on Windows with #21's
fix in a published release. That needs a new `datasource-foundationdb` release built from a
commit including #21, then a `seaweedfs` gate dispatch pointed at it — the next step once #21
lands on `main`.

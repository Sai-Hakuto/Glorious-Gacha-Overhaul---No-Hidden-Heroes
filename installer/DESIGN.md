# GGO No Hidden Heroes GitHub Downloader design

## Problem

Nexus cannot accept the 96 MB GGO payload as the primary file. Users still
need a simple installation path with visible progress and without manually
copying a large release archive.

## Desired state

A single, standalone `GGO_No_Hidden_Heroes_Installer.exe` must be placed in the DragonSword game
root next to `DSClient.exe` and double-clicked. It refuses to operate from any
other directory. It opens a Windows UI, resolves the latest
published GitHub release, downloads the one matching main GGO ZIP, verifies the
GitHub-provided SHA-256 digest, safely applies it to the game directory, and
performs the same local configuration as `INSTALL.cmd`. After the Control Panel
is activated, the same UI offers to download, verify, and enable Update Guard.

The executable is built from readable standard-library Python with PyInstaller,
following the existing DragonSword Guard packaging model. It must not require a
local Python runtime, administrator rights, or GitHub credentials.

## Safety boundaries

- Accept only the fixed public repository and exactly one asset matching
  `DragonSword_GGO_No_Hidden_Heroes_YYYYMMDD.zip`.
- Require a GitHub `sha256:` digest and verify it before extracting anything.
- Require `DSClient.exe`, the shipping executable, and `DS/Content/Paks` in the
  selected game root.
- Refuse installation while the game is running.
- Read DragonSword Guard state and refuse only when the selected game root is
  the protected root. A Guard protecting another test copy is not relevant.
- Reject absolute paths, drive-qualified paths, and `..` traversal in ZIP
  entries. Every resolved output path must remain below the selected root.
- Extract to staging first. Do not write downloaded bytes directly into the
  game directory.
- Back up every pre-existing destination file before the apply phase. Record a
  machine-readable backup manifest and roll file changes back if apply fails.
- Preserve existing runtime/state files that are not present in the release.
- Do not silently replace Control Plane registration belonging to another game
  copy. Treat that as a conflict unless system integration is explicitly
  skipped for an isolated test.

## User flow

1. User places the EXE in the game root and opens it.
2. The public GUI accepts only its own containing directory as the game root.
   If `DSClient.exe`, the shipping executable, or the vanilla `Paks` directory
   is missing there, it reports that the game was not found and makes no changes.
3. User clicks `Download and install`.
4. The UI shows release discovery, byte download progress, hash verification,
   extraction, backup/apply, configuration, and final verification.
5. The installer activates the Control Panel and verifies its configuration.
6. Success offers Update Guard. If accepted, the installer downloads the Guard
   asset from the same release, verifies its independent GitHub digest, runs its
   supported install action, and confirms the protected root.
7. Installation creates `Uninstall GGO - No Hidden Heroes.lnk` in the game root. It asks for
   confirmation, stops Control Panel, temporarily unlocks Guard when necessary,
   and moves the installed GGO files into a timestamped `deleted_ggo_no_hidden_heroes` tree while
   preserving their original relative paths. Pre-existing files are restored
   from the first-install backup.

## Architecture

- `ggo_installer.py`: UI, shared installer core, and non-interactive test entry.
- `GGONoHiddenInstaller.spec`: deterministic one-file, windowed PyInstaller build.
- `GGO_No_Hidden_Heroes_Installer.exe`: generated distributable artifact.
- `testing_tools/test_installer.py`: fixture tests for archive boundary checks,
  digest rejection, rollback, release selection, strict executable location,
  non-interactive install, and reversible uninstall.

The runtime uses Python standard-library HTTP, ZIP, hashing, filesystem, Tk, and
Windows APIs. The core installer reports progress through a callback; the GUI
and non-interactive mode share that exact implementation. PowerShell is used
only for the normal Windows `WScript.Shell` shortcut operation, matching Guard.

## Rollback

File apply failures restore overwritten files and remove files created by this
run. Configuration failures also restore the previous Startup shortcut and
desktop URL when they were changed. Successful installs retain their backup in
`%LOCALAPPDATA%\GGONoHiddenInstaller\backups` for manual recovery.

## Verification

- Known-good fixture installs into a fake validated game root.
- A traversal ZIP is rejected without writing outside staging.
- A digest mismatch is rejected before game mutation (negative control).
- The packaged EXE resolves the real public release and verifies both published
  asset digests.
- The final packaged EXE resolves the real GitHub 1.0.10 metadata, verifies the
  main asset as SHA-256
  `84AD60D6CD82CED9F27AE1122FAF8A4C61DC5B855D759D33FA4E943B94A516DB`,
  installs 96 files into an isolated game fixture, then uninstalls 98 files
  including generated runtime state with zero active mod residue.
- A packaged negative control launched outside a valid game root exits with
  code 2 before creating a result file or initializing the installer log.

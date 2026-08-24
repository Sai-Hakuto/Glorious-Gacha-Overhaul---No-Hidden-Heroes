# GGO - No Hidden Heroes Installer

`GGO_No_Hidden_Heroes_Installer.exe` is the single-file public installer for
the No Hidden Heroes edition of GGO. Place it in
the game folder next to `DSClient.exe`; it refuses to operate from any other
location. It discovers
the latest published GitHub release, downloads and verifies the main archive,
backs up replaced files, installs GGO, activates Control Panel, and offers to
enable the separately verified Update Guard from the same release.

A successful install creates `Uninstall GGO - No Hidden Heroes.lnk` in the game root. The shortcut
asks for confirmation and moves GGO files into
`deleted_ggo_no_hidden_heroes\YYYYMMDD-HHMMSS\` with their original hierarchy. Files that existed
before GGO are restored from the installer backup; vanilla files and `DS\Saved`
are outside the removal scope.

Build:

```powershell
py -m PyInstaller --noconfirm --clean GGONoHiddenInstaller.spec
```

The build deliberately disables UPX and embeds publisher/product metadata to
reduce heuristic antivirus false positives. It is still unsigned; public
distribution should include the published SHA-256 and, when available, an
Authenticode signature from a trusted code-signing certificate.

Acceptance mode uses the same core without changing Startup or desktop state.
The packaged EXE must still physically reside in the same game root supplied by
`--game-dir`:

```powershell
GGO_No_Hidden_Heroes_Installer.exe --non-interactive --game-dir "M:\Games\DragonSword  Awakening" --skip-system-integration --result-json result.json
```

Non-interactive uninstall for test automation:

```powershell
GGO_No_Hidden_Heroes_Installer.exe --non-interactive --uninstall --game-dir "M:\Games\DragonSword  Awakening" --result-json uninstall-result.json
```

# Glorious Gacha Overhaul — No Hidden Heroes

This is a separate Dragon Sword: Awakening GGO edition for players who want the
restored systems without access to the seven unreleased hidden heroes.

Target game version: **1.0.10**.

## Disabled acquisition

The build removes pickup banners and Fate Invitation shop goods from the client
tables (including the duplicated `BMGoodsData.WrapData` shop index) and the
local server XML for:

- Ryza CE
- Veronica
- Logan
- Jerome
- Awakened Lute
- Ysera
- Viola

Character, combat, progression, localization, soul-item, Mail, Sword Pass,
Rift, Control Panel, and runtime data remain intact. A hidden hero already
present in a save remains usable; this edition only removes acquisition routes.

## Installation

1. Download `GGO_No_Hidden_Heroes_Installer.exe` from the latest release.
2. Put it in the Dragon Sword: Awakening game folder next to `DSClient.exe`.
3. Close the game and run the installer.

The installer downloads the matching ZIP from this repository, verifies its
GitHub SHA-256 before changing game files, creates a recovery backup, installs
Control Panel, and optionally installs DragonSword Update Guard.

It also creates `Uninstall GGO - No Hidden Heroes.lnk`. Uninstalling moves owned
files into `deleted_ggo_no_hidden_heroes` while preserving their hierarchy and
restores files that existed before installation.

## Verification

See [TEST_REPORT.md](TEST_REPORT.md), [PAK_BUILD_REPORT.json](PAK_BUILD_REPORT.json),
and [INSTALLER_BUILD_REPORT.json](INSTALLER_BUILD_REPORT.json).

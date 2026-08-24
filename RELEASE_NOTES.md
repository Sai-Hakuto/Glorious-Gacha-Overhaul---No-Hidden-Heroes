# GGO — No Hidden Heroes (target game version 1.0.10)

Separate GGO edition with all acquisition routes disabled for Ryza CE,
Veronica, Logan, Jerome, Awakened Lute, Ysera, and Viola.

## Changes from standard GGO

- Removed seven pickup-banner rows from all five client and server regional summon tables.
- Removed the corresponding seven client and server summon item groups.
- Removed seven Fate Invitation shop goods from client primary data, the
  duplicated client shop index, and server data, so no blank/crash-icon cards
  remain in the Hero tab.
- Kept character/combat/progression data so already-owned characters still work.
- Kept the corrected Mail, Sword Pass, Rift, Control Panel, purchase-screen, and
  world-audio fixes from the current standard GGO release.
- Raised all 24 internal Karma shop prices from 30 to 300 dismantling currency
  in client primary data, the client UI index, and server data.

## Installer

Put `GGO_No_Hidden_Heroes_Installer.exe` in the game root next to
`DSClient.exe`, close the game, and run it. The installer verifies the GitHub
SHA-256 before modifying files, creates a backup, installs Control Panel, offers
Update Guard, and creates a dedicated uninstall shortcut.

The standard GGO repository and release are not replaced by this edition.

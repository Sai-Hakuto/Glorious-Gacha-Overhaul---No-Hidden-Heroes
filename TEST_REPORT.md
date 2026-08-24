# GGO No Hidden Hero Acquisition — verification

Status: PASS

- Baseline: corrected GGO release PAK `E17041E126D5E307FED4C47145E0D0C7E998324D01FBE45E6A39E80B0DA4D392`
- Variant PAK: `1F56E1382137046E2EE6C38F72ABD4698217923664BE046BE081789D35BA6472`
- PAK entries: 3,774
- Changed PAK entries: exactly 14 expected client/server data files
- Removed pickup banners: 7 targets across all 5 client and server locale tables
- Removed SummonItem groups: 7 from both client and server data
- Removed Fate Invitation shop goods: 7 (`1000032` through `1000038`) from
  client `Data`, client `WrapData[1000]`, and server data
- Remaining normal banners: 20
- Forbidden client/server banner routes after build: 0
- Forbidden client/server shop routes after build: 0
- All other PAK entries: byte-identical to baseline
- ZIP files: 97
- ZIP SHA-256: `D277C59218F0E1E1EE9A97C5B9C9F3C1A5C2ABF22678583B54D39369A0E19A59`
- ZIP round-trip hash comparison: PASS (97/97 files)
- Embedded PAK verification after ZIP extraction: PASS
- Negative controls: PASS; the verifier rejects v2 because all seven duplicated
  `WrapData` shop rows responsible for placeholder/crash-icon cards remained
- In-place upgrade from the broken client-only variant: PASS; a subsequent
  uninstall restores the original clean state with zero active mod residue

The packaged installer passed local install/uninstall acceptance with zero
active-mod residue. The corrected build was then installed on drive F for the
user's runtime check.

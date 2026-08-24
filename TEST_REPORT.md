# GGO No Hidden Hero Acquisition — verification

Status: PASS

- Baseline: corrected GGO release PAK `E17041E126D5E307FED4C47145E0D0C7E998324D01FBE45E6A39E80B0DA4D392`
- Variant PAK: `388D7BEBC1DB31EDFDA1B9455827DCE09E7FD9F51BBC9A6881D57510BA227377`
- PAK entries: 3,774
- Changed PAK entries: exactly 14 expected client/server data files
- Removed pickup banners: 7 targets across all 5 client and server locale tables
- Removed SummonItem groups: 7 from both client and server data
- Removed Fate Invitation shop goods: 7 (`1000032` through `1000038`) from both client and server data
- Remaining normal banners: 20
- Forbidden client/server banner routes after build: 0
- Forbidden client/server shop routes after build: 0
- All other PAK entries: byte-identical to baseline
- ZIP files: 97
- ZIP round-trip hash comparison: PASS
- Embedded PAK verification after ZIP extraction: PASS
- Negative controls: PASS; the verifier rejects both standard GGO and the old
  broken client-only variant that produced placeholder shop cards
- In-place upgrade from the broken client-only variant: PASS; a subsequent
  uninstall restores the original clean state with zero active mod residue

The installed game on drive F was not modified during this build.

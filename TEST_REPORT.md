# GGO No Hidden Hero Acquisition — verification

Status: PASS

- Baseline: corrected GGO release PAK `E17041E126D5E307FED4C47145E0D0C7E998324D01FBE45E6A39E80B0DA4D392`
- Variant PAK: `4BE41E95BAF28BB6604835B349068E8FD7769947ED0C90D952FAEB5AE3E49D6A`
- PAK entries: 3,774
- Changed PAK entries: exactly 7 expected tables
- Removed pickup banners: 7 targets across all 5 locale tables
- Removed SummonItem groups: 7
- Removed Fate Invitation shop goods: 7 (`1000032` through `1000038`)
- Remaining normal banners: 20
- Forbidden banner routes after build: 0
- Forbidden shop routes after build: 0
- All other PAK entries: byte-identical to baseline
- ZIP files: 97
- ZIP round-trip hash comparison: PASS
- Embedded PAK verification after ZIP extraction: PASS
- Negative control: PASS; the verifier rejects unmodified standard GGO

The installed game on drive F was not modified during this build.

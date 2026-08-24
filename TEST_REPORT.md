# GGO No Hidden Hero Acquisition — verification

Status: PASS

- Baseline: corrected GGO release PAK `92BDF6ADA4B231639A59290A1DF324681D4F79C93316D81EDC9A69C292B576E0`
- Variant PAK: `B9CFB7AC0DBC1D61DA2B4A88CB0C30B9D9A6A9949A74EF01BE56F818D68E4CF2`
- PAK entries: 3,774
- Changed PAK entries: exactly 14 expected client/server data files
- Removed pickup banners: 7 targets across all 5 client and server locale tables
- Removed SummonItem groups: 7 from both client and server data
- Removed Fate Invitation shop goods: 7 (`1000032` through `1000038`) from
  client `Data`, client `WrapData[1000]`, and server data
- Remaining normal banners: 20
- Forbidden client/server banner routes after build: 0
- Forbidden client/server shop routes after build: 0
- Karma shop prices: 24/24 equal 300 in client `Data`, client `WrapData`, and server XML
- All other PAK entries: byte-identical to baseline
- ZIP files: 97
- ZIP SHA-256: `D7116723448C6E975A6AD57AC14569D431D98A9914828B26446109EB07ABBA47`
- ZIP round-trip hash comparison: PASS (97/97 files)
- Embedded PAK verification after ZIP extraction: PASS
- Negative controls: PASS; the verifier rejects v2 because all seven duplicated
  `WrapData` shop rows responsible for placeholder/crash-icon cards remained
- In-place upgrade from the broken client-only variant: PASS; a subsequent
  uninstall restores the original clean state with zero active mod residue

The packaged installer passed local install/uninstall acceptance with zero
active-mod residue. The corrected build was then installed on drive F for the
user's runtime check.

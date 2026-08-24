#!/usr/bin/env python3
"""Verify the GGO no-hidden-hero acquisition PAK against its baseline."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

from build_variant import (
    EDITED_TABLES,
    SUMMON_GROUP_TABLES,
    TABLE_PREFIX,
    TARGETS,
    acquisition_map,
    decode_table,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pakmerge-root", required=True)
    parser.add_argument("--baseline-pak", required=True)
    parser.add_argument("--variant-pak", required=True)
    args = parser.parse_args()

    pakmerge_root = pathlib.Path(args.pakmerge_root).resolve()
    sys.path.insert(0, str(pakmerge_root))
    import pak_io  # type: ignore

    baseline = pak_io.read_pak(pathlib.Path(args.baseline_pak).resolve())
    variant = pak_io.read_pak(pathlib.Path(args.variant_pak).resolve())
    base_entries = baseline["entries"]
    entries = variant["entries"]
    if baseline["mount"] != variant["mount"]:
        raise RuntimeError("mount mismatch")
    if set(base_entries) != set(entries):
        raise RuntimeError("entry-set mismatch")
    changed = {path for path in entries if entries[path] != base_entries[path]}
    if changed != EDITED_TABLES:
        raise RuntimeError(
            f"change boundary mismatch: changed={sorted(changed)}, expected={sorted(EDITED_TABLES)}"
        )

    banners = {str(spec["banner"]) for spec in TARGETS.values()}
    for table_name in SUMMON_GROUP_TABLES:
        leaked = banners & set(decode_table(entries, table_name)["Data"])
        if leaked:
            raise RuntimeError(f"{table_name}: forbidden banners present: {sorted(leaked)}")
    leaked_groups = banners & set(decode_table(entries, "SummonItemData.table")["Data"])
    if leaked_groups:
        raise RuntimeError(f"SummonItemData: forbidden groups present: {sorted(leaked_groups)}")

    routes = acquisition_map(entries)
    leaked_routes = {
        item_id: route["goods_ids"] for item_id, route in routes.items() if route["goods_ids"]
    }
    if leaked_routes:
        raise RuntimeError(f"forbidden shop routes present: {leaked_routes}")

    # Non-target banners prove that the surrounding summon catalogue survived.
    normal_banner_count = len(decode_table(entries, "SummonGroupData.table")["Data"])
    if normal_banner_count < 10:
        raise RuntimeError(f"implausible remaining banner count: {normal_banner_count}")

    print(
        "ggo_no_hidden_verify=PASS"
        f"|entries={len(entries)}"
        f"|changed={len(changed)}"
        f"|remaining_banners={normal_banner_count}"
        "|forbidden_banners=0|forbidden_shop_routes=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

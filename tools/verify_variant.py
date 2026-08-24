#!/usr/bin/env python3
"""Verify the GGO no-hidden-hero acquisition PAK against its baseline."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

from build_variant import (
    EDITED_ENTRIES,
    SUMMON_GROUP_TABLES,
    SUMMON_GROUP_XML,
    TABLE_PREFIX,
    TARGETS,
    acquisition_map,
    decode_table,
    server_row_ids,
    wrapped_goods_rows,
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
    if changed != EDITED_ENTRIES:
        raise RuntimeError(
            f"change boundary mismatch: changed={sorted(changed)}, expected={sorted(EDITED_ENTRIES)}"
        )

    banners = {str(spec["banner"]) for spec in TARGETS.values()}
    for table_name in SUMMON_GROUP_TABLES:
        leaked = banners & set(decode_table(entries, table_name)["Data"])
        if leaked:
            raise RuntimeError(f"{table_name}: forbidden banners present: {sorted(leaked)}")
    leaked_groups = banners & set(decode_table(entries, "SummonItemData.table")["Data"])
    if leaked_groups:
        raise RuntimeError(f"SummonItemData: forbidden groups present: {sorted(leaked_groups)}")

    for xml_name in SUMMON_GROUP_XML:
        leaked = banners & set(server_row_ids(
            entries, xml_name, "SummonGroupData", "ID",
        ))
        if leaked:
            raise RuntimeError(f"{xml_name}: forbidden server banners present: {sorted(leaked)}")
    leaked_server_groups = banners & set(server_row_ids(
        entries, "SummonItemData.xml", "SummonItemData", "ItemGroupID",
    ))
    if leaked_server_groups:
        raise RuntimeError(
            f"SummonItemData.xml: forbidden server groups present: {sorted(leaked_server_groups)}"
        )

    target_goods = {str(goods_id) for goods_id in range(1000032, 1000039)}
    client_goods = decode_table(entries, "BMGoodsData_KOR.table")
    leaked_client_goods = target_goods & set(client_goods["Data"])
    leaked_wrapped_goods = target_goods & {
        str(row.get("ID")) for row in wrapped_goods_rows(client_goods)
    }
    if leaked_client_goods or leaked_wrapped_goods:
        raise RuntimeError(
            "BMGoodsData_KOR.table: forbidden shop goods remain: "
            f"primary={sorted(leaked_client_goods)} wrapped={sorted(leaked_wrapped_goods)}"
        )
    leaked_server_goods = target_goods & set(server_row_ids(
        entries, "BMGoodsData_KOR.xml", "BMGoodsData", "ID",
    ))
    if leaked_server_goods:
        raise RuntimeError(
            f"BMGoodsData_KOR.xml: forbidden server goods present: {sorted(leaked_server_goods)}"
        )

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
        "|forbidden_client_server_banners=0|forbidden_client_server_shop_routes=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

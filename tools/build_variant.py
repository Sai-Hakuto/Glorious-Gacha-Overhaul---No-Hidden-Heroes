#!/usr/bin/env python3
"""Build and verify a GGO variant with seven hidden heroes unobtainable."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from typing import Any
import xml.etree.ElementTree as ET

TARGETS = {
    "Ryza CE": {"cid": 10017, "banner": "4010", "item": 1111501},
    "Ysera": {"cid": 10010, "banner": "4012", "item": 1110901},
    "Awakened Lute": {"cid": 10026, "banner": "4013", "item": 1110103},
    "Viola": {"cid": 10035, "banner": "4014", "item": 1113301},
    "Jerome": {"cid": 10015, "banner": "4015", "item": 1111301},
    "Logan": {"cid": 10033, "banner": "4016", "item": 1113101},
    "Veronica": {"cid": 10019, "banner": "4017", "item": 1111702},
}
TABLE_PREFIX = "Design/GameData/"
SERVER_PREFIX = "__GeneratedGameData__/Server/XML/GameData/"
SUMMON_GROUP_TABLES = [
    "SummonGroupData.table",
    "SummonGroupData_AMERICA.table",
    "SummonGroupData_ASIA.table",
    "SummonGroupData_EUROPE.table",
    "SummonGroupData_KOR.table",
]
SUMMON_GROUP_XML = [name.removesuffix(".table") + ".xml" for name in SUMMON_GROUP_TABLES]
EDITED_ENTRIES = {
    *(TABLE_PREFIX + name for name in SUMMON_GROUP_TABLES),
    TABLE_PREFIX + "SummonItemData.table",
    TABLE_PREFIX + "BMGoodsData_KOR.table",
    *(SERVER_PREFIX + name for name in SUMMON_GROUP_XML),
    SERVER_PREFIX + "SummonItemData.xml",
    SERVER_PREFIX + "BMGoodsData_KOR.xml",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def decode_table(entries: dict[str, bytes], name: str) -> dict[str, Any]:
    path = TABLE_PREFIX + name
    try:
        raw = entries[path]
    except KeyError as exc:
        raise RuntimeError(f"missing table entry: {path}") from exc
    parsed = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(parsed, dict) or not isinstance(parsed.get("Data"), dict):
        raise RuntimeError(f"unexpected table shape: {path}")
    return parsed


def encode_table(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def local_name(value: str) -> str:
    return value.rsplit("}", 1)[-1]


def server_row_ids(
    entries: dict[str, bytes], name: str, element_name: str, attribute_name: str,
) -> list[str]:
    path = SERVER_PREFIX + name
    try:
        root = ET.fromstring(entries[path])
    except KeyError as exc:
        raise RuntimeError(f"missing server XML entry: {path}") from exc
    except ET.ParseError as exc:
        raise RuntimeError(f"invalid server XML: {path}: {exc}") from exc
    result: list[str] = []
    for child in root:
        if local_name(child.tag) != element_name:
            continue
        attributes = {local_name(key): value for key, value in child.attrib.items()}
        if attribute_name in attributes:
            result.append(attributes[attribute_name])
    return result


def remove_server_rows(
    entries: dict[str, bytes], name: str, element_name: str,
    attribute_name: str, targets: set[str],
) -> list[str]:
    path = SERVER_PREFIX + name
    before_ids = server_row_ids(entries, name, element_name, attribute_name)
    counts = {target: before_ids.count(target) for target in targets}
    bad_counts = {target: count for target, count in counts.items() if count != 1}
    if bad_counts:
        raise RuntimeError(f"{name}: expected exactly one server row per target: {bad_counts}")

    tag_marker = f":{element_name} ".encode("ascii")
    attribute_markers = {
        target: f':{attribute_name}="{target}"'.encode("ascii") for target in targets
    }
    removed: list[str] = []
    kept: list[bytes] = []
    for line in entries[path].splitlines(keepends=True):
        matched = [
            target for target, marker in attribute_markers.items()
            if tag_marker in line and marker in line
        ]
        if matched:
            if len(matched) != 1:
                raise RuntimeError(f"{name}: ambiguous target server row")
            removed.append(matched[0])
        else:
            kept.append(line)
    if sorted(removed, key=int) != sorted(targets, key=int):
        raise RuntimeError(f"{name}: removed unexpected server rows: {removed}")
    entries[path] = b"".join(kept)
    ET.fromstring(entries[path])
    remaining = set(server_row_ids(entries, name, element_name, attribute_name))
    leaked = sorted(targets & remaining, key=int)
    if leaked:
        raise RuntimeError(f"{name}: target server rows remain: {leaked}")
    return sorted(removed, key=int)


def flatten_random_ids(reward_row: dict[str, Any]) -> set[int]:
    result: set[int] = set()
    for reward in reward_row.get("RewardDatas", []):
        for value in reward.get("RandomID", []):
            if int(value):
                result.add(int(value))
    return result


def acquisition_map(entries: dict[str, bytes]) -> dict[int, dict[str, list[int]]]:
    random_rows = decode_table(entries, "RewardRandomData.table")["Data"]
    reward_rows = decode_table(entries, "RewardData.table")["Data"]
    goods_rows = decode_table(entries, "BMGoodsData_KOR.table")["Data"]
    result: dict[int, dict[str, list[int]]] = {}
    for spec in TARGETS.values():
        item_id = int(spec["item"])
        random_ids = sorted(
            int(key)
            for key, row in random_rows.items()
            if any(int(item.get("ItemID", 0)) == item_id for item in row.get("RewardRandomDataArray", []))
        )
        random_id_set = set(random_ids)
        reward_ids = sorted(
            int(key)
            for key, row in reward_rows.items()
            if flatten_random_ids(row) & random_id_set
        )
        reward_id_set = set(reward_ids)
        goods_ids = sorted(
            int(key)
            for key, row in goods_rows.items()
            if int(row.get("GoodsRewardId", 0)) in reward_id_set
        )
        result[item_id] = {
            "random_ids": random_ids,
            "reward_ids": reward_ids,
            "goods_ids": goods_ids,
        }
    return result


def wrapped_goods_rows(table: dict[str, Any], subcategory_id: str = "1000") -> list[dict[str, Any]]:
    """Return the client shop's duplicated category index for a subcategory."""
    try:
        rows = table["WrapData"][subcategory_id]["Data"]
    except (KeyError, TypeError) as exc:
        raise RuntimeError(
            f"BMGoodsData_KOR.table: missing WrapData[{subcategory_id}].Data"
        ) from exc
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise RuntimeError(
            f"BMGoodsData_KOR.table: invalid WrapData[{subcategory_id}].Data"
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pakmerge-root", required=True)
    parser.add_argument("--source-pak", required=True)
    parser.add_argument("--output-pak", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    pakmerge_root = pathlib.Path(args.pakmerge_root).resolve()
    source_pak = pathlib.Path(args.source_pak).resolve()
    output_pak = pathlib.Path(args.output_pak).resolve()
    report_path = pathlib.Path(args.report).resolve()
    if not source_pak.is_file():
        raise SystemExit(f"source PAK missing: {source_pak}")
    if output_pak.exists():
        raise SystemExit(f"refusing existing output PAK: {output_pak}")
    if report_path.exists():
        raise SystemExit(f"refusing existing report: {report_path}")

    sys.path.insert(0, str(pakmerge_root))
    # Forge keeps the DragonSword PAK writer at the modding-root level.
    sys.path.insert(0, str(pakmerge_root.parents[2]))
    import pak_io  # type: ignore
    import ds_pakwrite  # type: ignore

    archive = pak_io.read_pak(source_pak)
    original: dict[str, bytes] = archive["entries"]
    entries = dict(original)
    banner_ids = {str(spec["banner"]) for spec in TARGETS.values()}
    item_by_banner = {str(spec["banner"]): int(spec["item"]) for spec in TARGETS.values()}

    before_routes = acquisition_map(entries)
    removed_banners: dict[str, list[str]] = {}
    for table_name in SUMMON_GROUP_TABLES:
        table = decode_table(entries, table_name)
        data = table["Data"]
        missing = sorted(banner_ids - set(data))
        if missing:
            raise RuntimeError(f"{table_name}: expected target banners missing: {missing}")
        removed_banners[table_name] = sorted(banner_ids, key=int)
        for banner_id in banner_ids:
            del data[banner_id]
        entries[TABLE_PREFIX + table_name] = encode_table(table)

    summon_items = decode_table(entries, "SummonItemData.table")
    summon_data = summon_items["Data"]
    for banner_id, expected_item in item_by_banner.items():
        row = summon_data.get(banner_id)
        if row is None:
            raise RuntimeError(f"SummonItemData: expected group missing: {banner_id}")
        actual_items = {int(key) for key in row.get("SummonItemInfoData", {})}
        if actual_items != {expected_item}:
            raise RuntimeError(
                f"SummonItemData[{banner_id}] expected only {expected_item}, got {sorted(actual_items)}"
            )
        del summon_data[banner_id]
    entries[TABLE_PREFIX + "SummonItemData.table"] = encode_table(summon_items)

    target_goods = sorted(
        {goods_id for route in before_routes.values() for goods_id in route["goods_ids"]}
    )
    goods_ids = {str(goods_id) for goods_id in target_goods}
    goods = decode_table(entries, "BMGoodsData_KOR.table")
    goods_data = goods["Data"]
    wrapped_goods = wrapped_goods_rows(goods)
    missing_goods = [str(goods_id) for goods_id in target_goods if str(goods_id) not in goods_data]
    if missing_goods:
        raise RuntimeError(f"expected target goods missing: {missing_goods}")
    wrapped_by_id: dict[str, list[dict[str, Any]]] = {}
    for row in wrapped_goods:
        wrapped_by_id.setdefault(str(row.get("ID")), []).append(row)
    bad_wrapped = {
        str(goods_id): len(wrapped_by_id.get(str(goods_id), []))
        for goods_id in target_goods
        if len(wrapped_by_id.get(str(goods_id), [])) != 1
    }
    if bad_wrapped:
        raise RuntimeError(
            f"BMGoodsData_KOR.table: expected one wrapped row per target: {bad_wrapped}"
        )
    mismatched_wrapped = [
        str(goods_id)
        for goods_id in target_goods
        if wrapped_by_id[str(goods_id)][0] != goods_data[str(goods_id)]
    ]
    if mismatched_wrapped:
        raise RuntimeError(
            "BMGoodsData_KOR.table: wrapped target rows differ from primary rows: "
            f"{mismatched_wrapped}"
        )
    for goods_id in target_goods:
        del goods_data[str(goods_id)]
    goods["WrapData"]["1000"]["Data"] = [
        row for row in wrapped_goods if str(row.get("ID")) not in goods_ids
    ]
    entries[TABLE_PREFIX + "BMGoodsData_KOR.table"] = encode_table(goods)

    removed_server_rows: dict[str, list[str]] = {}
    for xml_name in SUMMON_GROUP_XML:
        removed_server_rows[xml_name] = remove_server_rows(
            entries, xml_name, "SummonGroupData", "ID", banner_ids,
        )
    removed_server_rows["SummonItemData.xml"] = remove_server_rows(
        entries, "SummonItemData.xml", "SummonItemData", "ItemGroupID", banner_ids,
    )
    removed_server_rows["BMGoodsData_KOR.xml"] = remove_server_rows(
        entries, "BMGoodsData_KOR.xml", "BMGoodsData", "ID", goods_ids,
    )

    output_pak.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    write_info = ds_pakwrite.write_pak(
        str(output_pak), archive["mount"], sorted(entries.items())
    )

    rebuilt = pak_io.read_pak(output_pak)
    rebuilt_entries: dict[str, bytes] = rebuilt["entries"]
    if rebuilt["mount"] != archive["mount"]:
        raise RuntimeError("mount changed after rebuild")
    if set(rebuilt_entries) != set(original):
        raise RuntimeError("PAK entry set changed after rebuild")

    changed = sorted(
        path for path in original if original[path] != rebuilt_entries[path]
    )
    unexpected_changed = sorted(set(changed) - EDITED_ENTRIES)
    unchanged_expected = sorted(EDITED_ENTRIES - set(changed))
    if unexpected_changed or unchanged_expected:
        raise RuntimeError(
            f"change boundary failed: unexpected={unexpected_changed}, unchanged_expected={unchanged_expected}"
        )

    for table_name in SUMMON_GROUP_TABLES:
        remaining = decode_table(rebuilt_entries, table_name)["Data"]
        leaked = sorted(banner_ids & set(remaining))
        if leaked:
            raise RuntimeError(f"{table_name}: target banners remain: {leaked}")
    remaining_summon = decode_table(rebuilt_entries, "SummonItemData.table")["Data"]
    leaked_groups = sorted(banner_ids & set(remaining_summon))
    if leaked_groups:
        raise RuntimeError(f"SummonItemData: target groups remain: {leaked_groups}")
    for xml_name in SUMMON_GROUP_XML:
        remaining = set(server_row_ids(
            rebuilt_entries, xml_name, "SummonGroupData", "ID",
        ))
        leaked = sorted(banner_ids & remaining, key=int)
        if leaked:
            raise RuntimeError(f"{xml_name}: target server banners remain: {leaked}")
    remaining_server_groups = set(server_row_ids(
        rebuilt_entries, "SummonItemData.xml", "SummonItemData", "ItemGroupID",
    ))
    leaked_server_groups = sorted(banner_ids & remaining_server_groups, key=int)
    if leaked_server_groups:
        raise RuntimeError(
            f"SummonItemData.xml: target server groups remain: {leaked_server_groups}"
        )
    remaining_server_goods = set(server_row_ids(
        rebuilt_entries, "BMGoodsData_KOR.xml", "BMGoodsData", "ID",
    ))
    leaked_server_goods = sorted(goods_ids & remaining_server_goods, key=int)
    if leaked_server_goods:
        raise RuntimeError(
            f"BMGoodsData_KOR.xml: target server goods remain: {leaked_server_goods}"
        )
    rebuilt_goods = decode_table(rebuilt_entries, "BMGoodsData_KOR.table")
    remaining_wrapped_goods = {
        str(row.get("ID")) for row in wrapped_goods_rows(rebuilt_goods)
    }
    leaked_wrapped_goods = sorted(goods_ids & remaining_wrapped_goods, key=int)
    if leaked_wrapped_goods:
        raise RuntimeError(
            "BMGoodsData_KOR.table: target wrapped shop rows remain: "
            f"{leaked_wrapped_goods}"
        )

    after_routes = acquisition_map(rebuilt_entries)
    leaked_goods = {
        str(item_id): route["goods_ids"]
        for item_id, route in after_routes.items()
        if route["goods_ids"]
    }
    if leaked_goods:
        raise RuntimeError(f"target shop acquisition routes remain: {leaked_goods}")

    target_report = {}
    for name, spec in TARGETS.items():
        item_id = int(spec["item"])
        target_report[name] = {
            **spec,
            "shop_route_before": before_routes[item_id],
            "shop_route_after": after_routes[item_id],
        }
    report = {
        "status": "PASS",
        "source_pak": str(source_pak),
        "source_sha256": sha256(source_pak.read_bytes()),
        "output_pak": str(output_pak),
        "output_sha256": sha256(output_pak.read_bytes()),
        "mount": archive["mount"],
        "entry_count": len(rebuilt_entries),
        "changed_entry_count": len(changed),
        "changed_entries": changed,
        "removed_goods_ids": target_goods,
        "removed_wrapped_goods_ids": target_goods,
        "removed_server_rows": removed_server_rows,
        "targets": target_report,
        "write_info": write_info,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        "ggo_no_hidden_build=PASS"
        f"|entries={len(rebuilt_entries)}"
        f"|changed={len(changed)}"
        f"|goods_removed={len(target_goods)}"
        f"|sha256={report['output_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

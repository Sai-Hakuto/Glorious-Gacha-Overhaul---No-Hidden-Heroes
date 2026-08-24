#!/usr/bin/env python3
"""Inspect GGO PAK catalogues for hidden-hero shop routes."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


TARGET_ITEMS = {1111501, 1110901, 1110103, 1113301, 1111301, 1113101, 1111702}
TARGET_CIDS = {10017, 10010, 10026, 10035, 10015, 10033, 10019}
TARGET_BANNERS = {4010, 4012, 4013, 4014, 4015, 4016, 4017}
TARGET_GOODS = set(range(1000032, 1000039))


def walk(value: object, path: str = ""):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk(child, f"{path}/{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, f"{path}/{index}")
    else:
        yield path, value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pakmerge-root", required=True)
    parser.add_argument("--pak", required=True)
    args = parser.parse_args()

    pakmerge_root = Path(args.pakmerge_root).resolve()
    sys.path.insert(0, str(pakmerge_root))
    sys.path.insert(0, str(pakmerge_root.parents[2]))
    import pak_io  # type: ignore

    archive = pak_io.read_pak(Path(args.pak).resolve())
    entries: dict[str, bytes] = archive["entries"]
    print(f"entries={len(entries)} mount={archive['mount']}")
    goods = json.loads(entries["Design/GameData/BMGoodsData_KOR.table"].decode("utf-8-sig"))["Data"]
    subcategories = json.loads(
        entries["Design/GameData/BMShopSubCategoryData.table"].decode("utf-8-sig")
    )["Data"]
    print("SHOP_SUBCATEGORY_1000 " + json.dumps(subcategories.get("1000"), ensure_ascii=False))
    for table_name in (
        "SummonGroupData.table", "SummonItemData.table", "BMGoodsData_KOR.table",
    ):
        value = json.loads(entries[f"Design/GameData/{table_name}"].decode("utf-8-sig"))
        wrapped_hits = []
        for path, scalar in walk(value.get("WrapData")):
            try:
                number = int(scalar)
            except (TypeError, ValueError):
                continue
            if number in TARGET_BANNERS | TARGET_GOODS | TARGET_ITEMS:
                wrapped_hits.append((path, number))
        print(
            f"WRAP {table_name} type={type(value.get('WrapData')).__name__} "
            f"hits={json.dumps(wrapped_hits, separators=(',', ':'))}"
        )
    print("CHARACTER_GOODS")
    for goods_id, row in goods.items():
        if int(row.get("GoodsSubCategoryId", 0)) == 1000:
            fields = {
                key: row.get(key)
                for key in (
                    "ID", "GoodsRewardId", "SortOrder", "GoodsStringId", "GoodsIconPath",
                    "PurchaseConditionCheckId", "PaymentItemId", "PaymentValue",
                    "GoodsDisplayType", "GoodsDisplayStartDate", "GoodsDisplayEndDate",
                )
            }
            print(f"  {goods_id} {json.dumps(fields, ensure_ascii=False, separators=(',', ':'))}")
    for name, raw in sorted(entries.items()):
        lower = name.lower()
        interesting_name = any(token in lower for token in ("shop", "goods", "store", "purchase", "reward"))
        interesting_content = any(str(value).encode() in raw for value in TARGET_ITEMS | TARGET_CIDS)
        if interesting_name or interesting_content:
            print(f"ENTRY {name} size={len(raw)} target_content={interesting_content}")
        if not lower.endswith(".table"):
            continue
        try:
            parsed = json.loads(raw.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        hits = []
        for path, value in walk(parsed):
            try:
                number = int(value)
            except (TypeError, ValueError):
                continue
            if number in TARGET_ITEMS or number in TARGET_CIDS:
                hits.append((path, number))
        if hits:
            print(f"TARGETS {name} count={len(hits)}")
            for path, value in hits[:100]:
                print(f"  {path}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

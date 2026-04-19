#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""简易记账本：CSV 存储，支持添加、查询与总金额统计。"""

from __future__ import annotations

import csv
import sys
from datetime import date, datetime
from pathlib import Path

CSV_NAME = "wallet_records.csv"
FIELDNAMES = ("date", "category", "amount", "note", "recorded_at")


def recorded_time_to_minute() -> str:
    """当前时刻，精确到分钟（秒、微秒归零）。"""
    now = datetime.now().replace(second=0, microsecond=0)
    return now.strftime("%Y-%m-%d %H:%M")


def data_path() -> Path:
    return Path(__file__).resolve().parent / CSV_NAME


def load_rows() -> list[dict[str, str]]:
    path = data_path()
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return []
        missing = [h for h in FIELDNAMES if h not in reader.fieldnames]
        if missing and set(missing) != {"recorded_at"}:
            print(f"警告：CSV 表头缺少列 {missing}，将按空值读取。", file=sys.stderr)
        return list(reader)


def save_rows(rows: list[dict[str, str]]) -> None:
    path = data_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in FIELDNAMES})


def add_entry(date_str: str, category: str, amount_str: str, note: str) -> None:
    category = category.strip()
    if not category:
        raise ValueError("类别不能为空。")
    try:
        amount = float(amount_str.strip())
    except ValueError as e:
        raise ValueError("金额必须是数字。") from e
    if amount <= 0:
        raise ValueError("金额必须大于 0。")

    rows = load_rows()
    rows.append(
        {
            "date": date_str.strip(),
            "category": category,
            "amount": f"{amount:.2f}",
            "note": note.strip(),
            "recorded_at": recorded_time_to_minute(),
        }
    )
    save_rows(rows)
    print("已保存到 CSV。")


def list_entries() -> None:
    rows = load_rows()
    if not rows:
        print("暂无账目。")
        return
    print(f"{'日期':<12} {'类别':<10} {'金额':>10}  {'记账时间':<16} 备注")
    print("-" * 60)
    for r in rows:
        print(
            f"{r.get('date', ''):<12} {r.get('category', ''):<10} "
            f"{float(r.get('amount', 0) or 0):>10.2f}  "
            f"{r.get('recorded_at', ''):<16}{r.get('note', '')}"
        )


def total_spent() -> float:
    """统计并返回当前总支出（金额之和）。"""
    total = 0.0
    for r in load_rows():
        try:
            total += float(r.get("amount", 0) or 0)
        except ValueError:
            continue
    return total


def show_total() -> None:
    t = total_spent()
    print(f"目前总共支出：{t:.2f} 元")


def main() -> None:
    while True:
        print()
        print("—— 我的记账本 ——")
        print("1. 添加账目（日期、类别、金额、备注；自动记录记账时间到分钟）")
        print("2. 查看明细")
        print("3. 统计总金额")
        print("0. 退出")
        choice = input("请选择 (0-3): ").strip()

        if choice == "0":
            print("再见。")
            break
        if choice == "1":
            today = date.today().isoformat()
            d = input(f"日期 (回车默认 {today}): ").strip() or today
            cat = input("类别: ").strip()
            amt = input("金额: ").strip()
            note = input("备注 (可空，例如：买奶茶): ").strip()
            try:
                add_entry(d, cat, amt, note)
            except ValueError as e:
                print(f"输入有误：{e}")
        elif choice == "2":
            list_entries()
        elif choice == "3":
            show_total()
        else:
            print("无效选项，请重试。")


if __name__ == "__main__":
    main()

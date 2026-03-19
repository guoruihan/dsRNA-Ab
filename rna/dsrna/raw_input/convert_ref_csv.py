#!/usr/bin/env python3
"""
把项目里的“假CSV”(tab分隔、无表头)转换成标准CSV(逗号分隔、有表头)。

输入 ref.csv 每行大致字段为：
  id, sequence, structure, energy, length, valid

其中 valid 通常为 "TRUE" / "FALSE"。
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


def parse_bool(v: str) -> str:
    v_norm = v.strip().upper()
    if v_norm in {"TRUE", "T", "1", "YES", "Y"}:
        return "TRUE"
    if v_norm in {"FALSE", "F", "0", "NO", "N"}:
        return "FALSE"
    # 兜底：保留原值（避免误判导致下游数据异常）
    return v.strip()


def convert(input_path: Path, output_path: Path) -> None:
    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 用 newline="" 让 csv.writer 在不同平台行为一致
    with input_path.open("r", encoding="utf-8") as f_in, output_path.open(
        "w", encoding="utf-8", newline=""
    ) as f_out:
        writer = csv.writer(f_out, delimiter=",", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["id", "sequence", "structure", "energy", "length", "valid"])

        for line_no, raw in enumerate(f_in, start=1):
            line = raw.strip()
            if not line:
                continue

            # 允许 sequence/structure 中出现意外 tab 的情况：sequence 使用中间部分拼回
            parts = line.split("\t")
            if len(parts) < 6:
                raise ValueError(
                    f"第 {line_no} 行字段数量不足（期望>=6，实际={len(parts)}）: {line}"
                )

            seq = "\t".join(parts[1:-4])
            row_id = parts[0]
            structure = parts[-4]
            energy_raw = parts[-3]
            length_raw = parts[-2]
            valid_raw = parts[-1]

            try:
                energy = float(energy_raw)
            except ValueError as e:
                raise ValueError(
                    f"第 {line_no} 行 energy 不是数字: {energy_raw}"
                ) from e

            try:
                length = int(float(length_raw))  # 防御：某些数据可能写成 29.0
            except ValueError as e:
                raise ValueError(
                    f"第 {line_no} 行 length 不是整数: {length_raw}"
                ) from e

            writer.writerow(
                [row_id, seq, structure, energy, length, parse_bool(valid_raw)]
            )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="把 raw_input/ref.csv (tab分隔无表头) 转成标准 CSV(逗号分隔+表头)"
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=Path(__file__).with_name("ref.csv"),
        help="输入假CSV路径（默认：同目录 ref.csv）",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path(__file__).with_name("ref_real.csv"),
        help="输出真实CSV路径（默认：同目录 ref_real.csv）",
    )

    args = parser.parse_args(argv)
    convert(args.input, args.output)
    print(f"转换完成: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


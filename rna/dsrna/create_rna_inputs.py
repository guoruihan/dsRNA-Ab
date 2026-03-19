#!/usr/bin/env python3
"""
根据 `raw_input/ref_real.csv` 生成 AF3 所需的输入：
  `rna/dsrna/input/rna_{id}/input.json`

输入参考：
  `rna/demo/input/input.json`
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


def is_true(v: str) -> bool:
    v_norm = v.strip().upper()
    return v_norm in {"TRUE", "T", "1", "YES", "Y"}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="根据 ref_real.csv 生成 rna_{id}/input.json"
    )
    parser.add_argument(
        "--ref",
        type=Path,
        default=Path(__file__).parent / "raw_input" / "ref_real.csv",
        help="参考 CSV（默认：rna/dsrna/raw_input/ref_real.csv）",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).parent / "input",
        help="输出目录（默认：rna/dsrna/input）",
    )
    parser.add_argument(
        "--model_seed",
        type=int,
        default=1,
        help="modelSeeds 中使用的随机种子（默认 1）",
    )
    parser.add_argument(
        "--flat",
        action="store_true",
        help="扁平输出：直接在 rna/dsrna/input 下生成 rna_{id}.json（不使用子目录）",
    )
    parser.add_argument(
        "--skip_invalid",
        action="store_true",
        help="如果 valid 列为 FALSE，则跳过该条记录",
    )

    args = parser.parse_args(argv)
    ref_path: Path = args.ref
    out_dir: Path = args.out

    if not ref_path.exists():
        raise FileNotFoundError(f"ref 文件不存在: {ref_path}")
    out_dir.mkdir(parents=True, exist_ok=True)

    created = 0
    skipped = 0

    with ref_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        required_cols = {"id", "sequence", "valid"}
        missing = required_cols - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV 缺少列: {sorted(missing)}; 现有列: {reader.fieldnames}")

        for row_idx, row in enumerate(reader, start=1):
            row_id = str(row["id"]).strip()
            seq = (row.get("sequence") or "").strip()
            valid = str(row.get("valid", "")).strip()

            if not row_id or not seq:
                # 没有 id 或 sequence 就没法生成
                skipped += 1
                continue

            if args.skip_invalid and (valid and not is_true(valid)):
                skipped += 1
                continue

            input_json = {
                "name": f"rna_{row_id}",
                "sequences": [
                    {
                        "rna": {
                            "id": row_id,
                            "sequence": seq,
                            # 和 demo 保持一致：初始输入为空，后续 pipeline 会生成/填充
                            "unpairedMsa": "",
                        }
                    }
                ],
                "modelSeeds": [args.model_seed],
                "dialect": "alphafold3",
                "version": 1,
            }

            if args.flat:
                out_file = out_dir / f"rna_{row_id}.json"
            else:
                target_dir = out_dir / f"rna_{row_id}"
                target_dir.mkdir(parents=True, exist_ok=True)
                out_file = target_dir / "input.json"

            out_file.write_text(
                json.dumps(input_json, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            created += 1

    print(f"生成完成: created={created}, skipped={skipped}, out={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


#!/usr/bin/env python3
"""
外层并行脚本：用 128 个 CPU 并行调用内层：
  motif/check_protein_rna_contacts_aa.py

目标：
  - 枚举 PDB_sync 下所有两字母分片目录（默认）
  - 每个分片一个子任务
  - 内层会把结果写到 ./output/<shard>.tsv（默认相对外层运行的 CWD）

Example:
  cd /Users/ruihan/Documents/Projects/dsRNA-Ab
  python3 motif/run_contacts_parallel.py --workers 128
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tqdm import tqdm


def discover_shards(root: Path) -> list[str]:
    shard_re = re.compile(r"^[a-z]{2}$")
    shards = []
    if not root.exists():
        return shards
    for p in root.iterdir():
        if p.is_dir() and shard_re.match(p.name):
            # Only process shards that actually contain cif.gz files
            if any(p.glob("*.cif.gz")):
                shards.append(p.name)
    return sorted(shards)


def run_one(
    inner_script: Path,
    root: Path,
    shard: str,
    distance: float,
    require_rna_chains: int,
    limit: int,
    outdir: Path,
) -> tuple[str, int]:
    log_path = outdir / f"{shard}.log"

    cmd = [
        sys.executable,
        str(inner_script),
        "--root",
        str(root),
        "--shard",
        shard,
        "--distance",
        str(distance),
        "--require-rna-chains",
        str(require_rna_chains),
        "--limit",
        str(limit),
        "--outdir",
        str(outdir),
    ]

    # Ensure output directory exists before launching.
    outdir.mkdir(parents=True, exist_ok=True)

    with log_path.open("w", encoding="utf-8") as f_log:
        proc = subprocess.run(cmd, stdout=f_log, stderr=subprocess.STDOUT)
        return shard, proc.returncode


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Parallel launcher for motif/check_protein_rna_contacts_aa.py"
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("/datapool/data2/home/ruihan/data/PDB_sync"),
        help="PDB_sync root directory (contains shard subdirs like aa, ab, ...).",
    )
    parser.add_argument("--workers", type=int, default=128, help="Number of parallel workers.")
    parser.add_argument(
        "--distance",
        type=float,
        default=4.5,
        help="Protein-RNA contact cutoff in angstrom.",
    )
    parser.add_argument(
        "--require-rna-chains",
        type=int,
        default=2,
        help="Approximate dsRNA: minimum RNA chains requirement.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max number of files per shard (0 means no limit).",
    )
    parser.add_argument(
        "--shards",
        type=str,
        default="",
        help="Optional comma-separated shard list, e.g. 'aa,ab,ac'. If empty, auto-discover.",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path.cwd() / "output",
        help="Results directory (default: ./output relative to current working dir).",
    )

    args = parser.parse_args(argv)

    inner_script = Path(__file__).parent / "check_protein_rna_contacts_aa.py"
    if not inner_script.exists():
        print(f"[ERROR] inner script not found: {inner_script}", file=sys.stderr)
        return 2

    if args.shards.strip():
        shards = [s.strip() for s in args.shards.split(",") if s.strip()]
    else:
        shards = discover_shards(args.root)

    if not shards:
        print("[WARN] No shards found to process.", file=sys.stderr)
        return 0

    print(f"Shards to process: {len(shards)}")
    print(f"Workers: {args.workers}")
    print(f"Outdir: {args.outdir}")

    failures = []

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = [
            ex.submit(
                run_one,
                inner_script,
                args.root,
                shard,
                args.distance,
                args.require_rna_chains,
                args.limit,
                args.outdir,
            )
            for shard in shards
        ]

        for fut in tqdm(as_completed(futures)):
            shard, rc = fut.result()
            if rc != 0:
                failures.append((shard, rc))
                print(f"[WARN] shard {shard} exit_code={rc}")

    print(f"Done. Failures: {len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


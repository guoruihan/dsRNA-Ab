#!/usr/bin/env python3
"""
Scan PDB structures whose PDB ID has middle 2 letters == 'aa'
(per motif/db_description.md sharding rule, i.e. scan ROOT/aa/*.cif.gz),
and report whether any protein has contacts with RNA within a distance cutoff.

This is a "simple check" heuristic:
  - protein residues are amino acids (Bio.PDB Polypeptide.is_aa)
  - RNA residues are nucleotide-like residue names (A/C/G/U and DNA variants)
  - "satisfy condition" == protein-RNA atom pairs within `--distance` Å
  - optional: require at least N RNA chains (default 2) to approximate dsRNA

Example:
  python3 motif/check_protein_rna_contacts_aa.py --root /datapool/data2/home/ruihan/data/PDB_sync
"""

from __future__ import annotations

import argparse
import gzip
import os
import sys
import tempfile
from pathlib import Path

from Bio.PDB import MMCIFParser
from Bio.PDB.NeighborSearch import NeighborSearch
from Bio.PDB.Polypeptide import is_aa


RNA_RESNAMES = {
    # Common 1- and 2-letter residue names found in PDB/mmCIF
    "A",
    "C",
    "G",
    "U",
    # DNA variants (often appear in protein-RNA/DNA complexes)
    "DA",
    "DC",
    "DG",
    "DT",
    "DU",
    # Sometimes mmCIF uses these 3-letter forms
    "ADE",
    "CYT",
    "GUA",
    "URA",
    "URI",
    "THY",
    "DT",
    "C5P",  # edge case; safe to keep as "nucleotide-like"
}


def is_rna_residue(residue) -> bool:
    resname = (residue.get_resname() or "").strip().upper()
    return resname in RNA_RESNAMES


def is_protein_residue(residue) -> bool:
    # standard=False to include more amino-acid-like residues
    return bool(is_aa(residue, standard=False))


def parse_structure_from_cif_gz(cif_gz_path: Path):
    # Bio.PDB MMCIFParser requires a real file path, so we decompress to temp.
    with gzip.open(cif_gz_path, "rb") as f_in:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".cif") as f_tmp:
            tmp_path = Path(f_tmp.name)
            f_tmp.write(f_in.read())

    try:
        parser = MMCIFParser(QUIET=True)
        # id parameter is arbitrary but should be stable for caching/debug
        structure = parser.get_structure(cif_gz_path.stem, str(tmp_path))
    finally:
        # Best-effort cleanup
        try:
            os.remove(tmp_path)
        except OSError:
            pass
    return structure


def analyze_one_structure(structure, distance: float, require_rna_chains: int):
    protein_atoms = []
    rna_atoms = []
    protein_chains = set()
    rna_chains = set()

    # Collect atoms from classified residues to avoid mixing everything.
    for model in structure:
        for chain in model:
            chain_id = chain.id
            for residue in chain:
                hetflag = residue.id[0]
                # Skip waters/unknowns early. Residue classification below is "best effort".
                if str(hetflag).upper() == "W":
                    continue

                if is_protein_residue(residue):
                    protein_chains.add(chain_id)
                    for atom in residue.get_atoms():
                        protein_atoms.append(atom)
                elif is_rna_residue(residue):
                    rna_chains.add(chain_id)
                    for atom in residue.get_atoms():
                        rna_atoms.append(atom)

    if not protein_atoms or not rna_atoms:
        return {
            "satisfy": False,
            "protein_chains": sorted(protein_chains),
            "rna_chains": sorted(rna_chains),
            "min_dist": None,
        }

    if len(rna_chains) < require_rna_chains:
        return {
            "satisfy": False,
            "protein_chains": sorted(protein_chains),
            "rna_chains": sorted(rna_chains),
            "min_dist": None,
            "reason": f"rna_chains<{require_rna_chains}",
        }

    ns = NeighborSearch(rna_atoms)

    min_dist = None
    contacting_protein_chains = set()
    contacting_rna_chains = set()

    for atom in protein_atoms:
        neighbors = ns.search(atom.coord, distance)
        if not neighbors:
            continue

        contacting_protein_chains.add(atom.get_parent().get_parent().id)  # chain id
        for nb in neighbors:
            contacting_rna_chains.add(nb.get_parent().get_parent().id)
            d = (atom - nb)
            if min_dist is None or d < min_dist:
                min_dist = float(d)

    satisfy = min_dist is not None
    return {
        "satisfy": satisfy,
        "protein_chains": sorted(contacting_protein_chains) if satisfy else sorted(protein_chains),
        "rna_chains": sorted(contacting_rna_chains) if satisfy else sorted(rna_chains),
        "min_dist": min_dist,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Check protein-RNA contacts in PDB_sync/<shard>/ (shard='aa' by default)."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("/datapool/data2/home/ruihan/data/PDB_sync"),
        help="PDB_sync root directory (see motif/db_description.md).",
    )
    parser.add_argument("--shard", type=str, default="aa", help="Shard directory name (default: aa).")
    parser.add_argument(
        "--distance",
        type=float,
        default=4.5,
        help="Protein-RNA contact cutoff in angstrom (default: 4.5).",
    )
    parser.add_argument(
        "--require-rna-chains",
        type=int,
        default=2,
        help="Approximate dsRNA: require at least this many RNA chains (default 2).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max number of files to process (0 means no limit).",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path.cwd() / "output",
        help="Write per-shard results into this directory (default: ./output relative to current working dir).",
    )
    args = parser.parse_args(argv)

    shard_dir = args.root / args.shard
    if not shard_dir.exists():
        print(f"[ERROR] shard dir not found: {shard_dir}", file=sys.stderr)
        return 2

    cif_files = sorted(shard_dir.glob("*.cif.gz"))
    if not cif_files:
        print(f"[WARN] no .cif.gz files found under: {shard_dir}", file=sys.stderr)
        return 0

    if args.limit and args.limit > 0:
        cif_files = cif_files[: args.limit]

    satisfied = []
    total = 0

    for cif_gz_path in cif_files:
        total += 1
        pdb_id = cif_gz_path.name.replace(".cif.gz", "")
        try:
            structure = parse_structure_from_cif_gz(cif_gz_path)
            res = analyze_one_structure(
                structure,
                distance=args.distance,
                require_rna_chains=args.require_rna_chains,
            )
        except Exception as e:
            print(f"[WARN] failed: {pdb_id} ({e.__class__.__name__}: {e})", file=sys.stderr)
            continue

        if res.get("satisfy"):
            satisfied.append((pdb_id, res.get("min_dist"), res.get("protein_chains"), res.get("rna_chains")))

    args.outdir.mkdir(parents=True, exist_ok=True)

    # Write per-shard result for later collection.
    # Format: TSV with header.
    out_tsv = args.outdir / f"{args.shard}.tsv"
    tmp_tsv = out_tsv.with_suffix(out_tsv.suffix + ".tmp")
    with tmp_tsv.open("w", encoding="utf-8", newline="") as f_out:
        f_out.write("pdb_id\tmin_dist_A\tprotein_chains\trna_chains\n")
        for pdb_id, min_dist, protein_chains, rna_chains in sorted(
            satisfied, key=lambda x: (x[1] if x[1] is not None else 1e9)
        ):
            md = f"{min_dist:.3f}" if min_dist is not None else "NA"
            f_out.write(
                f"{pdb_id}\t{md}\t{','.join(protein_chains)}\t{','.join(rna_chains)}\n"
            )
    tmp_tsv.replace(out_tsv)

    print(f"Processed files: {total}")
    print(f"Satisfied: {len(satisfied)}")
    # Print top results sorted by min_dist
    satisfied_sorted = sorted(satisfied, key=lambda x: (x[1] if x[1] is not None else 1e9))
    for pdb_id, min_dist, protein_chains, rna_chains in satisfied_sorted[:200]:
        md = f"{min_dist:.2f}" if min_dist is not None else "NA"
        print(f"{pdb_id}\tmin_dist_A={md}\tprotein_chains={protein_chains}\trna_chains={rna_chains}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


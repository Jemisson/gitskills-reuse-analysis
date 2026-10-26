#!/usr/bin/env python3

"""Score cross-repository adoption candidates without asserting unobserved ancestry."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd

from _provenance import atomic_json, base_manifest, ensure_new_outputs, file_record


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATES = ROOT / "outputs/rq2/adoption_candidates_v3/adoption_candidates.csv"
DEFAULT_OUTPUT = ROOT / "outputs/rq2/genealogical_relations_v4"
SCORING_VERSION = "genealogical-candidate-confidence-v1.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", default=str(DEFAULT_CANDIDATES))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def score_candidates(candidates: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if candidates.empty:
        accepted_columns = list(candidates.columns) + [
            "confidence_level", "relation_status", "ambiguous_predecessors", "scoring_version"
        ]
        rejected_columns = list(candidates.columns) + ["rejection_reason", "scoring_version"]
        return pd.DataFrame(columns=accepted_columns), pd.DataFrame(columns=rejected_columns)
    ordered = candidates.loc[candidates["temporal_order"].eq("strictly_later")].copy()
    rejected = candidates.loc[~candidates["temporal_order"].eq("strictly_later")].copy()
    predecessor_counts = ordered.groupby("target_diff_id")["source_diff_id"].nunique()
    ordered["confidence_level"] = "C"
    strong = (
        ordered["same_old_blob"].eq(True)
        & ordered["same_new_blob"].eq(True)
        & ordered["change_operation"].eq("modification")
    )
    ordered.loc[strong, "confidence_level"] = "B"
    ordered["relation_status"] = "compatible_adoption_candidate"
    ordered["ambiguous_predecessors"] = (
        ordered["target_diff_id"].map(predecessor_counts).fillna(0).astype(int) > 1
    )
    ordered["scoring_version"] = SCORING_VERSION
    rejected["rejection_reason"] = "direction_indeterminate_timestamp_tie"
    rejected["scoring_version"] = SCORING_VERSION
    return ordered, rejected


def atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def main() -> None:
    args = parse_args()
    candidates_path = Path(args.candidates).expanduser().resolve()
    if not candidates_path.is_file():
        raise FileNotFoundError(candidates_path)
    output_dir = Path(args.output_dir).expanduser().resolve()
    relations_path = output_dir / "genealogical_relations.csv"
    rejected_path = output_dir / "rejected_relations.csv"
    manifest_path = output_dir / "genealogy_manifest.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    ensure_new_outputs([relations_path, rejected_path, manifest_path], args.overwrite)
    candidates = pd.read_csv(candidates_path)
    relations, rejected = score_candidates(candidates)
    atomic_csv(relations, relations_path)
    atomic_csv(rejected, rejected_path)
    manifest = base_manifest(Path(__file__), vars(args))
    manifest["inputs"] = [file_record(candidates_path)]
    manifest["confidence_rules"] = {
        "A": "Reserved for explicit provenance or shared reachable Git ancestry; unavailable in this dataset.",
        "B": "Exact normalized modification, exact anchor family, strict temporal order, and identical non-removal old/new blob transition.",
        "C": "Exact normalized patch and anchor family with strict temporal order, but transition differs or the operation is an addition/removal with low specificity.",
        "D": "Direction indeterminate or required evidence absent; rejected from directed relations.",
    }
    manifest["interpretation"] = (
        "B and C are compatible adoption candidates, not proven transmission edges or origin assignments."
    )
    manifest["results"] = {
        "accepted_candidate_relations": len(relations),
        "confidence_B": int(relations.get("confidence_level", pd.Series(dtype=str)).eq("B").sum()),
        "confidence_C": int(relations.get("confidence_level", pd.Series(dtype=str)).eq("C").sum()),
        "ambiguous_candidate_relations": int(relations.get("ambiguous_predecessors", pd.Series(dtype=bool)).eq(True).sum()),
        "rejected_direction_indeterminate": len(rejected),
    }
    manifest["limitations"] = [
        "No relation reaches confidence A because explicit provenance/shared ancestry was not collected.",
        "Commit timestamps establish observed order, not causal transmission.",
        "A common unobserved source can generate identical patches in multiple repositories.",
    ]
    manifest["outputs"] = [file_record(relations_path), file_record(rejected_path)]
    atomic_json(manifest_path, manifest)
    print(manifest["results"])
    print(f"Manifesto: {manifest_path}")


if __name__ == "__main__":
    main()

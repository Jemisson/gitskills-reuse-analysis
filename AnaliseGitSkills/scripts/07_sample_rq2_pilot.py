#!/usr/bin/env python3

"""Draw a reproducible RQ2 recoverability pilot from exact-copy anchors."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd

from _provenance import atomic_json, base_manifest, ensure_new_outputs, file_record


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FRAME = (
    ROOT / "outputs" / "rq2" / "frame" / "rq2_exact_copy_occurrences.parquet"
)
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "rq2" / "pilot"


def reuse_bin(value: int) -> str:
    if value == 2:
        return "02"
    if value <= 5:
        return "03-05"
    if value <= 10:
        return "06-10"
    if value <= 50:
        return "11-50"
    return "51+"


def history_bin(fetched: int, occurrences: int) -> str:
    if fetched == 0:
        return "none"
    if fetched == occurrences:
        return "all"
    return "partial"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frame", default=str(DEFAULT_FRAME))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--per-stratum", type=int, default=5)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def build_anchor_table(frame: pd.DataFrame) -> pd.DataFrame:
    grouped = frame.groupby("anchor_file_sha", sort=True, observed=True)
    anchors = grouped.agg(
        occurrence_count=("occurrence_count", "first"),
        reuse_count=("reuse_count", "first"),
        observed_occurrences=("path", "size"),
        distinct_repositories=("repo_full_name", "nunique"),
        history_fetched_occurrences=("history_fetched", "sum"),
        any_repo_is_fork=("repo_is_fork", "max"),
        representative_count=("dedup_primary", "sum"),
    ).reset_index()
    if not (
        anchors["occurrence_count"] == anchors["observed_occurrences"]
    ).all():
        raise ValueError("Contagens de ocorrência inconsistentes no frame")
    if not (
        anchors["reuse_count"] == anchors["distinct_repositories"]
    ).all():
        raise ValueError("Contagens de repositório inconsistentes no frame")
    if not (anchors["representative_count"] == 1).all():
        raise ValueError("Cada âncora deve ter exatamente um representante")
    anchors["reuse_stratum"] = anchors["reuse_count"].map(reuse_bin)
    anchors["history_stratum"] = [
        history_bin(int(fetched), int(occurrences))
        for fetched, occurrences in zip(
            anchors["history_fetched_occurrences"],
            anchors["observed_occurrences"],
        )
    ]
    anchors["pilot_stratum"] = (
        anchors["reuse_stratum"] + "__" + anchors["history_stratum"]
    )
    return anchors


def atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        frame.to_csv(temporary, index=False)
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def main() -> None:
    args = parse_args()
    if args.per_stratum < 1:
        raise ValueError("--per-stratum deve ser positivo")
    frame_path = Path(args.frame).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    anchors_path = output_dir / "pilot_anchors.csv"
    occurrences_path = output_dir / "pilot_occurrences.csv"
    strata_path = output_dir / "pilot_strata.csv"
    manifest_path = output_dir / "pilot_manifest.json"
    if not frame_path.is_file():
        raise FileNotFoundError(frame_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    ensure_new_outputs(
        [anchors_path, occurrences_path, strata_path, manifest_path],
        args.overwrite,
    )

    frame = pd.read_parquet(frame_path)
    if frame.duplicated(["repo_full_name", "path"]).any():
        raise ValueError("Há ocorrências repo/path duplicadas")
    anchors = build_anchor_table(frame)

    sampled_parts = []
    for _, stratum in anchors.groupby("pilot_stratum", sort=True):
        n = min(args.per_stratum, len(stratum))
        sampled_parts.append(stratum.sample(n=n, random_state=args.seed))
    sample = (
        pd.concat(sampled_parts, ignore_index=True)
        .sort_values(["pilot_stratum", "anchor_file_sha"])
        .reset_index(drop=True)
    )
    sample["selection_probability_within_stratum"] = sample[
        "pilot_stratum"
    ].map(
        {
            name: min(args.per_stratum, len(group)) / len(group)
            for name, group in anchors.groupby("pilot_stratum", sort=True)
        }
    )
    selected = set(sample["anchor_file_sha"])
    pilot_occurrences = frame.loc[
        frame["anchor_file_sha"].isin(selected)
    ].sort_values(["anchor_file_sha", "repo_full_name", "path"])
    strata = (
        anchors.groupby("pilot_stratum", sort=True)
        .size()
        .rename("frame_anchors")
        .reset_index()
    )
    strata["sampled_anchors"] = strata["frame_anchors"].clip(
        upper=args.per_stratum
    )

    atomic_csv(sample, anchors_path)
    atomic_csv(pilot_occurrences, occurrences_path)
    atomic_csv(strata, strata_path)
    manifest = base_manifest(Path(__file__), vars(args))
    manifest["input"] = file_record(frame_path)
    manifest["purpose"] = (
        "Recoverability and protocol-calibration pilot only; "
        "not a confirmatory substantive sample."
    )
    manifest["stratification"] = ["reuse_stratum", "history_stratum"]
    manifest["invariants"] = {
        "frame_occurrences": len(frame),
        "frame_anchors": len(anchors),
        "available_strata": len(strata),
        "sampled_anchors": len(sample),
        "sampled_occurrences": len(pilot_occurrences),
        "seed": args.seed,
        "per_stratum_cap": args.per_stratum,
    }
    manifest["outputs"] = [
        file_record(anchors_path),
        file_record(occurrences_path),
        file_record(strata_path),
    ]
    atomic_json(manifest_path, manifest)
    print(manifest["invariants"])
    print(f"Manifesto: {manifest_path}")


if __name__ == "__main__":
    main()

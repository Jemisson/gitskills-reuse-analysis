#!/usr/bin/env python3

"""Build the exact-copy occurrence frame used to sample the RQ2 pilot."""

from __future__ import annotations

import argparse
import csv
import sqlite3
import time
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from _provenance import atomic_json, base_manifest, ensure_new_outputs, file_record


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT.parent / "Banco" / "agent_skills_release.db"
DEFAULT_REUSE = ROOT / "outputs" / "rq1" / "reuse_by_content.csv"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "rq2" / "frame"

SCHEMA = pa.schema(
    [
        ("anchor_file_sha", pa.string()),
        ("occurrence_count", pa.int64()),
        ("reuse_count", pa.int64()),
        ("repo_full_name", pa.string()),
        ("path", pa.string()),
        ("location_class", pa.string()),
        ("discovered_at", pa.string()),
        ("dedup_primary", pa.int8()),
        ("history_fetched", pa.int8()),
        ("first_commit_at", pa.string()),
        ("last_commit_at", pa.string()),
        ("commit_count", pa.int64()),
        ("repo_is_fork", pa.int8()),
        ("repo_created_at", pa.string()),
        ("repo_pushed_at", pa.string()),
    ]
)

OCCURRENCES_SQL = """
SELECT
    a.file_sha,
    a.repo_full_name,
    a.path,
    a.location_class,
    a.discovered_at,
    a.dedup_primary,
    a.history_fetched,
    a.first_commit_at,
    a.last_commit_at,
    a.commit_count,
    r.is_fork,
    r.created_at,
    r.pushed_at
FROM artifacts AS a
LEFT JOIN repos AS r
    ON r.full_name = a.repo_full_name
WHERE a.filename = 'SKILL.md'
  AND a.file_sha IS NOT NULL
"""


def nullable_int(value):
    return None if value is None else int(value)


def binary_int(value):
    return None if value is None else int(value == 1)


def load_reused_hashes(path: Path) -> dict[str, tuple[int, int]]:
    reused: dict[str, tuple[int, int]] = {}
    with path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        required = {"file_sha", "occurrence_count", "reuse_count"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError("CSV de reúso não possui as colunas obrigatórias")
        for row in reader:
            reuse_count = int(row["reuse_count"])
            if reuse_count > 1:
                reused[row["file_sha"]] = (
                    int(row["occurrence_count"]),
                    reuse_count,
                )
    return reused


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--reuse-file", default=str(DEFAULT_REUSE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--batch-size", type=int, default=20_000)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.batch_size < 1:
        raise ValueError("--batch-size deve ser positivo")
    db_path = Path(args.db).expanduser().resolve()
    reuse_path = Path(args.reuse_file).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    frame_path = output_dir / "rq2_exact_copy_occurrences.parquet"
    manifest_path = output_dir / "rq2_frame_manifest.json"
    if not db_path.is_file() or not reuse_path.is_file():
        raise FileNotFoundError("Banco ou CSV de reúso não encontrado")
    output_dir.mkdir(parents=True, exist_ok=True)
    ensure_new_outputs([frame_path, manifest_path], args.overwrite)

    reused = load_reused_hashes(reuse_path)
    expected_occurrences = sum(item[0] for item in reused.values())
    expected_repository_placements = sum(item[1] for item in reused.values())
    started = time.monotonic()

    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    cursor = connection.execute(OCCURRENCES_SQL)
    writer = pq.ParquetWriter(frame_path, SCHEMA, compression="zstd")
    written = 0
    repositories: set[str] = set()
    observed_per_hash: dict[str, int] = {}
    try:
        while rows := cursor.fetchmany(args.batch_size):
            output_rows = []
            for row in rows:
                counts = reused.get(row["file_sha"])
                if counts is None:
                    continue
                occurrence_count, reuse_count = counts
                output_rows.append(
                    {
                        "anchor_file_sha": row["file_sha"],
                        "occurrence_count": occurrence_count,
                        "reuse_count": reuse_count,
                        "repo_full_name": row["repo_full_name"],
                        "path": row["path"],
                        "location_class": row["location_class"],
                        "discovered_at": row["discovered_at"],
                        "dedup_primary": binary_int(row["dedup_primary"]),
                        "history_fetched": binary_int(row["history_fetched"]),
                        "first_commit_at": row["first_commit_at"],
                        "last_commit_at": row["last_commit_at"],
                        "commit_count": nullable_int(row["commit_count"]),
                        "repo_is_fork": binary_int(row["is_fork"]),
                        "repo_created_at": row["created_at"],
                        "repo_pushed_at": row["pushed_at"],
                    }
                )
                repositories.add(row["repo_full_name"])
                observed_per_hash[row["file_sha"]] = (
                    observed_per_hash.get(row["file_sha"], 0) + 1
                )
            if output_rows:
                writer.write_table(pa.Table.from_pylist(output_rows, schema=SCHEMA))
                written += len(output_rows)
    except BaseException:
        writer.close()
        frame_path.unlink(missing_ok=True)
        raise
    finally:
        writer.close()
        connection.close()

    mismatched = sum(
        observed_per_hash.get(file_sha, 0) != occurrence_count
        for file_sha, (occurrence_count, _) in reused.items()
    )
    if written != expected_occurrences or mismatched:
        frame_path.unlink(missing_ok=True)
        raise ValueError(
            "Frame incompleto: "
            f"observado={written}, esperado={expected_occurrences}, "
            f"hashes divergentes={mismatched}"
        )

    manifest = base_manifest(Path(__file__), vars(args))
    manifest["inputs"] = [file_record(db_path, include_hash=False), file_record(reuse_path)]
    manifest["query"] = OCCURRENCES_SQL.strip()
    manifest["scope"] = (
        "Exact-content anchors reused in at least two repositories; "
        "not genealogical families and not proof of ancestry."
    )
    manifest["invariants"] = {
        "anchor_hashes": len(reused),
        "occurrence_rows": written,
        "expected_occurrence_rows": expected_occurrences,
        "repository_placements": expected_repository_placements,
        "distinct_repositories": len(repositories),
        "hashes_with_count_mismatch": mismatched,
    }
    manifest["outputs"] = [file_record(frame_path)]
    manifest["elapsed_seconds"] = time.monotonic() - started
    atomic_json(manifest_path, manifest)
    print(manifest["invariants"])
    print(f"Manifesto: {manifest_path}")


if __name__ == "__main__":
    main()


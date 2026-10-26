#!/usr/bin/env python3

"""Build the two missing RQ1 inputs directly from the GitSkills SQLite DB."""

from __future__ import annotations

import argparse
import csv
import os
import sqlite3
import time
from pathlib import Path

from _provenance import atomic_json, base_manifest, ensure_new_outputs, file_record


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT.parent / "Banco" / "agent_skills_release.db"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "rq1" / "reproduced_inputs"

POPULATION_FILTER = """
dedup_primary = 1
AND filename = 'SKILL.md'
AND content_fetched = 1
AND content_sha_ok = 1
AND frontmatter_valid = 1
""".strip()

REUSE_SQL = f"""
WITH population AS (
    SELECT file_sha
    FROM artifacts
    WHERE {POPULATION_FILTER}
)
SELECT
    p.file_sha,
    COUNT(*) AS occurrence_count,
    COUNT(DISTINCT a.repo_full_name) AS reuse_count
FROM population AS p
JOIN artifacts AS a
    ON a.file_sha = p.file_sha
WHERE a.filename = 'SKILL.md'
GROUP BY p.file_sha
ORDER BY p.file_sha
"""

REPRESENTATIVE_SQL = f"""
SELECT
    file_sha,
    repo_full_name AS representative_repository
FROM artifacts
WHERE {POPULATION_FILTER}
ORDER BY file_sha
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera entradas auditáveis da RQ1 a partir do SQLite."
    )
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--batch-size", type=int, default=10_000)
    parser.add_argument(
        "--hash-database",
        action="store_true",
        help="Calcula SHA-256 do banco; pode demorar para o arquivo de 44 GB.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Permitido apenas para destinos explicitamente escolhidos pelo usuário.",
    )
    return parser.parse_args()


def write_query_csv(
    connection: sqlite3.Connection,
    query: str,
    destination: Path,
    columns: list[str],
    batch_size: int,
) -> tuple[int, dict[str, int]]:
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    cursor = connection.execute(query)
    row_count = 0
    totals = {column: 0 for column in columns if column.endswith("_count")}
    try:
        with temporary.open("w", encoding="utf-8", newline="") as output:
            writer = csv.writer(output)
            writer.writerow(columns)
            while rows := cursor.fetchmany(batch_size):
                writer.writerows(rows)
                row_count += len(rows)
                for row in rows:
                    for column, index in zip(columns, range(len(columns))):
                        if column in totals:
                            totals[column] += int(row[index])
            output.flush()
            os.fsync(output.fileno())
        temporary.replace(destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return row_count, totals


def main() -> None:
    args = parse_args()
    if args.batch_size < 1:
        raise ValueError("--batch-size deve ser positivo")

    db_path = Path(args.db).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    reuse_path = output_dir / "reuse_by_content.csv"
    representative_path = output_dir / "representative_repositories.csv"
    manifest_path = output_dir / "rq1_inputs_manifest.json"

    if not db_path.is_file():
        raise FileNotFoundError(f"Banco não encontrado: {db_path}")
    output_dir.mkdir(parents=True, exist_ok=True)
    ensure_new_outputs(
        [reuse_path, representative_path, manifest_path], args.overwrite
    )

    manifest = base_manifest(Path(__file__), vars(args))
    manifest["input_database"] = file_record(
        db_path, include_hash=args.hash_database
    )
    manifest["population_filter"] = POPULATION_FILTER
    manifest["queries"] = {
        "reuse_by_content": REUSE_SQL.strip(),
        "representative_repositories": REPRESENTATIVE_SQL.strip(),
    }

    started = time.monotonic()
    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    connection.execute("PRAGMA query_only = ON")
    connection.execute("BEGIN")
    try:
        schema_rows = connection.execute(
            "SELECT type, name, sql FROM sqlite_schema "
            "WHERE sql IS NOT NULL ORDER BY type, name"
        ).fetchall()
        manifest["sqlite"] = {
            "version": sqlite3.sqlite_version,
            "schema": schema_rows,
            "data_version": connection.execute(
                "PRAGMA data_version"
            ).fetchone()[0],
        }

        reuse_rows, reuse_totals = write_query_csv(
            connection,
            REUSE_SQL,
            reuse_path,
            ["file_sha", "occurrence_count", "reuse_count"],
            args.batch_size,
        )
        representative_rows, _ = write_query_csv(
            connection,
            REPRESENTATIVE_SQL,
            representative_path,
            ["file_sha", "representative_repository"],
            args.batch_size,
        )
        connection.commit()
    except BaseException:
        connection.rollback()
        reuse_path.unlink(missing_ok=True)
        representative_path.unlink(missing_ok=True)
        raise
    finally:
        connection.close()

    if reuse_rows != representative_rows:
        reuse_path.unlink(missing_ok=True)
        representative_path.unlink(missing_ok=True)
        raise ValueError(
            "As duas saídas têm números de linhas diferentes: "
            f"{reuse_rows} != {representative_rows}"
        )

    manifest["invariants"] = {
        "population_rows": reuse_rows,
        "representative_rows": representative_rows,
        **reuse_totals,
        "row_counts_equal": True,
    }
    manifest["outputs"] = [file_record(reuse_path), file_record(representative_path)]
    manifest["elapsed_seconds"] = time.monotonic() - started
    atomic_json(manifest_path, manifest)

    print(f"Conteúdos: {reuse_rows:,}")
    print(f"Ocorrências: {reuse_totals['occurrence_count']:,}")
    print(f"Presenças em repositórios: {reuse_totals['reuse_count']:,}")
    print(f"Manifesto: {manifest_path}")


if __name__ == "__main__":
    main()


#!/usr/bin/env python3

import argparse
import csv
import re
import sqlite3
import time
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REUSE_FILE = ROOT / "outputs" / "rq1" / "reuse_by_content.csv"
DEFAULT_OUTPUT = ROOT / "outputs" / "rq1" / "rq1_features.parquet"

URL_RE = re.compile(r"https?://[^\s<>\"]+|www\.[^\s<>\"]+", re.IGNORECASE)
FENCED_BLOCK_RE = re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL)
FENCE_LINE_RE = re.compile(r"^\s*(?:```|~~~)", re.MULTILINE)
INLINE_CODE_RE = re.compile(r"(?<!`)`[^`\n]+`(?!`)")
HEADING_RE = re.compile(r"^#{1,6}\s+\S+", re.MULTILINE)
LIST_ITEM_RE = re.compile(
    r"^\s*(?:[-*+]\s+\S+|\d+[.)]\s+\S+)",
    re.MULTILINE,
)
WORD_RE = re.compile(r"\b[\w'-]+\b", re.UNICODE)
SENTENCE_RE = re.compile(r"[.!?]+")
VOWEL_GROUP_RE = re.compile(r"[aeiouy]+", re.IGNORECASE)


SCHEMA = pa.schema(
    [
        ("file_sha", pa.string()),
        ("occurrence_count", pa.int64()),
        ("reuse_count", pa.int64()),
        ("is_reused", pa.int8()),
        ("extra_reuse", pa.int64()),
        ("text_length", pa.int64()),
        ("body_chars", pa.int64()),
        ("word_count", pa.int64()),
        ("line_count", pa.int64()),
        ("description_length", pa.int64()),
        ("description_word_count", pa.int64()),
        ("name_length", pa.int64()),
        ("url_count", pa.int64()),
        ("code_block_count", pa.int64()),
        ("inline_code_count", pa.int64()),
        ("heading_count", pa.int64()),
        ("list_item_count", pa.int64()),
        ("readability_flesch_english", pa.float64()),
        ("location_class", pa.string()),
        ("sibling_count", pa.int64()),
        ("sibling_bytes", pa.int64()),
        ("has_scripts", pa.int8()),
        ("has_references", pa.int8()),
        ("composition_truncated", pa.int8()),
        ("history_fetched", pa.int8()),
        ("commit_count", pa.int64()),
        ("first_commit_at", pa.string()),
        ("last_commit_at", pa.string()),
        ("repo_stars", pa.int64()),
        ("repo_forks", pa.int64()),
        ("repo_is_fork", pa.int8()),
        ("repo_language", pa.string()),
        ("repo_created_at", pa.string()),
        ("repo_pushed_at", pa.string()),
    ]
)


def nullable_int(value):
    if value is None:
        return None
    return int(value)


def binary_int(value):
    if value is None:
        return None
    return 1 if int(value) == 1 else 0


def count_syllables_english(word: str) -> int:
    cleaned = re.sub(r"[^a-z]", "", word.lower())

    if not cleaned:
        return 1

    if len(cleaned) <= 3:
        return 1

    cleaned = re.sub(
        r"(?:[^aeiouy]es|ed|[^aeiouy]e)$",
        "",
        cleaned,
    )
    cleaned = re.sub(r"^y", "", cleaned)

    return max(len(VOWEL_GROUP_RE.findall(cleaned)), 1)


def flesch_english(text: str):
    if not text or not text.strip():
        return None

    clean_text = FENCED_BLOCK_RE.sub(" ", text)
    words = WORD_RE.findall(clean_text)

    if not words:
        return None

    sentences = [
        item
        for item in SENTENCE_RE.split(clean_text)
        if item.strip()
    ]

    sentence_count = max(len(sentences), 1)
    syllable_count = sum(
        count_syllables_english(word)
        for word in words
    )

    score = (
        206.835
        - 1.015 * (len(words) / sentence_count)
        - 84.6 * (syllable_count / len(words))
    )

    return round(float(score), 4)


def extract_text_metrics(content, name, description):
    content = content or ""
    name = name or ""
    description = description or ""

    words = WORD_RE.findall(content)
    fence_count = len(FENCE_LINE_RE.findall(content))

    return {
        "text_length": len(content),
        "word_count": len(words),
        "line_count": len(content.splitlines()),
        "description_length": len(description),
        "description_word_count": len(
            WORD_RE.findall(description)
        ),
        "name_length": len(name),
        "url_count": len(URL_RE.findall(content)),
        "code_block_count": fence_count // 2,
        "inline_code_count": len(
            INLINE_CODE_RE.findall(content)
        ),
        "heading_count": len(
            HEADING_RE.findall(content)
        ),
        "list_item_count": len(
            LIST_ITEM_RE.findall(content)
        ),
        "readability_flesch_english": flesch_english(
            content
        ),
    }


def load_reuse_map(path: Path):
    reuse_map = {}

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as source:
        reader = csv.DictReader(source)

        for row in reader:
            reuse_map[row["file_sha"]] = (
                int(row["occurrence_count"]),
                int(row["reuse_count"]),
            )

    return reuse_map


def parse_args():
    parser = argparse.ArgumentParser(
        description="Extrai métricas da população principal da RQ1."
    )

    parser.add_argument(
        "--db",
        required=True,
        help="Caminho do banco SQLite GitSkills.",
    )
    parser.add_argument(
        "--reuse-file",
        default=str(DEFAULT_REUSE_FILE),
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5000,
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limite utilizado somente para testes.",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    db_path = Path(args.db).expanduser().resolve()
    reuse_path = Path(args.reuse_file).resolve()
    output_path = Path(args.output).resolve()

    if not db_path.exists():
        raise FileNotFoundError(
            f"Banco não encontrado: {db_path}"
        )

    if not reuse_path.exists():
        raise FileNotFoundError(
            f"Arquivo de reúso não encontrado: {reuse_path}"
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("Carregando contagens de reúso...")
    reuse_map = load_reuse_map(reuse_path)
    print(f"Hashes carregados: {len(reuse_map):,}")

    database_uri = f"file:{db_path}?mode=ro"
    connection = sqlite3.connect(
        database_uri,
        uri=True,
    )
    connection.row_factory = sqlite3.Row

    query = """
    SELECT
        a.file_sha,
        a.content,
        a.name,
        a.description,
        a.body_chars,
        a.location_class,
        a.sibling_count,
        a.sibling_bytes,
        a.has_scripts,
        a.has_references,
        a.composition_truncated,
        a.history_fetched,
        a.commit_count,
        a.first_commit_at,
        a.last_commit_at,
        r.stars AS repo_stars,
        r.forks AS repo_forks,
        r.is_fork AS repo_is_fork,
        r.language AS repo_language,
        r.created_at AS repo_created_at,
        r.pushed_at AS repo_pushed_at
    FROM artifacts AS a
    LEFT JOIN repos AS r
        ON r.full_name = a.repo_full_name
    WHERE a.dedup_primary = 1
      AND a.filename = 'SKILL.md'
      AND a.content_fetched = 1
      AND a.content_sha_ok = 1
      AND a.frontmatter_valid = 1
    """

    parameters = []

    if args.limit is not None:
        query += " LIMIT ?"
        parameters.append(args.limit)

    cursor = connection.execute(
        query,
        parameters,
    )

    writer = pq.ParquetWriter(
        output_path,
        SCHEMA,
        compression="zstd",
    )

    processed = 0
    started_at = time.time()

    try:
        while True:
            database_rows = cursor.fetchmany(
                args.batch_size
            )

            if not database_rows:
                break

            output_rows = []

            for row in database_rows:
                file_sha = row["file_sha"]

                if file_sha not in reuse_map:
                    raise KeyError(
                        f"Hash sem contagem de reúso: {file_sha}"
                    )

                occurrence_count, reuse_count = (
                    reuse_map[file_sha]
                )

                metrics = extract_text_metrics(
                    row["content"],
                    row["name"],
                    row["description"],
                )

                output_row = {
                    "file_sha": file_sha,
                    "occurrence_count": occurrence_count,
                    "reuse_count": reuse_count,
                    "is_reused": 1 if reuse_count > 1 else 0,
                    "extra_reuse": reuse_count - 1,
                    "body_chars": nullable_int(
                        row["body_chars"]
                    ),
                    "location_class": row["location_class"],
                    "sibling_count": nullable_int(
                        row["sibling_count"]
                    ),
                    "sibling_bytes": nullable_int(
                        row["sibling_bytes"]
                    ),
                    "has_scripts": binary_int(
                        row["has_scripts"]
                    ),
                    "has_references": binary_int(
                        row["has_references"]
                    ),
                    "composition_truncated": binary_int(
                        row["composition_truncated"]
                    ),
                    "history_fetched": binary_int(
                        row["history_fetched"]
                    ),
                    "commit_count": nullable_int(
                        row["commit_count"]
                    ),
                    "first_commit_at": row["first_commit_at"],
                    "last_commit_at": row["last_commit_at"],
                    "repo_stars": nullable_int(
                        row["repo_stars"]
                    ),
                    "repo_forks": nullable_int(
                        row["repo_forks"]
                    ),
                    "repo_is_fork": binary_int(
                        row["repo_is_fork"]
                    ),
                    "repo_language": (
                        row["repo_language"] or "Unknown"
                    ),
                    "repo_created_at": row["repo_created_at"],
                    "repo_pushed_at": row["repo_pushed_at"],
                    **metrics,
                }

                output_rows.append(output_row)

            table = pa.Table.from_pylist(
                output_rows,
                schema=SCHEMA,
            )
            writer.write_table(table)

            processed += len(output_rows)

            if processed % 50000 == 0:
                elapsed = time.time() - started_at
                rate = processed / elapsed

                print(
                    f"Processados: {processed:,} "
                    f"| taxa: {rate:,.0f} registros/s",
                    flush=True,
                )
    finally:
        writer.close()
        connection.close()

    elapsed = time.time() - started_at

    print(f"Total processado: {processed:,}")
    print(f"Tempo: {elapsed / 60:.2f} minutos")
    print(f"Arquivo gerado: {output_path}")


if __name__ == "__main__":
    main()

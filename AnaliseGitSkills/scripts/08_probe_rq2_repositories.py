#!/usr/bin/env python3

"""Probe public Git accessibility for repositories in the frozen RQ2 pilot."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import os
import re
import subprocess
import threading
import time
from pathlib import Path

import pandas as pd

from _provenance import atomic_json, base_manifest, ensure_new_outputs, file_record


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "outputs" / "rq2" / "pilot" / "pilot_occurrences.csv"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "rq2" / "recoverability"
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--retry-base-seconds", type=float, default=2.0)
    parser.add_argument("--requests-per-second", type=float, default=2.0)
    parser.add_argument(
        "--cache-file",
        default=None,
        help="CSV anterior; somente resultados acessíveis e completos são reutilizados.",
    )
    parser.add_argument(
        "--limit-repositories",
        type=int,
        default=None,
        help="Somente smoke test; uma execução limitada não conclui o piloto.",
    )
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def classify_failure(stderr: str, return_code: int) -> str:
    lowered = stderr.lower()
    if "repository not found" in lowered:
        return "not_publicly_accessible_or_missing"
    if "authentication" in lowered or "could not read username" in lowered:
        # GitHub can return this response for private/missing repositories and
        # under transient anonymous-access controls. It is not classifiable.
        return "inconclusive_access_failure"
    if "could not resolve host" in lowered or "failed to connect" in lowered:
        return "network_error"
    return f"git_error_{return_code}"


class RateLimiter:
    def __init__(self, requests_per_second: float) -> None:
        self.interval = 1.0 / requests_per_second
        self.lock = threading.Lock()
        self.next_allowed = time.monotonic()

    def wait(self) -> None:
        with self.lock:
            now = time.monotonic()
            delay = max(0.0, self.next_allowed - now)
            self.next_allowed = max(now, self.next_allowed) + self.interval
        if delay:
            time.sleep(delay)


def deterministic_jitter(repository: str, attempt: int) -> float:
    digest = hashlib.sha256(f"{repository}:{attempt}".encode()).digest()
    return int.from_bytes(digest[:4], "big") / (2**32 - 1)


def probe_once(
    repository: str,
    timeout_seconds: float,
    limiter: RateLimiter,
) -> dict[str, object]:
    if not REPOSITORY_RE.fullmatch(repository):
        return {
            "repo_full_name": repository,
            "status": "invalid_repository_name",
            "default_branch": None,
            "head_sha": None,
            "elapsed_seconds": 0.0,
            "stderr": "Repository name rejected before command execution",
        }
    url = f"https://github.com/{repository}.git"
    environment = os.environ.copy()
    environment["GIT_TERMINAL_PROMPT"] = "0"
    limiter.wait()
    started = time.monotonic()
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--symref", url, "HEAD"],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=environment,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        return {
            "repo_full_name": repository,
            "status": "timeout",
            "default_branch": None,
            "head_sha": None,
            "elapsed_seconds": time.monotonic() - started,
            "stderr": str(error),
        }

    default_branch = None
    head_sha = None
    for line in result.stdout.splitlines():
        if line.startswith("ref: refs/heads/") and line.endswith("\tHEAD"):
            default_branch = line.split("refs/heads/", 1)[1].split("\t", 1)[0]
        elif line.endswith("\tHEAD"):
            head_sha = line.split("\t", 1)[0]
    status = "accessible" if result.returncode == 0 and head_sha else classify_failure(
        result.stderr, result.returncode
    )
    return {
        "repo_full_name": repository,
        "status": status,
        "default_branch": default_branch,
        "head_sha": head_sha,
        "elapsed_seconds": time.monotonic() - started,
        "stderr": result.stderr.strip()[:1000] or None,
    }


def probe_repository(
    repository: str,
    timeout_seconds: float,
    attempts: int,
    retry_base_seconds: float,
    limiter: RateLimiter,
) -> dict[str, object]:
    started = time.monotonic()
    history = []
    last_result: dict[str, object] | None = None
    for attempt in range(1, attempts + 1):
        last_result = probe_once(repository, timeout_seconds, limiter)
        history.append(str(last_result["status"]))
        if last_result["status"] == "accessible":
            break
        if attempt < attempts:
            delay = retry_base_seconds * (2 ** (attempt - 1))
            delay += retry_base_seconds * deterministic_jitter(repository, attempt)
            time.sleep(delay)
    assert last_result is not None
    last_result["attempts"] = len(history)
    last_result["attempt_statuses"] = "|".join(history)
    last_result["elapsed_seconds"] = time.monotonic() - started
    last_result["source"] = "network"
    return last_result


def main() -> None:
    args = parse_args()
    if (
        args.workers < 1
        or args.timeout_seconds <= 0
        or args.attempts < 1
        or args.retry_base_seconds < 0
        or args.requests_per_second <= 0
    ):
        raise ValueError("workers, attempts, timeout e taxa devem ser positivos")
    input_path = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    results_path = output_dir / "repository_probe.csv"
    manifest_path = output_dir / "repository_probe_manifest.json"
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    ensure_new_outputs([results_path, manifest_path], args.overwrite)

    occurrences = pd.read_csv(input_path, usecols=["repo_full_name"])
    repositories = sorted(occurrences["repo_full_name"].dropna().unique())
    total_pilot_repositories = len(repositories)
    if args.limit_repositories is not None:
        if args.limit_repositories < 1:
            raise ValueError("--limit-repositories deve ser positivo")
        repositories = repositories[: args.limit_repositories]

    cached: dict[str, dict[str, object]] = {}
    if args.cache_file:
        cache_path = Path(args.cache_file).expanduser().resolve()
        if not cache_path.is_file():
            raise FileNotFoundError(cache_path)
        cache = pd.read_csv(cache_path)
        cache = cache.loc[
            (cache["status"] == "accessible")
            & cache["head_sha"].notna()
        ]
        for row in cache.to_dict(orient="records"):
            row["source"] = "cache"
            row["attempts"] = 0
            row["attempt_statuses"] = "cached_accessible"
            row["elapsed_seconds"] = 0.0
            cached[str(row["repo_full_name"])] = row

    pending = [repository for repository in repositories if repository not in cached]
    limiter = RateLimiter(args.requests_per_second)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        network_rows = list(
            executor.map(
                lambda repository: probe_repository(
                    repository,
                    args.timeout_seconds,
                    args.attempts,
                    args.retry_base_seconds,
                    limiter,
                ),
                pending,
            )
        )
    rows = [cached[repository] for repository in repositories if repository in cached]
    rows.extend(network_rows)
    results = pd.DataFrame(rows).sort_values("repo_full_name")
    temporary = results_path.with_name(f".{results_path.name}.{os.getpid()}.tmp")
    try:
        results.to_csv(temporary, index=False)
        temporary.replace(results_path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise

    status_counts = {
        str(key): int(value)
        for key, value in results["status"].value_counts().sort_index().items()
    }
    manifest = base_manifest(Path(__file__), vars(args))
    manifest["input"] = file_record(input_path)
    manifest["scope"] = {
        "total_unique_pilot_repositories": total_pilot_repositories,
        "probed_repositories": len(repositories),
        "complete_pilot_probe": len(repositories) == total_pilot_repositories,
        "cached_accessible_repositories": len(repositories) - len(pending),
        "network_probed_repositories": len(pending),
        "probe_only": (
            "Accessibility of current Git HEAD; this does not establish that the "
            "snapshot path or complete history is recoverable."
        ),
    }
    manifest["status_counts"] = status_counts
    manifest["classification_note"] = (
        "Anonymous git failures are inconclusive unless the remote explicitly "
        "reports repository not found. Repeated full probes must not be used "
        "to estimate availability without retry/backoff and stability checks."
    )
    manifest["retry_policy"] = {
        "attempts": args.attempts,
        "exponential_base_seconds": args.retry_base_seconds,
        "deterministic_jitter_fraction": "[0, 1] times retry_base_seconds",
        "global_requests_per_second": args.requests_per_second,
        "cache_policy": "reuse accessible rows with a non-null HEAD only",
    }
    manifest["outputs"] = [file_record(results_path)]
    atomic_json(manifest_path, manifest)
    print(manifest["scope"])
    print(status_counts)
    print(f"Manifesto: {manifest_path}")


if __name__ == "__main__":
    main()

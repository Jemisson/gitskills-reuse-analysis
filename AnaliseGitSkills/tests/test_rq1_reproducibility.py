from __future__ import annotations

import csv
import math
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import importlib


build_inputs = importlib.import_module("00_build_rq1_inputs")
apply_fdr = importlib.import_module("04f_apply_fdr")
sample_rq2 = importlib.import_module("07_sample_rq2_pilot")
probe_rq2 = importlib.import_module("08_probe_rq2_repositories")
collect_rq2 = importlib.import_module("09_collect_rq2_histories")
extract_rq2_diffs = importlib.import_module("10_extract_rq2_diffs")
select_rq2_history = importlib.import_module("11_select_rq2_history_calibration")
classify_rq2_structured = importlib.import_module("12_classify_rq2_structured_diffs")
classify_rq3_behavioral = importlib.import_module("13_classify_rq3_behavioral_changes")
select_rq2_analytic = importlib.import_module("14_select_rq2_analytic_sample")
prepare_rq2_recovery = importlib.import_module("15_prepare_rq2_analytic_recovery")
generate_exploratory = importlib.import_module("16_generate_exploratory_rq2_rq3_results")
build_patch_signatures = importlib.import_module("17_build_patch_signatures")
find_adoptions = importlib.import_module("18_find_cross_repository_adoptions")
score_genealogy = importlib.import_module("19_score_genealogical_relations")
analyze_rq3_associations = importlib.import_module("22_analyze_rq3_associations")


ARTIFACTS_SCHEMA = """
CREATE TABLE artifacts (
    repo_full_name TEXT NOT NULL,
    path TEXT NOT NULL,
    filename TEXT,
    file_sha TEXT,
    content_fetched INTEGER,
    frontmatter_valid INTEGER,
    dedup_primary INTEGER,
    content_sha_ok INTEGER,
    PRIMARY KEY (repo_full_name, path)
)
"""


class BuildInputsTest(unittest.TestCase):
    def test_population_and_reuse_queries(self) -> None:
        connection = sqlite3.connect(":memory:")
        connection.execute(ARTIFACTS_SCHEMA)
        connection.executemany(
            "INSERT INTO artifacts VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("r/a", "SKILL.md", "SKILL.md", "sha-a", 1, 1, 1, 1),
                ("r/b", "SKILL.md", "SKILL.md", "sha-a", 1, 1, 0, 1),
                ("r/b", "copy/SKILL.md", "SKILL.md", "sha-a", 1, 1, 0, 1),
                ("r/c", "SKILL.md", "SKILL.md", "sha-b", 1, 1, 1, 1),
                ("r/d", "skill.md", "skill.md", "sha-b", 1, 1, 0, 1),
                ("r/e", "SKILL.md", "SKILL.md", "bad", 1, 0, 1, 1),
            ],
        )

        reuse = connection.execute(build_inputs.REUSE_SQL).fetchall()
        representatives = connection.execute(
            build_inputs.REPRESENTATIVE_SQL
        ).fetchall()
        connection.close()

        self.assertEqual(reuse, [("sha-a", 3, 2), ("sha-b", 1, 1)])
        self.assertEqual(
            representatives, [("sha-a", "r/a"), ("sha-b", "r/c")]
        )

    def test_csv_writer_counts_and_header(self) -> None:
        connection = sqlite3.connect(":memory:")
        connection.execute(ARTIFACTS_SCHEMA)
        connection.execute(
            "INSERT INTO artifacts VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("r/a", "SKILL.md", "SKILL.md", "sha-a", 1, 1, 1, 1),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reuse.csv"
            rows, totals = build_inputs.write_query_csv(
                connection,
                build_inputs.REUSE_SQL,
                path,
                ["file_sha", "occurrence_count", "reuse_count"],
                1,
            )
            with path.open(newline="", encoding="utf-8") as source:
                content = list(csv.reader(source))
        connection.close()
        self.assertEqual(rows, 1)
        self.assertEqual(totals, {"occurrence_count": 1, "reuse_count": 1})
        self.assertEqual(
            content,
            [
                ["file_sha", "occurrence_count", "reuse_count"],
                ["sha-a", "1", "1"],
            ],
        )


class FdrTest(unittest.TestCase):
    def test_benjamini_hochberg_known_values(self) -> None:
        source = pd.Series([0.01, 0.04, 0.03, 0.002])
        observed = apply_fdr.benjamini_hochberg(source)
        expected = np.array([0.02, 0.04, 0.04, 0.008])
        np.testing.assert_allclose(observed.to_numpy(), expected)

    def test_benjamini_hochberg_rejects_invalid_values(self) -> None:
        for values in ([0.1, -0.1], [0.1, 1.1], [0.1, np.nan]):
            with self.subTest(values=values), self.assertRaises(ValueError):
                apply_fdr.benjamini_hochberg(pd.Series(values))


class Rq2PilotTest(unittest.TestCase):
    def test_strata_boundaries(self) -> None:
        self.assertEqual(
            [sample_rq2.reuse_bin(value) for value in [2, 3, 5, 6, 10, 11, 50, 51]],
            ["02", "03-05", "03-05", "06-10", "06-10", "11-50", "11-50", "51+"],
        )
        self.assertEqual(sample_rq2.history_bin(0, 3), "none")
        self.assertEqual(sample_rq2.history_bin(1, 3), "partial")
        self.assertEqual(sample_rq2.history_bin(3, 3), "all")

    def test_anchor_invariants(self) -> None:
        frame = pd.DataFrame(
            {
                "anchor_file_sha": ["a", "a", "b", "b", "b"],
                "occurrence_count": [2, 2, 3, 3, 3],
                "reuse_count": [2, 2, 3, 3, 3],
                "repo_full_name": ["r1", "r2", "r1", "r2", "r3"],
                "path": ["a", "a", "b", "b", "b"],
                "history_fetched": [0, 0, 1, 0, 0],
                "repo_is_fork": [0, 0, 0, 1, 0],
                "dedup_primary": [1, 0, 0, 1, 0],
            }
        )
        anchors = sample_rq2.build_anchor_table(frame)
        observed = dict(zip(anchors.anchor_file_sha, anchors.pilot_stratum))
        self.assertEqual(observed, {"a": "02__none", "b": "03-05__partial"})


class RepositoryProbeTest(unittest.TestCase):
    def test_failure_taxonomy_is_cautious(self) -> None:
        self.assertEqual(
            probe_rq2.classify_failure("Repository not found", 128),
            "not_publicly_accessible_or_missing",
        )
        self.assertEqual(
            probe_rq2.classify_failure("could not read Username", 128),
            "inconclusive_access_failure",
        )
        self.assertEqual(
            probe_rq2.classify_failure("Could not resolve host", 128),
            "network_error",
        )

    def test_jitter_is_deterministic_and_bounded(self) -> None:
        first = probe_rq2.deterministic_jitter("owner/repository", 1)
        second = probe_rq2.deterministic_jitter("owner/repository", 1)
        self.assertEqual(first, second)
        self.assertGreaterEqual(first, 0.0)
        self.assertLessEqual(first, 1.0)


class GitHistoryCollectorTest(unittest.TestCase):
    def git(self, repository: Path, *arguments: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    def test_history_follows_rename_and_detects_removed_head_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            work = root / "work"
            bare = root / "fixture.git"
            histories = root / "histories"
            work.mkdir()
            histories.mkdir()
            self.git(work, "init", "-b", "main")
            self.git(work, "config", "user.name", "Fixture")
            self.git(work, "config", "user.email", "fixture@example.invalid")

            old_path = work / "old" / "SKILL.md"
            old_path.parent.mkdir()
            old_path.write_text("---\nname: fixture\n---\ninitial\n", encoding="utf-8")
            self.git(work, "add", "old/SKILL.md")
            self.git(work, "commit", "-m", "add skill")
            add_commit = self.git(work, "rev-parse", "HEAD")
            anchor_sha = self.git(work, "rev-parse", "HEAD:old/SKILL.md")

            (work / "new").mkdir()
            self.git(work, "mv", "old/SKILL.md", "new/SKILL.md")
            self.git(work, "commit", "-m", "rename skill")
            rename_commit = self.git(work, "rev-parse", "HEAD")
            rename_parent = self.git(work, "rev-parse", "HEAD^")
            new_path = work / "new" / "SKILL.md"
            new_path.write_text(new_path.read_text() + "changed\n", encoding="utf-8")
            self.git(work, "add", "new/SKILL.md")
            self.git(work, "commit", "-m", "change skill")
            self.git(work, "checkout", "-b", "feature")
            new_path.write_text(new_path.read_text() + "feature\n", encoding="utf-8")
            self.git(work, "add", "new/SKILL.md")
            self.git(work, "commit", "-m", "feature change")
            self.git(work, "checkout", "main")
            new_path.write_text(new_path.read_text() + "master\n", encoding="utf-8")
            self.git(work, "add", "new/SKILL.md")
            self.git(work, "commit", "-m", "master change")
            merge = subprocess.run(
                ["git", "-C", str(work), "merge", "feature"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(merge.returncode, 0)
            new_path.write_text(
                "---\nname: fixture\n---\ninitial\nchanged\nmaster\nfeature\n",
                encoding="utf-8",
            )
            self.git(work, "add", "new/SKILL.md")
            self.git(work, "commit", "-m", "merge feature")
            self.git(work, "rm", "new/SKILL.md")
            self.git(work, "commit", "-m", "remove skill")
            remove_commit = self.git(work, "rev-parse", "HEAD")
            remove_parent = self.git(work, "rev-parse", "HEAD^")
            subprocess.run(
                ["git", "clone", "--bare", str(work), str(bare)],
                check=True,
                capture_output=True,
                text=True,
            )

            history = collect_rq2.history_for_path(bare, "new/SKILL.md", 10)
            self.assertGreaterEqual(len(history), 6)
            merge_event = next(item for item in history if len(item["parents"]) == 2)
            for parent in merge_event["parents"]:
                changes = extract_rq2_diffs.changes_for_commit(
                    bare, parent, merge_event["commit"], 10
                )
                selected, ambiguous = extract_rq2_diffs.select_change(
                    changes, "new/SKILL.md"
                )
                self.assertIsNotNone(selected)
                self.assertFalse(ambiguous)
                self.assertEqual(selected["new_path"], "new/SKILL.md")
            root_changes = extract_rq2_diffs.changes_for_commit(
                bare, None, add_commit, 10
            )
            self.assertEqual(root_changes[0]["status"], "A")
            rename_changes = extract_rq2_diffs.changes_for_commit(
                bare, rename_parent, rename_commit, 10
            )
            self.assertEqual(rename_changes[0]["status"], "R100")
            self.assertEqual(rename_changes[0]["old_path"], "old/SKILL.md")
            self.assertEqual(rename_changes[0]["new_path"], "new/SKILL.md")
            removal_changes = extract_rq2_diffs.changes_for_commit(
                bare, remove_parent, remove_commit, 10
            )
            self.assertEqual(removal_changes[0]["status"], "D")
            row = pd.Series(
                {
                    "repo_full_name": "fixture/repository",
                    "path": "new/SKILL.md",
                    "anchor_file_sha": anchor_sha,
                }
            )
            result = collect_rq2.inspect_occurrence(
                bare, row, histories, timeout_seconds=10
            )
            self.assertTrue(result["anchor_blob_available"])
            self.assertEqual(result["head_path_status"], "missing")
            self.assertGreaterEqual(result["history_commit_count"], 6)
            self.assertTrue(
                (root / str(result["history_jsonl"])).is_file()
            )

    def test_git_path_validation(self) -> None:
        self.assertEqual(collect_rq2.safe_git_path("a/SKILL.md"), "a/SKILL.md")
        for invalid in ("../SKILL.md", "/SKILL.md"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                collect_rq2.safe_git_path(invalid)


class Rq2DiffExtractorTest(unittest.TestCase):
    def test_name_status_parses_regular_and_rename_changes(self) -> None:
        observed = extract_rq2_diffs.parse_name_status(
            "M\tdocs/SKILL.md\nR095\told/SKILL.md\tnew/SKILL.md\n"
        )
        self.assertEqual(
            observed,
            [
                {
                    "status": "M",
                    "old_path": "docs/SKILL.md",
                    "new_path": "docs/SKILL.md",
                },
                {
                    "status": "R095",
                    "old_path": "old/SKILL.md",
                    "new_path": "new/SKILL.md",
                },
            ],
        )

    def test_line_counts_excludes_diff_headers(self) -> None:
        diff = "\n".join(
            [
                "--- a/SKILL.md",
                "+++ b/SKILL.md",
                " context",
                "-removed",
                "+added",
                "+another",
            ]
        )
        self.assertEqual(extract_rq2_diffs.line_counts(diff), (2, 1))

    def test_unselected_comparison_taxonomy(self) -> None:
        self.assertEqual(
            extract_rq2_diffs.classify_unselected_comparison("blob", "blob"),
            ("UNCHANGED", "unchanged_context"),
        )
        self.assertEqual(
            extract_rq2_diffs.classify_unselected_comparison(None, None),
            ("PATH_ABSENT", "path_absent_context"),
        )
        self.assertEqual(
            extract_rq2_diffs.classify_unselected_comparison("old", "new"),
            ("UNRESOLVED", "unresolved"),
        )


class Rq2HistoryCalibrationSelectionTest(unittest.TestCase):
    def test_selection_is_deterministic_stratified_and_repository_unique(self) -> None:
        occurrences = pd.DataFrame(
            {
                "anchor_file_sha": ["a", "a", "b", "b", "b"],
                "repo_full_name": ["r/1", "r/2", "r/2", "r/3", "r/4"],
                "path": ["a", "a", "b", "b", "b"],
            }
        )
        anchors = pd.DataFrame(
            {
                "anchor_file_sha": ["a", "b"],
                "pilot_stratum": ["low", "high"],
            }
        )
        arguments = (occurrences, anchors, {"r/1", "r/2", "r/3", "r/4"}, 1, 2, 7)
        first = select_rq2_history.select_repositories(*arguments)
        second = select_rq2_history.select_repositories(*arguments)
        pd.testing.assert_frame_equal(first[0], second[0])
        self.assertEqual(first[0]["repo_full_name"].nunique(), 2)
        self.assertEqual(set(first[0]["selection_stratum"]), {"high", "low"})
        self.assertEqual(int(first[2]["selected_repositories"].sum()), 2)


class Rq2StructuredDiffTest(unittest.TestCase):
    def test_markdown_regions_and_candidate_scopes(self) -> None:
        text = "\n".join(
            [
                "---",
                "name: fixture",
                "description: test",
                "---",
                "# Examples",
                "- Run `tool --help` at https://example.invalid/docs",
                "```sh",
                "tool run",
                "```",
            ]
        )
        lines, frontmatter = classify_rq2_structured.markdown_lines(text)
        self.assertEqual(frontmatter, "closed")
        self.assertEqual(lines[1].structural_region, "front_matter")
        self.assertIn("name", lines[1].semantic_candidates)
        self.assertEqual(lines[4].structural_region, "heading")
        self.assertIn("example_candidate", lines[5].semantic_candidates)
        self.assertIn("network_url_candidate", lines[5].semantic_candidates)
        self.assertIn("command_code_candidate", lines[5].semantic_candidates)
        self.assertEqual(lines[7].structural_region, "code_block")

    def test_changed_lines_and_operations(self) -> None:
        old, _ = classify_rq2_structured.markdown_lines("# Title\nold\n")
        new, _ = classify_rq2_structured.markdown_lines("# Title\nnew\n")
        changes = classify_rq2_structured.changed_lines(old, new)
        self.assertEqual([direction for direction, _ in changes], ["deleted", "added"])
        self.assertEqual(
            classify_rq2_structured.change_operation("M", "a b", "a  b"),
            "formatting",
        )
        self.assertEqual(
            classify_rq2_structured.change_operation("R100", "same", "same"),
            "movement",
        )
        self.assertEqual(
            classify_rq2_structured.change_operation("A", "", "new"),
            "addition",
        )

    def test_unified_diff_preserves_git_line_selection(self) -> None:
        old, _ = classify_rq2_structured.markdown_lines("# Title\nold\nkeep\n")
        new, _ = classify_rq2_structured.markdown_lines("# Title\nnew\nkeep\n")
        diff = "\n".join(
            [
                "diff --git a/SKILL.md b/SKILL.md",
                "--- a/SKILL.md",
                "+++ b/SKILL.md",
                "@@ -1,3 +1,3 @@",
                " # Title",
                "-old",
                "+new",
                " keep",
            ]
        )
        changes = classify_rq2_structured.changed_lines_from_unified_diff(
            diff, old, new
        )
        self.assertEqual(
            [(direction, line.line_number, line.text) for direction, line in changes],
            [("deleted", 2, "old"), ("added", 2, "new")],
        )

    def test_category_counts_report_lines_and_unique_events(self) -> None:
        events = pd.DataFrame(
            {"diff_id": ["a", "b"], "change_operation": ["addition", "addition"]}
        )
        evidence = pd.DataFrame(
            {
                "diff_id": ["a", "a", "b"],
                "direction": ["added", "added", "deleted"],
                "structural_region": ["paragraph", "paragraph", "heading"],
                "semantic_candidates": [
                    "instruction_candidate",
                    "instruction_candidate;network_url_candidate",
                    "",
                ],
            }
        )
        counts = classify_rq2_structured.category_counts(events, evidence)
        paragraph = counts.loc[
            counts["dimension"].eq("structural_region")
            & counts["category"].eq("paragraph")
        ].iloc[0]
        self.assertEqual(paragraph["line_count"], 2)
        self.assertEqual(paragraph["event_count"], 1)


class Rq3BehavioralClassifierTest(unittest.TestCase):
    def git(self, repository: Path, *arguments: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    def test_strict_and_broad_text_rules(self) -> None:
        strict = classify_rq3_behavioral.text_rule_hits(
            "curl https://example.invalid/api", "code_block", "MD_FENCED_CONTENT"
        )
        strict_pairs = {(item["target"], item["scenario"]) for item in strict}
        self.assertIn(("command", "strict"), strict_pairs)
        self.assertIn(("external_access", "strict"), strict_pairs)
        self.assertIn(("external_access", "broad"), strict_pairs)

        url_only = classify_rq3_behavioral.text_rule_hits(
            "Documentation: https://example.invalid", "paragraph", "MD_PARAGRAPH"
        )
        url_pairs = {(item["target"], item["scenario"]) for item in url_only}
        self.assertIn(("external_access", "broad"), url_pairs)
        self.assertNotIn(("external_access", "strict"), url_pairs)

        broad_command = classify_rq3_behavioral.text_rule_hits(
            "custom-tool --flag value", "code_block", "MD_FENCED_CONTENT"
        )
        command_pairs = {
            (item["target"], item["scenario"]) for item in broad_command
        }
        self.assertIn(("command", "broad"), command_pairs)
        self.assertNotIn(("command", "strict"), command_pairs)

    def test_script_and_sibling_rules(self) -> None:
        invoked = classify_rq3_behavioral.text_rule_hits(
            "python scripts/run.py", "code_block", "MD_FENCED_CONTENT"
        )
        pairs = {(item["target"], item["scenario"]) for item in invoked}
        self.assertIn(("script_reference", "strict"), pairs)
        self.assertIn(("script_reference", "broad"), pairs)
        self.assertTrue(
            classify_rq3_behavioral.is_broad_executable_candidate(
                "scripts/run.py", "100644", False
            )
        )
        self.assertFalse(
            classify_rq3_behavioral.is_broad_executable_candidate(
                "references/guide.md", "100644", False
            )
        )
        self.assertEqual(classify_rq3_behavioral.sibling_operation("D"), "removed")

    def test_binary_blob_shebang_probe(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            self.git(repository, "init", "-b", "main")
            self.git(repository, "config", "user.name", "Fixture")
            self.git(repository, "config", "user.email", "fixture@example.invalid")
            binary = repository / "image.png"
            binary.write_bytes(b"\x89PNG\r\n\x1a\n")
            script = repository / "run.py"
            script.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
            self.git(repository, "add", "image.png", "run.py")
            self.git(repository, "commit", "-m", "fixtures")
            binary_sha = self.git(repository, "rev-parse", "HEAD:image.png")
            script_sha = self.git(repository, "rev-parse", "HEAD:run.py")
            self.assertFalse(
                classify_rq3_behavioral.blob_has_shebang(repository, binary_sha, 10)
            )
            self.assertTrue(
                classify_rq3_behavioral.blob_has_shebang(repository, script_sha, 10)
            )


class Rq2AnalyticSampleTest(unittest.TestCase):
    def test_primary_strata_are_unique_and_weights_are_known(self) -> None:
        occurrences = pd.DataFrame(
            {
                "anchor_file_sha": ["a", "a", "b", "b", "b", "c"],
                "repo_full_name": ["r/1", "r/2", "r/1", "r/3", "r/4", "r/5"],
                "path": ["a", "a", "b", "b", "b", "c"],
            }
        )
        anchors = pd.DataFrame(
            {
                "anchor_file_sha": ["a", "b", "c"],
                "pilot_stratum": ["rare", "common", "rare"],
            }
        )
        frame, eligible = select_rq2_analytic.build_repository_frame(
            occurrences,
            anchors,
            {"r/1", "r/2", "r/3", "r/4", "r/5"},
            9,
        )
        self.assertEqual(frame["repo_full_name"].nunique(), len(frame))
        self.assertEqual(
            frame.loc[frame["repo_full_name"].eq("r/1"), "selection_stratum"].iloc[0],
            "common",
        )
        selected, selected_occurrences, strata = select_rq2_analytic.draw_sample(
            frame, eligible, 1
        )
        self.assertEqual(selected["repo_full_name"].nunique(), 2)
        self.assertTrue((selected["selection_probability_conditional"] > 0).all())
        self.assertTrue(
            np.allclose(
                selected["selection_probability_conditional"]
                * selected["sampling_weight_conditional"],
                1.0,
            )
        )
        self.assertTrue(set(selected_occurrences["repo_full_name"]) <= set(selected["repo_full_name"]))
        self.assertEqual(len(strata), 2)

    def test_failed_repository_partial_rows_are_not_eligible(self) -> None:
        selected = pd.DataFrame(
            {
                "repo_full_name": ["r/good", "r/bad", "r/bad"],
                "path": ["a/SKILL.md", "b/SKILL.md", "c/SKILL.md"],
                "selection_stratum": ["s", "s", "s"],
            }
        )
        histories = pd.DataFrame(
            {
                "occurrence_id": ["good", "partial"],
                "repo_full_name": ["r/good", "r/bad"],
                "path": ["a/SKILL.md", "b/SKILL.md"],
                "anchor_blob_available": [True, True],
                "head_path_status": ["matches_anchor", "matches_anchor"],
                "history_commit_count": [1, 1],
                "history_jsonl": ["histories/good.jsonl", "histories/partial.jsonl"],
            }
        )
        status = pd.DataFrame(
            {
                "repo_full_name": ["r/good", "r/bad"],
                "status": ["collected", "collection_failed"],
                "error": [None, "timeout"],
            }
        )
        flow = prepare_rq2_recovery.build_recovery_flow(selected, histories, status)
        self.assertTrue(flow.loc[flow["repo_full_name"].eq("r/good"), "analysis_eligible"].all())
        self.assertFalse(flow.loc[flow["repo_full_name"].eq("r/bad"), "analysis_eligible"].any())


class ExploratoryResultsTest(unittest.TestCase):
    def test_wilson_interval_contains_observed_proportion(self) -> None:
        low, high = generate_exploratory.wilson_interval(5, 10)
        self.assertLess(low, 0.5)
        self.assertGreater(high, 0.5)
        self.assertTrue(math.isnan(generate_exploratory.wilson_interval(0, 0)[0]))

    def test_weighted_rate(self) -> None:
        frame = pd.DataFrame(
            {"sampling_weight_conditional": [1.0, 3.0], "outcome": [0, 1]}
        )
        self.assertEqual(generate_exploratory.weighted_rate(frame, "outcome"), 0.75)

    def test_cluster_bootstrap_is_deterministic_and_bounded(self) -> None:
        frame = pd.DataFrame(
            {
                "selection_stratum": ["a", "a", "b", "b"],
                "repo_full_name": ["r/1", "r/2", "r/3", "r/4"],
                "sampling_weight_conditional": [1.0, 1.0, 2.0, 2.0],
                "outcome": [0, 1, 0, 1],
            }
        )
        first = generate_exploratory.stratified_cluster_bootstrap(
            frame, "outcome", 100, 42
        )
        second = generate_exploratory.stratified_cluster_bootstrap(
            frame, "outcome", 100, 42
        )
        self.assertEqual(first, second)
        self.assertGreaterEqual(first[0], 0.0)
        self.assertLessEqual(first[1], 1.0)


class PropagationCandidateTest(unittest.TestCase):
    def test_patch_signature_normalizes_whitespace_but_preserves_direction(self) -> None:
        added_a, deleted_a = build_patch_signatures.changed_lines(
            "--- a/SKILL.md\n+++ b/SKILL.md\n-old   value\n+new value\n"
        )
        added_b, deleted_b = build_patch_signatures.changed_lines(
            "--- a/SKILL.md\n+++ b/SKILL.md\n-old value\n+new   value\n"
        )
        self.assertEqual(added_a, added_b)
        self.assertEqual(deleted_a, deleted_b)
        forward = build_patch_signatures.patch_signature("modification", added_a, deleted_a)
        reverse = build_patch_signatures.patch_signature("modification", deleted_a, added_a)
        self.assertNotEqual(forward, reverse)

    def test_cross_repository_candidates_require_same_family_and_strict_order(self) -> None:
        frame = pd.DataFrame(
            {
                "signature_eligible": [True, True, True, True],
                "is_post_anchor_divergence": [True, True, True, True],
                "committed_at": [
                    "2026-01-01T00:00:00Z",
                    "2026-01-02T00:00:00Z",
                    "2026-01-02T00:00:00Z",
                    "2026-01-03T00:00:00Z",
                ],
                "anchor_file_sha": ["a", "a", "a", "other"],
                "patch_signature": ["p", "p", "p", "p"],
                "repo_full_name": ["r/1", "r/2", "r/3", "r/4"],
                "diff_id": ["d1", "d2", "d3", "d4"],
                "occurrence_id": ["o1", "o2", "o3", "o4"],
                "commit": ["c1", "c2", "c3", "c4"],
                "old_blob_sha": ["x", "x", "x", "x"],
                "new_blob_sha": ["y", "y", "y", "y"],
                "change_operation": ["modification"] * 4,
            }
        )
        candidates = find_adoptions.build_candidates(frame)
        self.assertEqual(len(candidates), 3)
        self.assertEqual((candidates["temporal_order"] == "strictly_later").sum(), 2)
        accepted, rejected = score_genealogy.score_candidates(candidates)
        self.assertEqual(len(accepted), 2)
        self.assertEqual(len(rejected), 1)
        self.assertTrue(accepted["confidence_level"].eq("B").all())

    def test_no_cross_repository_match_keeps_output_schema(self) -> None:
        frame = pd.DataFrame(
            {
                "signature_eligible": [True],
                "is_post_anchor_divergence": [True],
                "committed_at": ["2026-01-01T00:00:00Z"],
                "anchor_file_sha": ["a"],
                "patch_signature": ["p"],
                "repo_full_name": ["r/1"],
                "diff_id": ["d1"],
                "occurrence_id": ["o1"],
                "commit": ["c1"],
                "old_blob_sha": ["x"],
                "new_blob_sha": ["y"],
                "change_operation": ["modification"],
            }
        )
        candidates = find_adoptions.build_candidates(frame)
        self.assertTrue(candidates.empty)
        self.assertEqual(list(candidates.columns), find_adoptions.CANDIDATE_COLUMNS)


class Rq3AssociationTest(unittest.TestCase):
    def test_model_gate_rejects_small_cluster_count(self) -> None:
        self.assertFalse(analyze_rq3_associations.model_is_supported(75, 40, 10, 8, 18))
        self.assertTrue(analyze_rq3_associations.model_is_supported(100, 20, 10, 20, 30))

    def test_weighted_risk_ratio(self) -> None:
        frame = pd.DataFrame(
            {
                "outcome": [True, False, True, False],
                "exposure": [True, True, False, False],
                "sampling_weight_conditional": [1.0, 1.0, 1.0, 3.0],
            }
        )
        exposed, unexposed, ratio = analyze_rq3_associations.risk_ratio(
            frame, "outcome", "exposure"
        )
        self.assertEqual(exposed, 0.5)
        self.assertEqual(unexposed, 0.25)
        self.assertEqual(ratio, 2.0)

    def test_parent_exposures_exclude_file_additions(self) -> None:
        frame = pd.DataFrame(
            {"parent_blob_present": [True, False], "x_parent_100plus_lines": [False, False]}
        )
        eligible = analyze_rq3_associations.eligible_for_exposure(
            frame, "x_parent_100plus_lines"
        )
        self.assertEqual(len(eligible), 1)
        self.assertEqual(
            len(analyze_rq3_associations.eligible_for_exposure(frame, "x_parent_blob_present")),
            2,
        )


if __name__ == "__main__":
    unittest.main()


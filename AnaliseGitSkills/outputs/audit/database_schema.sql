CREATE TABLE mining_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_type TEXT NOT NULL,
    query TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    discovered INTEGER DEFAULT 0
, note TEXT);
CREATE TABLE sqlite_sequence(name,seq);
CREATE TABLE repos (
    full_name TEXT PRIMARY KEY,
    owner TEXT,
    stars INTEGER,
    forks INTEGER,
    is_fork INTEGER,
    language TEXT,
    license TEXT,
    description TEXT,
    created_at TEXT,
    pushed_at TEXT,
    metadata_fetched INTEGER DEFAULT 0
);
CREATE TABLE artifact_siblings (
    repo_full_name TEXT NOT NULL,
    artifact_path TEXT NOT NULL,
    entry_name TEXT NOT NULL,
    entry_type TEXT,
    entry_size INTEGER,
    entry_sha TEXT,
    content TEXT,
    content_fetched INTEGER DEFAULT 0,
    skipped_reason TEXT,
    PRIMARY KEY (repo_full_name, artifact_path, entry_name)
);
CREATE TABLE IF NOT EXISTS "artifacts" (
            repo_full_name TEXT NOT NULL,
            path TEXT NOT NULL,
            filename TEXT,
            location_class TEXT,
            file_sha TEXT,
            discovered_at TEXT,
            content TEXT,
            content_fetched INTEGER DEFAULT 0,
            frontmatter_valid INTEGER,
            name TEXT,
            description TEXT,
            body_chars INTEGER,
            history_fetched INTEGER DEFAULT 0,
            composition_fetched INTEGER DEFAULT 0,
            dedup_primary INTEGER,
            first_commit_at TEXT,
            last_commit_at TEXT,
            commit_count INTEGER,
            sibling_count INTEGER,
            sibling_bytes INTEGER,
            has_scripts INTEGER,
            has_references INTEGER,
            content_sha_ok INTEGER,
            composition_truncated INTEGER,
            first_commit_author TEXT,
            first_commit_author_type TEXT,
            first_commit_message TEXT,
            last_commit_author TEXT,
            last_commit_author_type TEXT,
            last_commit_message TEXT,
            PRIMARY KEY (repo_full_name, path)
        );
CREATE INDEX idx_repos_meta ON repos(metadata_fetched);
CREATE INDEX idx_artifacts_sha ON artifacts(file_sha);
CREATE INDEX idx_artifacts_repo ON artifacts(repo_full_name);

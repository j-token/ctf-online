CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT    NOT NULL UNIQUE,
    password    TEXT    NOT NULL,
    nickname    TEXT    NOT NULL,
    role        TEXT    NOT NULL DEFAULT 'employee',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS challenges (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    slug        TEXT    NOT NULL UNIQUE,
    title       TEXT    NOT NULL,
    description TEXT    NOT NULL,
    category    TEXT    NOT NULL,
    points      INTEGER NOT NULL DEFAULT 100
);

CREATE TABLE IF NOT EXISTS solved_challenges (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(id),
    challenge_id  INTEGER NOT NULL REFERENCES challenges(id),
    solved_at     TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, challenge_id)
);

CREATE TABLE IF NOT EXISTS directory_profiles (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(id),
    department    TEXT    NOT NULL,
    position      TEXT    NOT NULL,
    email         TEXT    NOT NULL,
    phone         TEXT,
    bio           TEXT,
    private_note  TEXT,
    active        INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS tickets (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         TEXT    NOT NULL,
    description   TEXT    NOT NULL,
    status        TEXT    NOT NULL DEFAULT 'open',
    created_by    INTEGER NOT NULL REFERENCES users(id),
    internal_memo TEXT,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS documents (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    filename      TEXT    NOT NULL,
    display_name  TEXT    NOT NULL,
    category      TEXT    NOT NULL DEFAULT 'general',
    is_public     INTEGER NOT NULL DEFAULT 1,
    uploaded_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS payroll_requests (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id     INTEGER NOT NULL REFERENCES users(id),
    amount          REAL    NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'pending',
    approve_count   INTEGER NOT NULL DEFAULT 0,
    cancel_count    INTEGER NOT NULL DEFAULT 0,
    approved_by     INTEGER REFERENCES users(id),
    approval_chain  TEXT    NOT NULL DEFAULT '[]',
    memo            TEXT,
    snapshot_data   TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS reports (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         TEXT    NOT NULL,
    content       TEXT    NOT NULL,
    submitted_by  INTEGER NOT NULL REFERENCES users(id),
    status        TEXT    NOT NULL DEFAULT 'pending',
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS verification_samples (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    label         TEXT    NOT NULL,
    message       TEXT    NOT NULL,
    nonce         TEXT    NOT NULL,
    signature     TEXT    NOT NULL,
    is_public     INTEGER NOT NULL DEFAULT 1,
    nonce_group   INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS verification_logs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    sample_id     INTEGER REFERENCES verification_samples(id),
    action        TEXT    NOT NULL,
    performed_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

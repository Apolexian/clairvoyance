CREATE TABLE IF NOT EXISTS players (
    viewer_id     INTEGER PRIMARY KEY,
    display_name  TEXT,
    -- borrow card the player has set
    borrow_card_id        INTEGER,
    borrow_card_level     INTEGER,
    borrow_card_limit_break INTEGER,
    -- current trained uma set as profile
    profile_chara_id      INTEGER,
    profile_card_id       INTEGER,
    profile_rank          INTEGER,
    -- meta
    first_seen    INTEGER NOT NULL,  -- unix timestamp
    last_seen     INTEGER NOT NULL,
    raw_json      TEXT               -- full friend_info blob for reprocessing
);

CREATE TABLE IF NOT EXISTS crawl_queue (
    viewer_id  INTEGER PRIMARY KEY,
    state      TEXT NOT NULL DEFAULT 'pending',  -- pending | done | error
    added_at   INTEGER NOT NULL,
    done_at    INTEGER
);

CREATE TABLE IF NOT EXISTS seeds (
    viewer_id  INTEGER PRIMARY KEY,
    source     TEXT NOT NULL,   -- 'recommend' | 'manual' | 'friend_of'
    added_at   INTEGER NOT NULL
);

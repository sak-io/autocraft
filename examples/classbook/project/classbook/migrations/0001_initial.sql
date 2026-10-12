-- 0001: full phase-1 schema (architecture s3). Instants are UTC text 'YYYY-MM-DDTHH:MM:SSZ'.

CREATE TABLE users (
  id            INTEGER PRIMARY KEY,
  email         TEXT NOT NULL UNIQUE CHECK (email = lower(email)),
  name          TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  role          TEXT NOT NULL CHECK (role IN ('student', 'admin')),
  created_at    TEXT NOT NULL,
  last_login_at TEXT,
  prev_login_at TEXT
);
-- at most one admin
CREATE UNIQUE INDEX users_one_admin ON users (role) WHERE role = 'admin';

CREATE TABLE sessions (
  token_hash TEXT PRIMARY KEY,            -- SHA-256 of the cookie token
  user_id    INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL
);
CREATE INDEX sessions_expires ON sessions (expires_at);

CREATE TABLE classes (
  id           INTEGER PRIMARY KEY,
  title        TEXT NOT NULL,
  starts_at    TEXT NOT NULL,
  duration_min INTEGER NOT NULL CHECK (duration_min >= 1),
  instructor   TEXT NOT NULL,
  capacity     INTEGER NOT NULL CHECK (capacity >= 1),
  status       TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'cancelled')),
  created_at   TEXT NOT NULL
);
CREATE INDEX classes_starts ON classes (starts_at);

CREATE TABLE bookings (
  id           INTEGER PRIMARY KEY,
  class_id     INTEGER NOT NULL REFERENCES classes (id),
  user_id      INTEGER NOT NULL REFERENCES users (id),
  status       TEXT NOT NULL DEFAULT 'booked' CHECK (status IN ('booked', 'cancelled')),
  cancelled_by TEXT CHECK (cancelled_by IN ('student', 'studio')),
  created_at   TEXT NOT NULL,
  cancelled_at TEXT,
  -- cancelled_by is set exactly when the booking is cancelled
  CHECK ((status = 'booked') = (cancelled_by IS NULL))
);
-- one active booking per student per class; rebooking after a cancel inserts a new row
CREATE UNIQUE INDEX bookings_one_active ON bookings (class_id, user_id) WHERE status = 'booked';
CREATE INDEX bookings_class_status ON bookings (class_id, status);
CREATE INDEX bookings_user_status ON bookings (user_id, status);

CREATE TABLE messages (
  id         INTEGER PRIMARY KEY,
  to_email   TEXT NOT NULL,
  subject    TEXT NOT NULL,
  body       TEXT NOT NULL,
  kind       TEXT NOT NULL,
  booking_id INTEGER REFERENCES bookings (id),
  status     TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'recorded', 'failed')),
  created_at TEXT NOT NULL,
  UNIQUE (booking_id, kind)
);

CREATE TABLE login_failures (
  key TEXT NOT NULL,                       -- e.g. 'email:x@y.z' or 'ip:1.2.3.4'
  at  TEXT NOT NULL
);
CREATE INDEX login_failures_key_at ON login_failures (key, at);

-- F24: one row per book/cancel attempt (refusals count); the 20/hour/user cap counts these
CREATE TABLE user_actions (
  id      INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  at      TEXT NOT NULL
);
CREATE INDEX user_actions_user_at ON user_actions (user_id, at);

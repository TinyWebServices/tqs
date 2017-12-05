-- This Source Code Form is subject to the terms of the Mozilla Public
-- License, v. 2.0. If a copy of the MPL was not distributed with this
-- file, You can obtain one at http://mozilla.org/MPL/2.0/.


PRAGMA foreign_keys = ON;


CREATE TABLE IF NOT EXISTS queues (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  create_date REAL NOT NULL,
  name TEXT NOT NULL UNIQUE,
  insert_count integer default 0,
  delete_count integer default 0,
  expire_count integer default 0
);

CREATE UNIQUE INDEX IF NOT EXISTS queues_id ON queues (id);
CREATE UNIQUE INDEX IF NOT EXISTS queues_name ON queues (name);


CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  create_date REAL NOT NULL,
  visible_date REAL NOT NULL,
  expire_date REAL NOT NULL,
  body TEXT not null,
  lease_date REAL,
  lease_uuid TEXT UNIQUE,
  lease_timeout INTEGER,
  queue_id INTEGER REFERENCES queues (id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS messages_id ON messages (id);
CREATE INDEX IF NOT EXISTS messages_queue_id ON messages (queue_id);
CREATE INDEX IF NOT EXISTS messages_create_date ON messages (create_date);
CREATE INDEX IF NOT EXISTS messages_lease_date ON messages (lease_date);
CREATE UNIQUE INDEX IF NOT EXISTS messages_lease_uuid ON messages (lease_uuid);
CREATE INDEX IF NOT EXISTS messages_queue_id_lease_date_create_date ON messages (queue_id, lease_date, create_date);

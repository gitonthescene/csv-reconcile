DROP TABLE IF EXISTS reconcile;

CREATE TABLE reconcile (
  id TEXT PRIMARY KEY,
  word TEXT NOT NULL,
  bigrams TEXT NOT NULL
);

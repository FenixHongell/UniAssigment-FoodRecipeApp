CREATE TABLE visits (
  id INTEGER PRIMARY KEY,
  last_visit TEXT
);

CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  username TEXT,
  password TEXT
);

CREATE TABLE recipes (
    id INTEGER PRIMARY KEY,
    name TEXT,
    ingredients TEXT,
    directions TEXT,
    user_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id)
)
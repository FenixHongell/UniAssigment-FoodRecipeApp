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
);

CREATE TABLE comments (
    id INTEGER PRIMARY KEY,
    content TEXT,
    recipe_id INTEGER,
    user_id INTEGER,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE ratings (
    id INTEGER PRIMARY KEY,
    rating INTEGER,
    recipe_id INTEGER,
    user_id INTEGER,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE recipe_images (
    recipe_id INTEGER PRIMARY KEY,
    image BLOB NOT NULL,
    mime_type TEXT,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);

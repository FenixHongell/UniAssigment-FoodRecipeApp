CREATE TABLE visits (
  id INTEGER PRIMARY KEY,
  last_visit TEXT
);

CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  username TEXT,
  password TEXT
);

CREATE TABLE IF NOT EXISTS categories (
  id   INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE recipes (
    id INTEGER PRIMARY KEY,
    name TEXT,
    ingredients TEXT,
    directions TEXT,
    user_id INTEGER,
    category_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
);

CREATE TABLE comments (
    id INTEGER PRIMARY KEY,
    content TEXT,
    recipe_id INTEGER,
    user_id INTEGER,
    created_at INTEGER NOT NULL DEFAULT (unixepoch()),
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE ratings (
    id INTEGER PRIMARY KEY,
    rating INTEGER,
    recipe_id INTEGER,
    user_id INTEGER,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE recipe_images (
    recipe_id INTEGER PRIMARY KEY,
    image BLOB NOT NULL,
    mime_type TEXT,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);

-- Speed up filtering and joining recipes by category (used on /recipes with category filter)
CREATE INDEX IF NOT EXISTS idx_recipes_category ON recipes(category_id);

-- Speed up fetching a user's recipes (used on /account and for authorization checks)
CREATE INDEX IF NOT EXISTS idx_recipes_user ON recipes(user_id);

-- Speed up average/rating lookups and updates per recipe, and uniqueness checks by (recipe_id, user_id)
CREATE INDEX IF NOT EXISTS idx_ratings_recipe ON ratings(recipe_id);
CREATE INDEX IF NOT EXISTS idx_ratings_recipe_user ON ratings(recipe_id, user_id);

-- Speed up listing and deleting comments per recipe
CREATE INDEX IF NOT EXISTS idx_comments_recipe ON comments(recipe_id);

INSERT OR IGNORE INTO categories (name) VALUES
('Breakfast'),
('Lunch'),
('Dinner'),
('Dessert'),
('Snack'),
('Drink'),
('Vegan'),
('Vegetarian'),
('Gluten-Free'),
('Keto'),
('Paleo'),
('Uncategorized');

UPDATE recipes
SET category_id = (SELECT id FROM categories WHERE name = 'Uncategorized' LIMIT 1)
WHERE category_id IS NULL;

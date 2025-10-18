BEGIN;

-- Clean out demo-related data so seeding is repeatable
DELETE FROM ratings;
DELETE FROM comments;
DELETE FROM recipe_images;
DELETE FROM recipes;
DELETE FROM users;

-- Users (passwords are SHA-256 hex of: password, password123, hunter2)
INSERT INTO users (id, username, password) VALUES
  (1, 'ChefNebula',   '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8'),
  (2, 'NoodleNinja',  'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f'),
  (3, 'BiscuitBandit','f52fbd32b2b3b86ff88ef6c490628285f482af15ddcb29541f94bcf526a3f6c7');

-- Recipes (1–2 per user)
INSERT INTO recipes (id, name, ingredients, directions, user_id) VALUES
  (1, 'Supernova Salsa',
   'Tomatoes; red onion; jalapeño; lime; cilantro; salt; pepper.',
   'Dice everything, toss with lime and salt, rest 10 minutes, serve with chips.',
   1),
  (2, 'Cosmic Cinnamon Rolls',
   'Flour; yeast; milk; sugar; butter; cinnamon; salt; vanilla.',
   'Mix dough, first rise, roll with filling, slice, second rise, bake until golden.',
   1),
  (3, 'Lightning Noodle Stir-Fry',
   'Rice noodles; tofu; bell pepper; scallions; soy; lime; chili; garlic.',
   'Soak noodles, sear tofu, stir-fry veg, add sauce, toss noodles, finish with lime.',
   2),
  (4, 'Midnight Ramen Broth',
   'Chicken stock; miso; soy; ginger; garlic; bonito; sesame oil.',
   'Simmer aromatics, whisk in miso, season to taste, ladle over cooked ramen.',
   2),
  (5, 'Bandit’s Buttermilk Biscuits',
   'Flour; baking powder; baking soda; salt; cold butter; buttermilk.',
   'Cut butter into flour, add buttermilk, fold dough, cut rounds, bake until tall and golden.',
   3);

-- Ratings (no self-ratings; not every recipe is rated by everyone)
INSERT INTO ratings (rating, recipe_id, user_id) VALUES
  (5, 1, 2), -- NoodleNinja -> ChefNebula's Supernova Salsa
  (4, 1, 3), -- BiscuitBandit -> Supernova Salsa
  (4, 2, 2), -- NoodleNinja -> Cosmic Cinnamon Rolls
  (5, 3, 1), -- ChefNebula -> Lightning Noodle Stir-Fry
  (3, 4, 1), -- ChefNebula -> Midnight Ramen Broth
  (5, 5, 1), -- ChefNebula -> Bandit’s Buttermilk Biscuits
  (4, 3, 3); -- BiscuitBandit -> Lightning Noodle Stir-Fry

-- Comments (a sampling across recipes)
INSERT INTO comments (content, recipe_id, user_id) VALUES
  ('That salsa is a flavor supernova. Added mango—boom!', 1, 2),
  ('Perfect heat level. My roommates devoured it.',      1, 3),
  ('These rolls are dangerously soft. Frosting was ace!', 2, 2),
  ('Stir-fry lived up to the name—done in ten!',          3, 1),
  ('Broth is cozy. I added corn and chili oil.',          4, 3),
  ('Flaky layers for days. New brunch staple.',           5, 2);

COMMIT;

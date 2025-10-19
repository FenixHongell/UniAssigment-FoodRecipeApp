# RECIPE APP
This is a recipe app made using Flask, Pylint, Python & SQLite for University.

## Features

- Create Account ✅
- Login ✅
- Create Recipe ✅
- View Recipe ✅
- Delete Recipe ✅
- Comment on recipies ✅
- Add images to recipies ✅
- Search recipies ✅
- Show users recipies ✅
- Add/Show recipe ratings ✅
- Show top recipes ✅
- Recipe categories ✅

## Requirements
- Python 3.13+
- SQLite3
- Virtualenv
- Packages: `Flask`, `Pylint` (development)

## Setup
1. Clone the repository `git clone https://github.com/FenixHongell/UniAssigment-FoodRecipeApp`

2. Install dependencies
   - `pip install --upgrade pip`
   - `pip install flask pylint`

3. Initialize the database
   - `sqlite3 database.db < schema.sql`
   - `sqlite3 database.db < init.sql`

4. Optional:
    - Add some data by using the following command:
      - `sqlite3 database.db < mock-data.sql`

## Running the app
- Start the server
   - `flask run`
-  App will be available at http://127.0.0.1:5000


## Linting
- Run Pylint on the project:
  - Single file: `pylint app.py`
  - Entire project: `pylint .`

## Notes
- To reset the database, delete the `database.db` file and setup step 3 again.
- A report on the code quality and performance can be found in [report.md](report.md).

## Troubleshooting
- Flask not found: Ensure your virtual environment is activated and `pip install flask` has been run.
- Database errors: Verify `database.db` exists and matches `schema.sql`.

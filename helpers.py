import hashlib
import sqlite3

def create_connection():
    db = sqlite3.connect("./database.db")
    db.execute("PRAGMA foreign_keys = ON")
    return db

def close_connection(db):
    db.close()

def execute_cmd(cmd, params=None):
    """
    Executes a given SQL command with optional parameters, commits the transaction,
    and returns the result. It ensures the database connection is properly managed
    by opening and closing it securely within the execution cycle.

    :param cmd: The SQL command to be executed.
    :type cmd: str
    :param params: Optional parameterized values to include in the SQL command.
                   Defaults to an empty list if no parameters are provided.
    :type params: list, optional
    :return: The result of the executed SQL command.
    :rtype: Any
    """
    if params is None:
        params = []
    db = create_connection()
    result = db.execute(cmd, params)
    db.commit()
    close_connection(db)
    return result

def run_query(cmd, params=None, no_factory=False):
    """
    Executes a SQL query against the database and returns the result. Establishes a
    connection to the database, optionally disables the row factory, executes the
    query with given parameters, and fetches all results before closing the
    connection.

    :param cmd: The SQL command/query to execute.
    :type cmd: str
    :param params: Optional list of parameters to bind to the SQL query.
    :type params: list, optional
    :param no_factory: Flag to disable row factory for database connection. Defaults
        to False.
    :type no_factory: bool, optional
    :return: The result set of the executed query.
    :rtype: list
    """
    if params is None:
        params = []
    db = create_connection()
    if no_factory:
        db.row_factory = None
    result = db.execute(cmd, params).fetchall()
    close_connection(db)
    return result

def get_avg_rating(recipe_id):
    """
    Calculates the average rating for a given recipe based on ratings stored in the database.

    This function queries the database for ratings associated with a specific recipe ID,
    calculates their average, and returns the rounded result. If there are no ratings for
    the given recipe, it defaults to 0.

    :param recipe_id: The unique identifier of the recipe for which the average rating is
        being calculated.
    :type recipe_id: int
    :return: A tuple containing the rounded average rating and rating count.
    :rtype: tuple
    """
    result = run_query("SELECT AVG(rating), COUNT(*) FROM ratings WHERE recipe_id = ?", [recipe_id])
    if len(result) == 0:
        return 0
    return round(result[0][0], 1) if result and result[0][0] is not None else 0, result[0][1] if result and result[0][1] is not None else 0

def validate_credentials(username, password):
    """
    Validates user credentials against a database. The function hashes the provided
    password using SHA-256, then compares the resulting hash and username with
    entries in the database. If a matching user is found, their details are returned;
    otherwise, None is returned.

    :param username: The username of the user attempting to log in.
    :type username: str
    :param password: The plaintext password provided by the user.
    :type password: str
    :return: The matching user's information from the database if credentials are valid,
        otherwise None.
    :rtype: dict or None
    """
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    result = run_query("SELECT * FROM users WHERE username = ? AND password = ?", [username, hashed_password])
    return None if len(result) == 0 else result[0]


def validate_input_recipe(name, ingredients, directions, min_recipe_name_len, max_recipe_name_len, min_ingredients_len,
                          max_ingredients_len, min_directions_len, max_directions_len):
    has_issue = False
    error_message = ""

    if not name or len(name.strip()) < min_recipe_name_len:
        has_issue = True
        error_message = f"Recipe name is required to be over {min_recipe_name_len} characters"

    if not ingredients or len(ingredients.strip()) < min_ingredients_len:
        has_issue = True
        error_message = f"Ingredients are required to be over {min_ingredients_len} characters"

    if not directions or len(directions.strip()) < min_directions_len:
        has_issue = True
        error_message = f"Directions are required to be over {min_directions_len} characters"

    if len(name) > max_recipe_name_len:
        has_issue = True
        error_message = f"Recipe name must be at most {max_recipe_name_len} characters"

    if len(ingredients) > max_ingredients_len:
        has_issue = True
        error_message = f"Ingredients must be at most {max_ingredients_len} characters"

    if len(directions) > max_directions_len:
        has_issue = True
        error_message = f"Directions must be at most {max_directions_len} characters"

    return has_issue, error_message

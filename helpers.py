import sqlite3

def create_connection():
    db = sqlite3.connect("./database.db")
    return db

def close_connection(db):
    db.close()

def execute_cmd(cmd, params=None):
    if params is None:
        params = []
    db = create_connection()
    result = db.execute(cmd, params)
    db.commit()
    close_connection(db)
    return result

def run_query(cmd, params=None, no_factory=False):
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
    return round(result[0][0]) if result and result[0][0] is not None else 0, result[0][1] if result and result[0][1] is not None else 0

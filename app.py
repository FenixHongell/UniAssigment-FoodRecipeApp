import hashlib
import secrets
from flask import Flask, render_template, request, redirect, session, abort
from helpers import execute_cmd, run_query, get_avg_rating, validate_credentials

app = Flask(__name__)

# This is terrible practice, but this is a simple UNI project and I dont want to start using ENV variables. Might change later.
app.config['SECRET_KEY'] = '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918'

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=False,
    PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 7
)

#Helper functions for authentication
def require_login():
    if "user_id" not in session:
        print("redirecting to login")
        abort(403)

def check_csrf():
    if "csrf_token" not in request.form:
        print("csrf token missing")
        abort(403)
    if request.form["csrf_token"] != session["csrf_token"]:
        print("csrf token mismatch")
        abort(403)

def add_visits():
    execute_cmd("INSERT INTO visits (last_visit) VALUES (datetime('now'))")
@app.route("/")
def index():
    add_visits()

    top_recipes = run_query(
        """
        SELECT r.id,
               r.name,
               r.ingredients,
               r.directions,
               ROUND(AVG(rt.rating), 1) AS avg_rating,
               COUNT(rt.id) AS ratings_count
        FROM recipes r
        LEFT JOIN ratings rt ON rt.recipe_id = r.id
        GROUP BY r.id, r.name, r.ingredients, r.directions
        ORDER BY COALESCE(AVG(rt.rating), 0) DESC, COUNT(rt.id) DESC, r.id DESC
        LIMIT 3
        """
    )


    return render_template("index.html", top_recipes=top_recipes)

@app.route("/create_account", methods=["GET", "POST"])
def create_account():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        existing_user = run_query("SELECT * FROM users WHERE username = ?", [username])

        if len(existing_user) > 0:
            return render_template("createAccount.html", error="Username already exists")

        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        execute_cmd("INSERT INTO users (username, password) VALUES (?, ?)", [username, hashed_password])

        return redirect("/login")

    return render_template("createAccount.html")

@app.route("/login", methods=["GET", "POST"])
def signin():
    if "user_id" in session:
        return redirect("/")

    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')

        user = validate_credentials(username, password)

        if not user:
            return render_template("login.html", error="Invalid username or password")

        session["user_id"] = user[0]
        session["username"] = user[1]
        session["csrf_token"] = secrets.token_hex(16)

        return redirect("/")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/create_recipe", methods=["GET", "POST"])
def create_recipe():
    require_login()

    if request.method == "POST":
        check_csrf()
        name = request.form.get('name')
        ingredients = request.form.get('ingredients')
        directions = request.form.get('directions')

        if not name or name.strip() == "":
            return render_template("createRecipe.html", error="Recipe name is required")
        if not ingredients or ingredients.strip() == "":
            return render_template("createRecipe.html", error="Ingredients are required")
        if not directions or directions.strip() == "":
            return render_template("createRecipe.html", error="Directions are required")

        execute_cmd("INSERT INTO recipes (name, ingredients, directions, user_id) VALUES (?, ?, ?, ?)",
                    [name, ingredients, directions, session["user_id"]])

        return redirect("/")


    return render_template("createRecipe.html")

@app.route("/recipes")
def recipes():
    require_login()
    q = request.args.get("q", "", type=str)
    # Search functionality
    if q:
        pattern = f"%{q}%"
        rec = run_query("SELECT * FROM recipes WHERE name LIKE ? OR ingredients LIKE ? OR directions LIKE ? ORDER BY id DESC",
                            [pattern, pattern, pattern])
    else:
        rec = run_query("SELECT * FROM recipes ORDER BY id DESC")

    ratings = {r[0]: get_avg_rating(r[0]) for r in rec}

    return render_template("recipes.html", recipes=rec, q=q, ratings=ratings)

@app.route("/recipes/delete", methods=["POST"])
def delete_recipe():
    require_login()
    check_csrf()
    recipe_id = request.form.get("recipe_id", type=int)
    if not recipe_id:
        abort(400)
    user_id = session["user_id"]

    execute_cmd("DELETE FROM recipes WHERE id = ? AND user_id = ?", [recipe_id, user_id])

    return redirect("/account")


@app.route("/account", methods=["GET"])
def account():
    require_login()
    user_id = session["user_id"]
    username = session.get("username", "User")
    my_recipes = run_query("SELECT id, name FROM recipes WHERE user_id = ? ORDER BY name", [user_id])

    return render_template("account.html", username=username, recipes=my_recipes)


@app.route("/recipes/<int:recipe_id>/edit", methods=["GET", "POST"])
def edit_recipe(recipe_id: int):
    require_login()
    user_id = session["user_id"]

    if request.method == "POST":
        check_csrf()
        name = request.form.get("name", "").strip()
        ingredients = request.form.get("ingredients", "").strip()
        directions = request.form.get("directions", "").strip()

        if not name:
            return render_template("editRecipe.html", error="Recipe name is required",
                                   recipe=(recipe_id, name, ingredients, directions))
        if not ingredients:
            return render_template("editRecipe.html", error="Ingredients are required",
                                   recipe=(recipe_id, name, ingredients, directions))
        if not directions:
            return render_template("editRecipe.html", error="Directions are required",
                                   recipe=(recipe_id, name, ingredients, directions))

        cur = execute_cmd("UPDATE recipes SET name = ?, ingredients = ?, directions = ? WHERE id = ? AND user_id = ?",
                          [name, ingredients, directions, recipe_id, user_id])
        if cur.rowcount == 0:
            abort(404)

        return redirect("/account")

    result = run_query("SELECT id, name, ingredients, directions FROM recipes WHERE id = ? AND user_id = ?", [recipe_id, user_id])

    if len(result) == 0:
        abort(404)

    return render_template("editRecipe.html", recipe=result[0])

@app.route("/rate", methods=["POST"])
def rate():
    require_login()
    check_csrf()

    recipe_id = request.form.get("recipe_id", type=int)
    rating = request.form.get("rating", type=int)

    if not recipe_id or rating is None:
        abort(400)

    if rating < 1 or rating > 5:
        abort(400)

    user_id = session["user_id"]

    existing = run_query(
        "SELECT id FROM ratings WHERE recipe_id = ? AND user_id = ? LIMIT 1",
        [recipe_id, user_id]
    )
    if existing:
        execute_cmd(
            "UPDATE ratings SET rating = ? WHERE recipe_id = ? AND user_id = ?",
            [rating, recipe_id, user_id]
        )
    else:
        execute_cmd(
            "INSERT INTO ratings (rating, recipe_id, user_id) VALUES (?, ?, ?)",
            [rating, recipe_id, user_id]
        )

    return redirect(f"/recipes/{recipe_id}")


@app.route("/recipes/<int:recipe_id>", methods=["GET"])
def recipe(recipe_id: int):
    require_login()
    result = run_query("SELECT id, name, ingredients, directions FROM recipes WHERE id = ?", [recipe_id])
    if len(result) == 0:
        abort(404)

    rating = get_avg_rating(recipe_id)

    user_rating_row  = run_query("SELECT rating FROM ratings WHERE recipe_id = ? AND user_id = ? LIMIT 1", [recipe_id, session["user_id"]])
    user_rating = user_rating_row[0][0] if user_rating_row else None
    return render_template("recipe.html", recipe=result[0], avg_rating=rating[0], ratings_count=rating[1], user_rating=user_rating)

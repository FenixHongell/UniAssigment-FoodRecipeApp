import hashlib
import secrets
from flask import Flask, render_template, request, redirect, session, abort, make_response

from formatting import format_timestamp
from helpers import execute_cmd, run_query, get_avg_rating, validate_credentials

app = Flask(__name__)

# The things we do to not use javascript on the frontend smh, anyway this registers the function for use in templates
app.jinja_env.globals["format_timestamp"] = format_timestamp

# This is terrible practice, but this is a simple UNI project and I dont want to start using ENV variables. Might change later.
app.config['SECRET_KEY'] = '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918'

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=False,
    PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 7
)


# Helper functions for authentication
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
               COUNT(rt.id)             AS ratings_count
        FROM recipes r
                 LEFT JOIN ratings rt ON rt.recipe_id = r.id
        GROUP BY r.id, r.name, r.ingredients, r.directions
        ORDER BY COALESCE(AVG(rt.rating), 0) DESC, COUNT(rt.id) DESC, r.id DESC LIMIT 3
        """
    )

    return render_template("index.html", top_recipes=top_recipes)


@app.route("/create_account", methods=["GET", "POST"])
def create_account():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            return render_template("createAccount.html", error="Username and password are required")
        elif len(username) < 4:
            return render_template("createAccount.html", error="Username must be at least 4 characters long")
        elif len(password) < 8:
            return render_template("createAccount.html", error="Password must be at least 8 characters long")

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

        # Save image if exists
        file = request.files.get('cover')
        image_bytes = None
        mime_type = None
        if file and file.filename:
            data = file.read()
            if len(data) > 5 * 1024 * 1024:
                return render_template("createRecipe.html", error="Image too large (max 5MB)")
            header = data[:12]
            if header.startswith(b"\xff\xd8\xff"):
                mime_type = "image/jpeg"
            elif header.startswith(b"\x89PNG\r\n\x1a\n"):
                mime_type = "image/png"
            elif header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
                mime_type = "image/gif"
            elif header[:4] == b"RIFF" and header[8:12] == b"WEBP":
                mime_type = "image/webp"
            else:
                return render_template("createRecipe.html",
                                       error="Unsupported image format. Use JPG, PNG, GIF, or WebP.")
            image_bytes = data

        if not name or len(name.strip()) < 4:
            return render_template("createRecipe.html", error="Recipe name is required to be over 4 characters")
        if not ingredients or len(ingredients.strip()) < 10:
            return render_template("createRecipe.html", error="Ingredients are required to be over 10 characters")
        if not directions or len(directions.strip()) < 10:
            return render_template("createRecipe.html", error="Directions are required to be over 10 characters")

        cur = execute_cmd("INSERT INTO recipes (name, ingredients, directions, user_id) VALUES (?, ?, ?, ?)",
                          [name, ingredients, directions, session["user_id"]])
        recipe_id = cur.lastrowid

        if image_bytes is not None:
            execute_cmd("INSERT OR REPLACE INTO recipe_images (recipe_id, image, mime_type) VALUES (?, ?, ?)",
                        [recipe_id, image_bytes, mime_type])

        return redirect("/")

    return render_template("createRecipe.html")


@app.route("/recipes")
def recipes():
    require_login()
    q = request.args.get("q", "", type=str)
    # Search functionality
    if q:
        pattern = f"%{q}%"
        rec = run_query(
            "SELECT * FROM recipes WHERE name LIKE ? OR ingredients LIKE ? OR directions LIKE ? ORDER BY id DESC",
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

    recipes_count = len(my_recipes)

    avg_rating_row = run_query("""
                               SELECT AVG(rt.rating)
                               FROM ratings rt
                                        JOIN recipes r ON rt.recipe_id = r.id
                               WHERE r.user_id = ?
                               """, [user_id])
    avg_rating = avg_rating_row[0][0] if avg_rating_row and avg_rating_row[0][0] is not None else 0

    comments_count_row = run_query("""
                                   SELECT COUNT(*)
                                   FROM comments c
                                            JOIN recipes r ON c.recipe_id = r.id
                                   WHERE r.user_id = ?
                                   """, [user_id])
    comments_count = comments_count_row[0][0] if comments_count_row else 0

    return render_template("account.html", username=username, recipes=my_recipes,
                           recipes_count=recipes_count, avg_rating=avg_rating, comments_count=comments_count)


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

    result = run_query("SELECT id, name, ingredients, directions FROM recipes WHERE id = ? AND user_id = ?",
                       [recipe_id, user_id])

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

    # Validation so that you can't rate your own recipes
    author_check = run_query("SELECT user_id FROM recipes WHERE id = ? LIMIT 1", [recipe_id])
    if author_check and author_check[0] and author_check[0][0] == session["user_id"]:
        abort(403)

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
    result = run_query(
        """
        SELECT r.id,
               r.name,
               r.ingredients,
               r.directions,
               r.user_id                                                      AS author_id,
               u.username                                                     AS author_name,
               EXISTS(SELECT 1 FROM recipe_images i WHERE i.recipe_id = r.id) AS has_image
        FROM recipes r
                 JOIN users u ON u.id = r.user_id
        WHERE r.id = ?
        """,
        [recipe_id]
    )
    if len(result) == 0:
        abort(404)

    rating = get_avg_rating(recipe_id)

    user_rating_row = run_query("SELECT rating FROM ratings WHERE recipe_id = ? AND user_id = ? LIMIT 1",
                                [recipe_id, session["user_id"]])
    user_rating = user_rating_row[0][0] if user_rating_row else None

    comments = run_query(
        """
        SELECT c.id, c.content, u.username, c.user_id, c.created_at
        FROM comments c
                 JOIN users u ON u.id = c.user_id
        WHERE c.recipe_id = ?
        ORDER BY c.id DESC
        """,
        [recipe_id]
    )

    recipe_tuple = result[0]
    author_id = recipe_tuple[4]
    author_name = recipe_tuple[5]
    return render_template("recipe.html",
                           recipe=recipe_tuple,
                           avg_rating=rating[0],
                           ratings_count=rating[1],
                           user_rating=user_rating,
                           comments=comments,
                           author_id=author_id,
                           author_name=author_name)


@app.route("/comment", methods=["POST"])
def add_comment():
    require_login()
    check_csrf()

    recipe_id = request.form.get("recipe_id", type=int)
    comment = request.form.get("content", "").strip()
    if not comment or not recipe_id:
        abort(400)

    if len(comment) > 1000 or len(comment.strip()) == 0:
        abort(400)

    execute_cmd(
        "INSERT INTO comments (content, recipe_id, user_id) VALUES (?, ?, ?)",
        [comment, recipe_id, session["user_id"]])

    return redirect(f"/recipes/{recipe_id}")


@app.route("/comment/delete", methods=["POST"])
def delete_comment():
    require_login()
    check_csrf()
    recipe_id = request.form.get("recipe_id", type=int)
    comment_id = request.form.get("comment_id", type=int)
    if not recipe_id or not comment_id:
        abort(400)
    user_id = session["user_id"]

    execute_cmd("DELETE FROM comments WHERE id = ? AND recipe_id = ? AND user_id = ?", [comment_id, recipe_id, user_id])

    return redirect(f"/recipes/{recipe_id}")


@app.route("/recipes/<int:recipe_id>/cover", methods=["GET"])
def recipe_cover(recipe_id: int):
    require_login()
    row = run_query("SELECT image, mime_type FROM recipe_images WHERE recipe_id = ? LIMIT 1", [recipe_id])
    if not row:
        abort(404)
    data: bytes = row[0][0]
    ctype = row[0][1] or "application/octet-stream"

    # Fallback if mime_type missing
    if ctype == "application/octet-stream":
        if data.startswith(b"\xff\xd8\xff"):
            ctype = "image/jpeg"
        elif data.startswith(b"\x89PNG\r\n\x1a\n"):
            ctype = "image/png"
        elif data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
            ctype = "image/gif"
        elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            ctype = "image/webp"

    resp = make_response(data)
    resp.headers["Content-Type"] = ctype
    resp.headers["Cache-Control"] = "public, max-age=86400"
    return resp

import hashlib
import secrets
from flask import Flask, render_template, request, redirect, session, abort, make_response

from formatting import format_timestamp
from helpers import execute_cmd, run_query, get_avg_rating, validate_credentials, validate_input_recipe

app = Flask(__name__)

app.jinja_env.globals["format_timestamp"] = format_timestamp
app.config['SECRET_KEY'] = '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918'

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=False,
    PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 7
)

MIN_USERNAME_LEN = 4
MAX_USERNAME_LEN = 32
MIN_PASSWORD_LEN = 8
MAX_PASSWORD_LEN = 128
MIN_COMMENT_LEN = 1
MAX_COMMENT_LEN = 1000
MIN_RECIPE_NAME_LEN = 4
MAX_RECIPE_NAME_LEN = 100
MIN_INGREDIENTS_LEN = 10
MAX_INGREDIENTS_LEN = 5000
MIN_DIRECTIONS_LEN = 10
MAX_DIRECTIONS_LEN = 10000


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
        if len(username) < MIN_USERNAME_LEN:
            return render_template("createAccount.html",
                                   error=f"Username must be at least {MIN_USERNAME_LEN} characters long")
        if len(password) < MIN_PASSWORD_LEN:
            return render_template("createAccount.html",
                                   error=f"Password must be at least {MIN_PASSWORD_LEN} characters long")
        if len(username) > MAX_USERNAME_LEN:
            return render_template("createAccount.html",
                                   error=f"Username must be at most {MAX_USERNAME_LEN} characters long")
        if len(password) > MAX_PASSWORD_LEN:
            return render_template("createAccount.html",
                                   error=f"Password must be at most {MAX_PASSWORD_LEN} characters long")

        existing_user = run_query("SELECT id, username, password FROM users WHERE username = ?", [username])

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

        try:
            category_id = int(request.form.get('category_id') or 0)
        except (TypeError, ValueError):
            category_id = 0
        cat_exists = run_query("SELECT id FROM categories WHERE id = ? LIMIT 1", [category_id])
        if not cat_exists:
            return render_template("createRecipe.html",
                                   error="Invalid category selected",
                                   categories=run_query("SELECT id, name FROM categories ORDER BY name"),
                                   selected_category_id=None)

        file = request.files.get('cover')
        image_bytes = None
        mime_type = None
        if file and file.filename:
            data = file.read()
            if len(data) > 5 * 1024 * 1024:
                return render_template("createRecipe.html", error="Image too large (max 5MB)",
                                       categories=run_query("SELECT id, name FROM categories ORDER BY name"),
                                       selected_category_id=category_id)
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
                                       error="Unsupported image format. Use JPG, PNG, GIF, or WebP.",
                                       categories=run_query("SELECT id, name FROM categories ORDER BY name"),
                                       selected_category_id=category_id)
            image_bytes = data

        has_issue, error_message = validate_input_recipe(name, ingredients, directions, MIN_RECIPE_NAME_LEN,
                                                         MAX_RECIPE_NAME_LEN, MIN_INGREDIENTS_LEN, MAX_INGREDIENTS_LEN,
                                                         MIN_DIRECTIONS_LEN, MAX_DIRECTIONS_LEN)

        if has_issue:
            return render_template("createRecipe.html",
                                   error=error_message,
                                   categories=run_query("SELECT id, name FROM categories ORDER BY name"),
                                   selected_category_id=category_id)

        cur = execute_cmd(
            "INSERT INTO recipes (name, ingredients, directions, user_id, category_id) VALUES (?, ?, ?, ?, ?)",
            [name, ingredients, directions, session["user_id"], category_id]
        )
        recipe_id = cur.lastrowid

        if image_bytes is not None:
            execute_cmd("INSERT OR REPLACE INTO recipe_images (recipe_id, image, mime_type) VALUES (?, ?, ?)",
                        [recipe_id, image_bytes, mime_type])

        return redirect("/")

    cats = run_query("SELECT id, name FROM categories ORDER BY name")
    return render_template("createRecipe.html", categories=cats, selected_category_id=None)


@app.route("/recipes")
def recipes():
    require_login()
    q = request.args.get("q", "", type=str)
    cat_id = request.args.get("cat", "", type=str)
    page = request.args.get("page", 1, type=int) or 1
    per_page = 10

    params = []
    where_clauses = []
    if q:
        pattern = f"%{q}%"
        where_clauses.append("(r.name LIKE ? OR r.ingredients LIKE ? OR r.directions LIKE ?)")
        params.extend([pattern, pattern, pattern])
    if cat_id and cat_id.isdigit():
        where_clauses.append("r.category_id = ?")
        params.append(int(cat_id))

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    # Count total results for pagination
    total_row = run_query(
        f"""
        SELECT COUNT(*)
        FROM recipes r
        JOIN categories c ON c.id = r.category_id
        {where_sql}
        """,
        params
    )
    total_count = total_row[0][0] if total_row else 0
    total_pages = max(1, (total_count + per_page - 1) // per_page)

    page = max(page, 1)
    page = min(page, total_pages)

    offset = (page - 1) * per_page

    rec = run_query(
        f"""
        SELECT r.id, r.name, r.ingredients, r.directions, r.user_id, r.category_id, c.name AS category_name
        FROM recipes r
        JOIN categories c ON c.id = r.category_id
        {where_sql}
        ORDER BY r.id DESC
        LIMIT ? OFFSET ?
        """,
        params + [per_page, offset]
    )

    ratings = {r[0]: get_avg_rating(r[0]) for r in rec}
    cats = run_query("SELECT id, name FROM categories ORDER BY name")

    start_idx = (page - 1) * per_page + 1 if total_count > 0 else 0
    end_idx = min(page * per_page, total_count)

    return render_template(
        "recipes.html",
        recipes=rec,
        q=q,
        ratings=ratings,
        categories=cats,
        selected_cat_id=(int(cat_id) if str(cat_id).isdigit() else None),
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        total_count=total_count,
        start_idx=start_idx,
        end_idx=end_idx,
    )


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
        try:
            category_id = int(request.form.get('category_id') or 0)
        except (TypeError, ValueError):
            category_id = 0

        has_issue, error_message = validate_input_recipe(name, ingredients, directions, MIN_RECIPE_NAME_LEN,
                                                         MAX_RECIPE_NAME_LEN, MIN_INGREDIENTS_LEN, MAX_INGREDIENTS_LEN,
                                                         MIN_DIRECTIONS_LEN, MAX_DIRECTIONS_LEN)

        if has_issue:
            return render_template("editRecipe.html",
                                   error=error_message,
                                   recipe=(recipe_id, name, ingredients, directions, category_id),
                                   categories=run_query("SELECT id, name FROM categories ORDER BY name"),
                                   selected_category_id=category_id)

        cat_exists = run_query("SELECT id FROM categories WHERE id = ? LIMIT 1", [category_id])
        if not cat_exists:
            return render_template("editRecipe.html", error="Invalid category selected",
                                   recipe=(recipe_id, name, ingredients, directions, category_id),
                                   categories=run_query("SELECT id, name FROM categories ORDER BY name"),
                                   selected_category_id=category_id)

        cur = execute_cmd(
            "UPDATE recipes SET name = ?, ingredients = ?, directions = ?, category_id = ? WHERE id = ? AND user_id = ?",
            [name, ingredients, directions, category_id, recipe_id, user_id])
        if cur.rowcount == 0:
            abort(404)

        return redirect("/account")

    result = run_query(
        "SELECT id, name, ingredients, directions, category_id FROM recipes WHERE id = ? AND user_id = ?",
        [recipe_id, user_id])

    if len(result) == 0:
        abort(404)

    cats = run_query("SELECT id, name FROM categories ORDER BY name")
    return render_template("editRecipe.html", recipe=result[0], categories=cats, selected_category_id=result[0][4])


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
               EXISTS(SELECT 1 FROM recipe_images i WHERE i.recipe_id = r.id) AS has_image,
               r.category_id,
               c.name                                                         AS category_name
        FROM recipes r
                 JOIN users u ON u.id = r.user_id
                 JOIN categories c ON c.id = r.category_id
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
    category_name = recipe_tuple[8]
    return render_template("recipe.html",
                           recipe=recipe_tuple,
                           avg_rating=rating[0],
                           ratings_count=rating[1],
                           user_rating=user_rating,
                           comments=comments,
                           author_id=author_id,
                           author_name=author_name,
                           category_name=category_name)


@app.route("/comment", methods=["POST"])
def add_comment():
    require_login()
    check_csrf()

    recipe_id = request.form.get("recipe_id", type=int)
    comment = request.form.get("content", "").strip()
    if not comment or not recipe_id:
        abort(400)

    if len(comment) > MAX_COMMENT_LEN or len(comment.strip()) < MIN_COMMENT_LEN:
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

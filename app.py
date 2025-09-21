from flask import Flask, render_template, request, redirect, session, abort
import sqlite3
import hashlib
import secrets
app = Flask(__name__)

# This is terrible practice, but this is a simple UNI project and I dont want to start using ENV variables. Might change later.
app.config['SECRET_KEY'] = '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918'

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=False,
    PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 7
)


def add_visits():
    db = sqlite3.connect('./database.db')
    db.execute("INSERT INTO visits (last_visit) VALUES (datetime('now'))")
    db.commit()
@app.route("/")
def index():
    add_visits()

    return render_template("index.html")

@app.route("/create_account", methods=["GET", "POST"])
def create_account():
    if request.method == "POST":
        db = sqlite3.connect('./database.db')
        username = request.form.get('username')
        password = request.form.get('password')

        existing_user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

        if existing_user:
            return render_template("createAccount.html", error="Username already exists")

        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
        db.commit()
        db.close()

        return redirect("/login")
    else:
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
    else:
        return render_template("login.html")

def validate_credentials(username, password):
    db = sqlite3.connect('./database.db')
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    user = db.execute("SELECT * FROM users WHERE username = ? AND password = ?",
                      (username, hashed_password)).fetchone()
    db.close()
    
    return user

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

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/create_recipe", methods=["GET", "POST"])
def create_recipe():
    require_login()

    if request.method == "POST":
        check_csrf()
        db = sqlite3.connect('./database.db')
        name = request.form.get('name')
        ingredients = request.form.get('ingredients')
        directions = request.form.get('directions')

        if not name or name.strip() == "":
            return render_template("createRecipe.html", error="Recipe name is required")
        if not ingredients or ingredients.strip() == "":
            return render_template("createRecipe.html", error="Ingredients are required")
        if not directions or directions.strip() == "":
            return render_template("createRecipe.html", error="Directions are required")

        db.execute("INSERT INTO recipes (name, ingredients, directions, user_id) VALUES (?, ?, ?, ?)", (name, ingredients, directions, session["user_id"]))

        db.commit()
        db.close()

        return redirect("/")

    else:
        return render_template("createRecipe.html")

@app.route("/recipes")
def recipes():
    q = request.args.get("q", "", type=str)
    db = sqlite3.connect('./database.db')
    db.row_factory = None
    if q:
        pattern = f"%{q}%"
        recipes = db.execute(
            "SELECT * FROM recipes WHERE name LIKE ? OR ingredients LIKE ? OR directions LIKE ? ORDER BY id DESC",
            (pattern, pattern, pattern)
        ).fetchall()
    else:
        recipes = db.execute(
            "SELECT * FROM recipes ORDER BY id DESC"
        ).fetchall()
    db.close()
    return render_template("recipes.html", recipes=recipes, q=q)

@app.route("/recipes/delete", methods=["POST"])
def delete_recipe():
    require_login()
    check_csrf()
    recipe_id = request.form.get("recipe_id", type=int)
    if not recipe_id:
        abort(400)
    user_id = session["user_id"]
    db = sqlite3.connect("./database.db")
    cur = db.execute("DELETE FROM recipes WHERE id = ? AND user_id = ?", (recipe_id, user_id))
    db.commit()
    db.close()
    return redirect("/account")


@app.route("/account", methods=["GET"])
def account():
    require_login()
    user_id = session["user_id"]
    username = session.get("username", "User")
    db = sqlite3.connect("./database.db")
    my_recipes = db.execute(
        "SELECT id, name FROM recipes WHERE user_id = ? ORDER BY name",
        (user_id,)
    ).fetchall()
    db.close()
    return render_template("account.html", username=username, recipes=my_recipes)





#TODO sort functions so this file make sense.
#TODO sort the css into separate files and classes
#TODO add session so that accounts actually work, sign out, and the rest of the features + protection against SQL injection.
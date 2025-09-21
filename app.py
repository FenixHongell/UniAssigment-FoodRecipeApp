from flask import Flask, render_template, request, redirect
import sqlite3
import hashlib
app = Flask(__name__)


def add_visits():
    """
    Add a new visit entry to the visits table in the database.
    :raises sqlite3.Error: If an issue occurs during the database operation.
    :return: None
    """
    db = sqlite3.connect('./database/database.db')
    db.execute("INSERT INTO visits (visited_at) VALUES (datetime('now'))")
    db.commit()
@app.route("/")
def index():
    add_visits()

    return render_template("index.html")

@app.route("/create_account")
def create_account():
    return render_template("createAccount.html")

@app.route("/new_account", methods=["POST"])
def new_account():
    """
    Handles the creation of new user accounts. This function connects to the database, checks whether the
    username already exists, and if not, creates a new user with a hashed password. It provides error handling
    for duplicate usernames and redirects the user upon successful registration.

    :param request: Flask's request object containing form data with `username` and `password` fields.
    :type request: flask.request

    :return: Renders the account creation page with an error message for duplicate usernames or redirects
        to the home page upon successful account creation.
    :rtype: flask.Response
    """
    db = sqlite3.connect('./database/database.db')
    username = request.form.get('username')
    password = request.form.get('password')

    existing_user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

    if existing_user:
        return render_template("createAccount.html", error="Username already exists")

    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
    db.commit()
    db.close()

    return redirect("/")

@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/login_request", methods=["POST"])
def signin():
    """
    Handle user login requests by validating credentials and directing them
    to the corresponding page upon success or failure.

    Validates the user-supplied username and password against a SQLite
    database. If the credentials match an existing user, the user is
    redirected to the home page. Otherwise, an error message is displayed
    on the login page.

    :param username: Submitted username from the login form
    :param password: Submitted password from the login form
    :return: A rendered login page with an error message if the credentials
             are invalid, or a redirection to the home page if successful
    """
    db = sqlite3.connect('./database/database.db')
    username = request.form.get('username')
    password = request.form.get('password')

    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    user = db.execute("SELECT * FROM users WHERE username = ? AND password = ?",
                      (username, hashed_password)).fetchone()

    if not user:
        return render_template("login.html", error="Invalid username or password")

    db.close()
    return redirect("/")

#TODO add session so that accounts actually work, sign out, and the rest of the features.
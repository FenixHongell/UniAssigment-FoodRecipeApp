from __future__ import annotations

import hashlib
import secrets
from typing import Optional

from flask import render_template, request, redirect, session, abort

from helpers import execute_cmd, run_query, validate_credentials, validate_input_recipe


def create_account_action(
    username: Optional[str],
    password: Optional[str],
    min_username_len: int,
    max_username_len: int,
    min_password_len: int,
    max_password_len: int,
):
    if not username or not password:
        return render_template("createAccount.html", error="Username and password are required")
    if len(username) < min_username_len:
        return render_template("createAccount.html", error=f"Username must be at least {min_username_len} characters long")
    if len(password) < min_password_len:
        return render_template("createAccount.html", error=f"Password must be at least {min_password_len} characters long")
    if len(username) > max_username_len:
        return render_template("createAccount.html", error=f"Username must be at most {max_username_len} characters long")
    if len(password) > max_password_len:
        return render_template("createAccount.html", error=f"Password must be at most {max_password_len} characters long")

    existing_user = run_query("SELECT id, username, password FROM users WHERE username = ?", [username])
    if len(existing_user) > 0:
        return render_template("createAccount.html", error="Username already exists")

    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    execute_cmd("INSERT INTO users (username, password) VALUES (?, ?)", [username, hashed_password])

    return redirect("/login")


def signin_action(username: Optional[str], password: Optional[str]):
    user = validate_credentials(username, password)
    if not user:
        return render_template("login.html", error="Invalid username or password")

    session["user_id"] = user[0]
    session["username"] = user[1]
    session["csrf_token"] = secrets.token_hex(16)

    return redirect("/")


def logout_action():
    session.clear()
    return redirect("/")


def create_recipe_post_action(
    min_recipe_name_len: int,
    max_recipe_name_len: int,
    min_ingredients_len: int,
    max_ingredients_len: int,
    min_directions_len: int,
    max_directions_len: int,
):
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

    has_issue, error_message = validate_input_recipe(
        name, ingredients, directions,
        min_recipe_name_len, max_recipe_name_len,
        min_ingredients_len, max_ingredients_len,
        min_directions_len, max_directions_len
    )

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


def delete_recipe_action():
    recipe_id = request.form.get("recipe_id", type=int)
    if not recipe_id:
        abort(400)
    user_id = session["user_id"]

    execute_cmd("DELETE FROM recipes WHERE id = ? AND user_id = ?", [recipe_id, user_id])

    return redirect("/account")


def edit_recipe_post_action(
    recipe_id: int,
    min_recipe_name_len: int,
    max_recipe_name_len: int,
    min_ingredients_len: int,
    max_ingredients_len: int,
    min_directions_len: int,
    max_directions_len: int,
):
    user_id = session["user_id"]

    name = request.form.get("name", "").strip()
    ingredients = request.form.get("ingredients", "").strip()
    directions = request.form.get("directions", "").strip()
    try:
        category_id = int(request.form.get('category_id') or 0)
    except (TypeError, ValueError):
        category_id = 0

    has_issue, error_message = validate_input_recipe(
        name, ingredients, directions,
        min_recipe_name_len, max_recipe_name_len,
        min_ingredients_len, max_ingredients_len,
        min_directions_len, max_directions_len
    )

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


def rate_action():
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


def add_comment_action(min_comment_len: int, max_comment_len: int):
    recipe_id = request.form.get("recipe_id", type=int)
    comment = request.form.get("content", "").strip()
    if not comment or not recipe_id:
        abort(400)

    if len(comment) > max_comment_len or len(comment.strip()) < min_comment_len:
        abort(400)

    execute_cmd(
        "INSERT INTO comments (content, recipe_id, user_id) VALUES (?, ?, ?)",
        [comment, recipe_id, session["user_id"]])

    return redirect(f"/recipes/{recipe_id}")


def delete_comment_action():
    recipe_id = request.form.get("recipe_id", type=int)
    comment_id = request.form.get("comment_id", type=int)
    if not recipe_id or not comment_id:
        abort(400)
    user_id = session["user_id"]

    execute_cmd("DELETE FROM comments WHERE id = ? AND recipe_id = ? AND user_id = ?", [comment_id, recipe_id, user_id])

    return redirect(f"/recipes/{recipe_id}")

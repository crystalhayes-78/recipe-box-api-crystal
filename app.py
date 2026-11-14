"""Recipe Box API — BE104 course skeleton.

A working Flask + SQLite CRUD API for recipes. It stores data perfectly —
and it trusts everyone. There is no authentication and no authorization yet.
That is the point: you will add both, lesson by lesson, in Units 2 and 3.
"""

import sqlite3

from flask import Flask, g, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import jwt

load_dotenv()
JWT_SECRET = os.getenv("JWT_SECRET")

from functools import wraps
from flask import g, request, jsonify
import jwt

def token_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        # 1. Read Authorization header
        auth_header = request.headers.get("Authorization", "")
        parts = auth_header.split()

        if len(parts) != 2 or parts[0] != "Bearer":
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        token = parts[1]

        # 2. Verify JWT and extract identity
        try:
            decoded = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired, please log in again"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        # 3. Store user info on `g`
        g.current_user_id = decoded.get("sub")
        g.current_user_role = decoded.get("role")

        # 4. Call the original view
        return view_func(*args, **kwargs)

    return wrapped_view
DATABASE = "recipes.db"

app = Flask(__name__)


def hash_password(password: str) -> str:
    """Return a secure, one-way hash for storing this password."""
    return generate_password_hash(password, method="pbkdf2:sha256")

def verify_password(stored_hash: str, candidate_password: str) -> bool:
    """Return True if the candidate password matches the stored hash."""
    return check_password_hash(stored_hash, candidate_password)

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def recipe_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "ingredients": row["ingredients"],
        "instructions": row["instructions"],
        "is_public": bool(row["is_public"]),
    }


@app.get("/")
def hello():
    return jsonify({"message": "Recipe Box API", "recipes": "/recipes"})


@app.get("/recipes")
def list_recipes():
    rows = get_db().execute("SELECT * FROM recipes ORDER BY id").fetchall()
    return jsonify([recipe_to_dict(r) for r in rows])


@app.get("/recipes/<int:recipe_id>")
def get_recipe(recipe_id):
    row = get_db().execute(
        "SELECT * FROM recipes WHERE id = ?", (recipe_id,)
    ).fetchone()
    if row is None:
        return jsonify({"error": "recipe not found"}), 404
    return jsonify(recipe_to_dict(row))

@app.post("/recipes")
@token_required
def create_recipe():
    # We already have a verified user at this point
    user_id = g.current_user_id

    # JSON/body validation
    data = request.get_json(silent=True)
    if not data or not data.get("title") or not data.get("ingredients"):
        return jsonify({"error": "title and ingredients are required"}), 400

    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO recipes (title, ingredients, instructions, is_public, owner_id)"
            " VALUES (?, ?, ?, ?, ?)",
            (
                data["title"],
                data["ingredients"],
                data.get("instructions", ""),
                1 if data.get("is_public", True) else 0,
                user_id,
            ),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "a recipe with that title already exists"}), 409

    row = db.execute(
        "SELECT * FROM recipes WHERE id = ?", (cur.lastrowid,)
    ).fetchone()
    return jsonify(recipe_to_dict(row)), 201

@app.patch("/recipes/<int:recipe_id>")
@token_required
def update_recipe(recipe_id):
    # User info already verified by token_required
    user_id = g.current_user_id
    role = g.current_user_role

    db = get_db()

    # 2. Load recipe to distinguish 404 vs 403
    row = db.execute(
        "SELECT * FROM recipes WHERE id = ?", (recipe_id,)
    ).fetchone()

    if row is None:
        return jsonify({"error": "recipe not found"}), 404

    # 3. Enforce ownership (or allow admin)
    if str(row["owner_id"]) != str(user_id) and role != "admin":
        return jsonify({"error": "forbidden: you do not own this recipe"}), 403

    # 4. Validate body and build update fields
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "a JSON body is required"}), 400

    fields, values = [], []
    for column in ("title", "ingredients", "instructions"):
        if column in data:
            fields.append(f"{column} = ?")
            values.append(data[column])
    if "is_public" in data:
        fields.append("is_public = ?")
        values.append(1 if data["is_public"] else 0)

    if not fields:
        return jsonify({"error": "nothing to update"}), 400

    values.append(recipe_id)

    # 5. Perform the update (we already know id exists and is owned)
    try:
        db.execute(
            f"UPDATE recipes SET {', '.join(fields)} WHERE id = ?", values
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "a recipe with that title already exists"}), 409

    updated = db.execute(
        "SELECT * FROM recipes WHERE id = ?", (recipe_id,)
    ).fetchone()
    return jsonify(recipe_to_dict(updated)), 200

@app.delete("/recipes/<int:recipe_id>")
@token_required
def delete_recipe(recipe_id):
    # User info already verified by token_required
    user_id = g.current_user_id
    role = g.current_user_role

    db = get_db()

    # 3. Load the recipe first so we can distinguish 404 vs 403
    row = db.execute(
        "SELECT id, owner_id FROM recipes WHERE id = ?", (recipe_id,)
    ).fetchone()

    if row is None:
        return jsonify({"error": "recipe not found"}), 404

    # 4. Enforce ownership (or allow admin)
    if str(row["owner_id"]) != str(user_id) and role != "admin":
        return jsonify({"error": "forbidden: you do not own this recipe"}), 403

    # 5. Perform the delete
    db.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
    db.commit()

    return "", 204

@app.post("/register")
def register():
    data = request.get_json(silent=True)

    # 1. Validate input
    if not data:
        return jsonify({"error": "JSON body is required"}), 400

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return jsonify({"error": "username, email, and password are required"}), 400

    # 2. Hash the password
    password_hash = hash_password(password)

    # 3. Insert user into the database
    db = get_db()
    try:
        db.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, password_hash),
        )
        db.commit()
    except sqlite3.IntegrityError:
        # could be duplicate username or email
        return jsonify({"error": "an account with that username or email already exists"}), 409

    # 4. Return success (do NOT return password or hash)
    return jsonify({
        "message": "account created",
        "username": username,
        "email": email
    }), 201

@app.post("/login")
def login():
    data = request.get_json(silent=True) or {}

    # Allow choosing a fake user_id via the JSON body, default to 1
    user_id = data.get("user_id", 1)

    # Decide role based on user_id (for now)
    role = "admin" if user_id == 1 else "user"

    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.utcnow() + timedelta(seconds=30),
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

    return jsonify({"token": token}), 200

if __name__ == "__main__":
    app.run(port=5001, debug=True)

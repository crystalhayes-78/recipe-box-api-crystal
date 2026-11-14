"""Create and seed recipes.db. Run once after cloning: python init_db.py"""

import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user'
);

CREATE TABLE IF NOT EXISTS recipes (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL UNIQUE,
    ingredients TEXT NOT NULL,
    instructions TEXT NOT NULL DEFAULT '',
    is_public INTEGER NOT NULL DEFAULT 1,
    owner_id INTEGER NOT NULL
);
"""

SEED = [
    (
        "Shakshuka",
        "eggs, tomatoes, peppers, onion, cumin, paprika",
        "Simmer the sauce, crack in the eggs, cover until just set.",
        1,
        1,  # owner_id
    ),
    (
        "Overnight oats",
        "rolled oats, milk, yogurt, chia seeds, honey",
        "Stir everything together and refrigerate overnight.",
        1,
        1,  # owner_id
    ),
    (
        "Secret family hot sauce",
        "habaneros, garlic, vinegar, a secret ingredient",
        "If we wrote it down here, it wouldn't be a secret.",
        0,
        1,  # owner_id
    ),
]

# open the connection once
connection = sqlite3.connect("recipes.db")
connection.executescript(SCHEMA)

# Seed one admin user if users table is empty
existing_users = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
if existing_users == 0:
    connection.execute(
        "INSERT INTO users (email, password_hash, role) VALUES (?, ?, ?)",
        ("admin@example.com", "FAKE_HASH_FOR_NOW", "admin"),
    )
    connection.commit()
    print("Seeded 1 admin user.")

# Seed recipes if table is empty
existing = connection.execute("SELECT COUNT(*) FROM recipes").fetchone()[0]
if existing == 0:
    connection.executemany(
        "INSERT INTO recipes (title, ingredients, instructions, is_public, owner_id)"
        " VALUES (?, ?, ?, ?, ?)",
        SEED,
    )
    connection.commit()
    print(f"Created recipes.db and seeded {len(SEED)} recipes.")
else:
    print(f"recipes.db already has {existing} recipes - nothing to do.")

connection.close()
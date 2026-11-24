# Refactor Plan

## Target layout (planning only)

- core.py: app setup, config, DB helpers, main entry point
- auth.py: password hashing, verification, JWT helpers, login, register, token_required
- recipes.py: recipe CRUD routes and related logic

## Acceptance list (public contract)

1. GET /recipes → 200 and returns a list of recipes in JSON
2. POST /login → 200 and returns a JSON object with an access token
3. POST /recipes → 200 and returns a JSON object for the new recipe, including its ID
4. DELETE /recipes/<id> → 200 and returns JSON confirming the recipe was deleted  *(if this matches your app)*
5. PUT /recipes/<id> → 200 and returns the updated recipe as JSON
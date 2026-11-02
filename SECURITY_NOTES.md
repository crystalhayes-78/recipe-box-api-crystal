# Security notes

- 2026-11-02: Anonymous `GET /recipes` request reaches the server and triggers real database logic. The only failure is a missing `recipes` table (`sqlite3.OperationalError: no such table: recipes`), not a security check. The API does not ask who the requester is before accessing data.
- 2026-11-02: Current API design would allow any anonymous requester who knows `/recipes` or `/recipes/<id>` to perform the same read/update/delete actions as a trusted user, because there is no identity check on these routes.
- 2026-11-02: Correct responses or crashes do not mean the API is secure. Lack of authentication means anyone who discovers the URLs can interact with the recipes data.


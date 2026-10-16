"""Worker package.

Workers are discovered *dynamically* by `app.osint.registry`. Importing this package must never fail
because one worker has an optional dependency (e.g. httpx) — so we deliberately do NOT eager-import the
individual worker modules here. Add a new `workers/<name>.py` with an `@worker("<name>")` function and the
registry picks it up with zero engine/registry edits.
"""
